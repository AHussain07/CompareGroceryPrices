"""
Morrisons all-products scraper (API-driven, via real browser context).
Discovers every top-level category from the All Products page, then pulls
Category, Product Name, Price for each using the site's own JSON API called
from inside the page (so it passes anti-bot protection).
"""
import asyncio
import csv
import re
import sys
from playwright.async_api import async_playwright

ALL_PRODUCTS_URL = "https://groceries.morrisons.com/categories"
OUTPUT_CSV = "morrisons.csv"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
MAX_CATEGORIES = None  # set an int to limit while testing

# This runs in the browser. It walks the product-pages API page by page using
# nextPageToken, and decorates any undecorated product IDs via the products
# endpoint. Returns {category, products:[{name, price}]}.
JS_SCRAPE_CATEGORY = r"""
async (retailerCategoryId) => {
  const base = "/api/webproductpagews/v6";
  const sort = "pricePerAscending";
  const out = [];
  let categoryName = "Unknown";
  let pageToken = null;
  let guard = 0;

  const decorate = async (ids) => {
    if (!ids.length) return [];
    const res = await fetch(base + "/products", {
      method: "PUT",
      headers: { "content-type": "application/json", "accept": "application/json" },
      credentials: "include",
      body: JSON.stringify(ids),
    });
    if (!res.ok) return [];
    const j = await res.json();
    return j.products || [];
  };

  while (guard++ < 200) {
    const params = new URLSearchParams({
      includeAdditionalPageInfo: "true",
      maxPageSize: "300",
      maxProductsToDecorate: "50",
      retailerCategoryId: String(retailerCategoryId),
      sortOptionId: sort,
    });
    params.append("tag", "web");
    params.append("tag", "category-item");
    if (pageToken) params.set("nextPageToken", pageToken);

    const res = await fetch(base + "/product-pages?" + params.toString(), {
      headers: { "accept": "application/json" },
      credentials: "include",
    });
    if (!res.ok) break;
    const data = await res.json();

    const info = data.additionalPageInfo || {};
    if (info.currentCategory && info.currentCategory.name)
      categoryName = info.currentCategory.name;

    // Collect every product entry across all groups (decorated or just an id).
    const undecorated = [];
    for (const g of (data.productGroups || [])) {
      const items = g.decoratedProducts || g.products || [];
      for (const p of items) {
        if (p && p.name && p.price && p.price.amount != null) {
          out.push({ name: p.name.trim(), price: p.price.amount });
        } else if (p && (p.productId || p.retailerProductId)) {
          undecorated.push(p.productId || p.retailerProductId);
        } else if (typeof p === "string") {
          undecorated.push(p);
        }
      }
    }
    // Fill in the ones the page didn't decorate.
    for (let i = 0; i < undecorated.length; i += 50) {
      const chunk = undecorated.slice(i, i + 50);
      const decorated = await decorate(chunk);
      for (const p of decorated) {
        if (p && p.name && p.price && p.price.amount != null)
          out.push({ name: p.name.trim(), price: p.price.amount });
      }
    }

    pageToken = (data.metadata && data.metadata.nextPageToken) || null;
    if (!pageToken) break;
  }
  return { category: categoryName, products: out };
}
"""


async def dismiss_cookies(page):
    for sel in ['button:has-text("Accept")', 'button:has-text("Reject")',
                "#onetrust-reject-all-handler"]:
        try:
            await page.click(sel, timeout=2500)
            return
        except Exception:
            pass


async def discover_categories(page):
    await page.goto(ALL_PRODUCTS_URL, wait_until="domcontentloaded", timeout=60000)
    await dismiss_cookies(page)
    await page.wait_for_timeout(2000)
    hrefs = await page.eval_on_selector_all(
        'a[href*="/categories/"]',
        "els => els.map(e => e.getAttribute('href'))",
    )
    cats = {}
    for href in hrefs or []:
        m = re.match(r"^/categories/([a-z0-9\-]+)/(\d+)", href or "")
        if m:
            cats[m.group(2)] = m.group(1)   # id -> slug
    return cats


async def scrape():
    products = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled",
                  "--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=USER_AGENT, viewport={"width": 1366, "height": 900}, locale="en-GB")
        await context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        page = await context.new_page()

        cats = await discover_categories(page)
        cat_ids = list(cats.items())
        if MAX_CATEGORIES:
            cat_ids = cat_ids[:MAX_CATEGORIES]
        print(f"Discovered {len(cat_ids)} categories.", file=sys.stderr)

        for i, (cat_id, slug) in enumerate(cat_ids, 1):
            # Land on the category page first so the API call runs in the right
            # context (referer, cookies, any per-category state).
            url = f"https://groceries.morrisons.com/categories/{slug}/{cat_id}"
            print(f"[{i}/{len(cat_ids)}] {slug} ({cat_id})", file=sys.stderr)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(1500)
                result = await page.evaluate(JS_SCRAPE_CATEGORY, cat_id)
            except Exception as e:
                print(f"  failed: {e}", file=sys.stderr)
                continue

            cat_name = result.get("category", slug)
            n = 0
            for prod in result.get("products", []):
                try:
                    price = f"£{float(prod['price']):.2f}"
                except (TypeError, ValueError):
                    continue
                key = (cat_name, prod["name"], price)
                if key not in products:
                    products[key] = {"category": cat_name, "name": prod["name"], "price": price}
                    n += 1
            print(f"  {cat_name}: +{n} (total {len(products)})", file=sys.stderr)

        await browser.close()

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Category", "Product Name", "Price"])
        for r in products.values():
            w.writerow([r["category"], r["name"], r["price"]])
    print(f"Done. Wrote {len(products)} rows to {OUTPUT_CSV}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(scrape())