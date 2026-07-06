"""
aldi.py

Scrapes Category, Product Name and Price for all products from ALDI UK
category listing pages (https://www.aldi.co.uk/products/...).

ALDI's edge protection blocks plain HTTP clients (requests/curl_cffi may work,
but they escalate). This version drives a real headless Chromium via Playwright,
which passes the anti-bot layer, renders the page, and reads the same
server-rendered product tiles.

Key correctness details discovered from the live site:
  * Product tile:  div.product-tile
  * Brand:  .product-tile__brandname   Name: .product-tile__name
  * Price:  .base-price__discounted  (fallback .base-price__regular)
  * Pagination uses ?page=N. IMPORTANT: out-of-range pages are CLAMPED to the
    last valid page (page=999 returns the last page's products, not empty), so
    we must read the true last page number from the pagination control and also
    dedupe defensively.

Output: aldi_products.csv  ->  Category,Product Name,Price

Install:
    pip install playwright beautifulsoup4
    playwright install chromium
"""

import csv
import random
import re
import sys
import time

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = "https://www.aldi.co.uk"

# Top-level grocery categories (label -> listing path, without ?page=).
CATEGORIES = {
    "price-drops":            "/products/price-drops/k/1588161430418388",
    "fresh-food":             "/products/fresh-food/k/1588161416978050",
    "chilled-food":           "/products/chilled-food/k/1588161416978051",
    "food-cupboard":          "/products/food-cupboard/k/1588161416978053",
    "frozen-food":            "/products/frozen-food/k/1588161416978056",
    "baby-toddler":           "/products/baby-toddler/k/1588161416978057",
    "health-beauty":          "/products/health-beauty/k/1588161416978058",
    "home-essentials":        "/products/home-essentials/k/1588161416978059",
    "pet-care":               "/products/pet-care/k/1588161416978060",
    "vegetarian-plant-based": "/products/vegetarian-plant-based/k/1588161421881163",
    "higher-protein":         "/products/higher-protein-food-drink/k/1588161424510127",
    "specially-selected":     "/products/specially-selected/k/1588161431580089",
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

MAX_PAGES = 200          # hard safety cap per category
NAV_TIMEOUT = 30_000     # ms
TILE_TIMEOUT = 15_000    # ms to wait for product tiles to render
MIN_DELAY, MAX_DELAY = 1.0, 2.5   # polite delay between page loads


def polite_sleep():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def clean(text):
    return " ".join(text.split()).strip() if text else ""


def dismiss_cookie_banner(page):
    """Accept/close the OneTrust consent banner if it appears (best-effort)."""
    for sel in ("#onetrust-accept-btn-handler",
                "button#onetrust-reject-all-handler",
                "button[aria-label='Close']"):
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click(timeout=3000)
                page.wait_for_timeout(500)
                return
        except Exception:
            pass


def parse_products(html, category):
    """Extract (category, name, price) tuples + tile count from one page."""
    soup = BeautifulSoup(html, "html.parser")
    tiles = soup.select("div.product-tile")
    rows = []
    for tile in tiles:
        brand_el = tile.select_one(".product-tile__brandname")
        name_el = tile.select_one(".product-tile__name")
        price_el = (tile.select_one(".base-price__discounted")
                    or tile.select_one(".base-price__regular"))

        brand = clean(brand_el.get_text()) if brand_el else ""
        name = clean(name_el.get_text()) if name_el else ""
        price = clean(price_el.get_text()) if price_el else ""

        if not name:
            continue

        full_name = f"{brand} {name}".strip() if brand else name
        rows.append((category, full_name, price))
    return rows, len(tiles)


def get_last_page(html):
    """Read the highest page number from the pagination control (default 1)."""
    soup = BeautifulSoup(html, "html.parser")
    nums = []
    for el in soup.select(".base-pagination__count"):
        m = re.match(r"\d+", el.get_text().strip())
        if m:
            nums.append(int(m.group()))
    return max(nums) if nums else 1


def load_page(page, url):
    """Navigate and wait for product tiles. Returns HTML or None."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
    except PWTimeout:
        print(f"  nav timeout: {url}", file=sys.stderr)
        return None
    dismiss_cookie_banner(page)
    try:
        page.wait_for_selector("div.product-tile", timeout=TILE_TIMEOUT)
    except PWTimeout:
        # No tiles rendered (empty category or a block page).
        return page.content()
    return page.content()


def scrape_category(page, category, path):
    print(f"Scraping category: {category}")
    all_rows = []
    seen = set()  # dedupe by (name, price) to survive page clamping

    # Page 1 first so we can read the true last-page number.
    html = load_page(page, f"{BASE}{path}?page=1")
    if html is None:
        print(f"  failed to load {category} page 1", file=sys.stderr)
        return all_rows

    last_page = min(get_last_page(html), MAX_PAGES)
    rows, tiles = parse_products(html, category)
    for r in rows:
        key = (r[1], r[2])
        if key not in seen:
            seen.add(key)
            all_rows.append(r)
    print(f"  page 1/{last_page}: {tiles} tiles")

    for pnum in range(2, last_page + 1):
        polite_sleep()
        html = load_page(page, f"{BASE}{path}?page={pnum}")
        if html is None:
            break
        rows, tiles = parse_products(html, category)
        new = 0
        for r in rows:
            key = (r[1], r[2])
            if key not in seen:
                seen.add(key)
                all_rows.append(r)
                new += 1
        print(f"  page {pnum}/{last_page}: {tiles} tiles, {new} new")
        # If a clamped page yields nothing new, stop early.
        if new == 0:
            break

    print(f"  -> {len(all_rows)} products in {category}")
    return all_rows


def main():
    all_rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="en-GB",
            viewport={"width": 1366, "height": 900},
            extra_http_headers={"Accept-Language": "en-GB,en;q=0.9"},
        )
        # Light stealth: hide the webdriver flag.
        context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        page = context.new_page()

        # Warm up on the homepage so cookies/consent are established.
        try:
            page.goto(BASE + "/", wait_until="domcontentloaded",
                      timeout=NAV_TIMEOUT)
            dismiss_cookie_banner(page)
        except PWTimeout:
            pass
        polite_sleep()

        for category, path in CATEGORIES.items():
            try:
                all_rows.extend(scrape_category(page, category, path))
            except Exception as e:
                print(f"  error in {category}: {e}", file=sys.stderr)
            polite_sleep()

        browser.close()

    with open("aldi.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Category", "Product Name", "Price"])
        writer.writerows(all_rows)

    print(f"\nDone. Wrote {len(all_rows)} products to aldi.csv")


if __name__ == "__main__":
    main()