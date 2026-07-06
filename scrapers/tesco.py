"""
Tesco groceries scraper.
Scrapes Category, Name, Price for every product across all top-level categories
and writes them to tesco.csv.

Data source: server-side-rendered HTML at
    https://www.tesco.com/shop/en-GB/browse/{category}/all?page={n}
"""

import csv
import random
import re
import sys
import time
from dataclasses import dataclass

from bs4 import BeautifulSoup

# --- HTTP client: prefer curl_cffi (Chrome TLS impersonation) to avoid anti-bot blocks
try:
    from curl_cffi import requests as http
    _IMPERSONATE = {"impersonate": "chrome"}
except ImportError:  # graceful fallback
    import requests as http
    _IMPERSONATE = {}

BASE = "https://www.tesco.com/shop/en-GB/browse/{cat}/all"

CATEGORIES = [
    "fresh-food",
    "bakery",
    "frozen-food",
    "treats-and-snacks",
    "food-cupboard",
    "drinks",
    "baby-and-toddler",
    "health-and-beauty",
    "pets",
    "household",
    "home-and-ware",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.tesco.com/",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
}

PRICE_CLASS = "online-components-product-tile-price__text"
COUNT_RE = re.compile(r"of\s+([\d,]+)\s+items", re.I)
PER_PAGE = 24


@dataclass(frozen=True)
class Product:
    category: str
    name: str
    price: str


def make_session():
    s = http.Session()
    s.headers.update(HEADERS)
    return s


def fetch(session, url, params=None, max_retries=4):
    """GET with retries + exponential backoff and polite jitter."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, params=params, timeout=30, **_IMPERSONATE)
            if resp.status_code == 200 and resp.text:
                return resp.text
            if resp.status_code in (403, 429, 503):
                wait = min(60, 2 ** attempt) + random.uniform(0, 3)
                print(f"  [{resp.status_code}] blocked/throttled, backing off {wait:.1f}s", file=sys.stderr)
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except Exception as e:  # network errors
            wait = min(60, 2 ** attempt) + random.uniform(0, 3)
            print(f"  request error: {e} -> retry in {wait:.1f}s", file=sys.stderr)
            time.sleep(wait)
    return None


def parse_products(html, category):
    soup = BeautifulSoup(html, "html.parser")
    products = []
    for li in soup.select("li[data-testid]"):
        link = li.select_one('h2 a[href*="/products/"], h3 a[href*="/products/"]')
        price_el = li.select_one(f".{PRICE_CLASS}")
        if not link or not price_el:
            continue
        name = link.get_text(strip=True)
        price = price_el.get_text(strip=True)
        if name and price:
            products.append(Product(category, name, price))
    return products


def total_pages(html):
    m = COUNT_RE.search(BeautifulSoup(html, "html.parser").get_text(" "))
    if not m:
        return 1
    total = int(m.group(1).replace(",", ""))
    return (total + PER_PAGE - 1) // PER_PAGE


def scrape_category(session, category):
    url = BASE.format(cat=category)
    first = fetch(session, url, params={"page": 1})
    if not first:
        print(f"! failed first page for {category}", file=sys.stderr)
        return []

    pages = total_pages(first)
    print(f"== {category}: {pages} page(s)")

    seen = set()
    results = []

    def add(items):
        for p in items:
            key = (p.category, p.name, p.price)
            if key not in seen:
                seen.add(key)
                results.append(p)

    add(parse_products(first, category))

    for page in range(2, pages + 1):
        time.sleep(random.uniform(1.0, 2.5))  # polite, human-like pacing
        html = fetch(session, url, params={"page": page})
        if not html:
            print(f"  ! skipped {category} page {page}", file=sys.stderr)
            continue
        items = parse_products(html, category)
        add(items)
        print(f"  page {page}/{pages}: {len(items)} items (total {len(results)})")

    return results


def main():
    session = make_session()
    all_products = []
    for category in CATEGORIES:
        try:
            all_products.extend(scrape_category(session, category))
        except Exception as e:
            print(f"! error scraping {category}: {e}", file=sys.stderr)
        time.sleep(random.uniform(2.0, 4.0))

    with open("tesco.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Category", "Name", "Price"])
        for p in all_products:
            writer.writerow([p.category, p.name, p.price])

    print(f"\nDone. {len(all_products)} products written to tesco.csv")


if __name__ == "__main__":
    main()