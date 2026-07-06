#!/usr/bin/env python3
"""
ASDA Groceries product scraper.

Pulls Category, Name, Price for every product from ASDA's public Algolia
product index (the same API their website uses client-side). Writes asda.csv.

Designed to run headless on GitHub Actions:
 - No browser / Selenium needed (pure HTTP + JSON).
 - Retries with exponential backoff + jitter.
 - Recursively subdivides large buckets to work around Algolia's
   pagination limit so no products are missed.
"""

import csv
import json
import time
import random
import sys
from urllib import request, error

# ---- Algolia config (public search credentials read from ASDA's site config) ----
ALGOLIA_APP_ID = "8I6WSKCCNV"
ALGOLIA_API_KEY = "03e4272048dd17f771da37b57ff8a75e"
ALGOLIA_INDEX = "ASDA_PRODUCTS"
ALGOLIA_URL = (
    f"https://{ALGOLIA_APP_ID.lower()}-dsn.algolia.net"
    f"/1/indexes/{ALGOLIA_INDEX}/query"
)

HITS_PER_PAGE = 1000
# Algolia refuses page * hitsPerPage beyond paginationLimitedTo.
# When a bucket reports more hits than we can page through, subdivide it.
MAX_REACHABLE_HITS = 3000

# The facet levels we subdivide by, from broad to narrow.
TAXONOMY_LEVELS = [
    "PRIMARY_TAXONOMY.CAT_NAME",
    "PRIMARY_TAXONOMY.DEPT_NAME",
    "PRIMARY_TAXONOMY.AISLE_NAME",
    "PRIMARY_TAXONOMY.SHELF_NAME",
]

PRICE_ZONE = "EN"  # England pricing


def _headers():
    return {
        "X-Algolia-API-Key": ALGOLIA_API_KEY,
        "X-Algolia-Application-Id": ALGOLIA_APP_ID,
        "Content-Type": "application/json",
        # Look like the browser client the site actually uses.
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        "Origin": "https://www.asda.com",
        "Referer": "https://www.asda.com/",
    }


def algolia_query(params, max_retries=6):
    """POST a single query to Algolia with retry/backoff. Returns parsed JSON."""
    body = json.dumps({"params": params}).encode("utf-8")
    last_err = None
    for attempt in range(max_retries):
        try:
            req = request.Request(
                ALGOLIA_URL, data=body, headers=_headers(), method="POST"
            )
            with request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (error.HTTPError, error.URLError, TimeoutError) as e:
            last_err = e
            # Exponential backoff with jitter to be polite and dodge rate limits.
            sleep = (2 ** attempt) + random.uniform(0, 1.5)
            print(f"  request failed ({e}); retry {attempt + 1} in {sleep:.1f}s",
                  file=sys.stderr)
            time.sleep(sleep)
    raise RuntimeError(f"Algolia query failed after {max_retries} retries: {last_err}")


def _encode_params(query="", hits=HITS_PER_PAGE, page=0, facet_filters=None,
                   facets=None):
    parts = [f"query={query}", f"hitsPerPage={hits}", f"page={page}"]
    if facets:
        parts.append("facets=" + request.quote(json.dumps(facets)))
    if facet_filters:
        parts.append("facetFilters=" + request.quote(json.dumps(facet_filters)))
    return "&".join(parts)


def get_facet_values(level, facet_filters):
    """Return {value: count} for `level` within the given filter constraints."""
    params = _encode_params(hits=0, facets=[level], facet_filters=facet_filters)
    data = algolia_query(params)
    return data.get("facets", {}).get(level, {})


def extract_rows(hits):
    """Turn Algolia hits into (category, name, price) tuples."""
    rows = []
    for h in hits:
        name = (h.get("NAME") or "").strip()
        tax = h.get("PRIMARY_TAXONOMY") or {}
        category = (tax.get("CAT_NAME") or "").strip()
        prices = (h.get("PRICES") or {}).get(PRICE_ZONE) or {}
        price = prices.get("PRICE")
        if not name or price is None:
            continue
        rows.append((category, name, f"£{float(price):.2f}"))
    return rows


def scrape_bucket(facet_filters, level_index, seen_ids, writer, path=""):
    """
    Recursively scrape all products matching `facet_filters`.

    If the bucket has more hits than Algolia lets us page through, drill down
    into the next taxonomy level and scrape each sub-bucket separately.
    """
    probe = algolia_query(_encode_params(hits=0, facet_filters=facet_filters))
    total = probe.get("nbHits", 0)
    if total == 0:
        return

    if total > MAX_REACHABLE_HITS and level_index < len(TAXONOMY_LEVELS):
        # Subdivide.
        level = TAXONOMY_LEVELS[level_index]
        values = get_facet_values(level, facet_filters)
        print(f"{path} -> {total} hits; splitting on {level} "
              f"({len(values)} values)")
        for value in values:
            child_filters = facet_filters + [f"{level}:{value}"]
            scrape_bucket(child_filters, level_index + 1, seen_ids, writer,
                          path=f"{path} / {value}")
        return

    # Small enough to page through directly.
    print(f"{path} -> paging {total} hits")
    page = 0
    while True:
        data = algolia_query(
            _encode_params(page=page, facet_filters=facet_filters)
        )
        hits = data.get("hits", [])
        if not hits:
            break
        new_hits = []
        for h in hits:
            oid = h.get("objectID")
            if oid in seen_ids:
                continue
            seen_ids.add(oid)
            new_hits.append(h)
        for row in extract_rows(new_hits):
            writer.writerow(row)
        page += 1
        if page >= data.get("nbPages", 0):
            break
        time.sleep(random.uniform(0.2, 0.6))  # light throttle / jitter


def main():
    seen_ids = set()
    # Discover top-level categories dynamically so new ones aren't missed.
    top_level = TAXONOMY_LEVELS[0]
    categories = get_facet_values(top_level, facet_filters=[])
    print(f"Found {len(categories)} top-level categories, "
          f"{sum(categories.values())} products total.")

    with open("asda.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Category", "Name", "Price"])
        for category in categories:
            scrape_bucket(
                facet_filters=[f"{top_level}:{category}"],
                level_index=1,
                seen_ids=seen_ids,
                writer=writer,
                path=category,
            )

    print(f"Done. Wrote {len(seen_ids)} unique products to asda.csv")


if __name__ == "__main__":
    main()