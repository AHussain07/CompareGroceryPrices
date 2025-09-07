import os
import sys

chromedriver_path = os.environ.get("UCD_CHROMEDRIVER_PATH")
if not chromedriver_path:
    if os.name == "nt":
        chromedriver_path = os.path.join(os.getcwd(), "chromedriver.exe")
        if not os.path.exists(chromedriver_path):
            print("❌ chromedriver.exe not found. Please download it and set UCD_CHROMEDRIVER_PATH or place it in the script directory.")
            sys.exit(1)
    else:
        chromedriver_path = "./chromedriver"
        if not os.path.exists(chromedriver_path):
            print("❌ chromedriver not found at ./chromedriver. Set UCD_CHROMEDRIVER_PATH or check your workflow.")
            sys.exit(1)
        # Use Windows or Linux default name
        chromedriver_path = "chromedriver.exe" if os.name == "nt" else "chromedriver"

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import time
import threading

products_lock = threading.Lock()
all_products = []

def setup_optimized_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-images')
    options.add_argument('--disable-plugins')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-backgrounding-occluded-windows')
    # Don't disable JS for Tesco, site needs it!
    # options.add_argument('--disable-javascript')
    return uc.Chrome(options=options, driver_executable_path=chromedriver_path)

def scrape_single_category(base_url, category_name):
    driver = setup_optimized_driver()
    category_products = []
    try:
        category = base_url.split('/shop/')[1].split('/')[0]
        print(f"Starting category: {category}")
        url = f"{base_url}?page=1"
        driver.get(url)
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='verticalTile']:first-child"))
            )
        except Exception:
            print(f"No products found in {category}. Skipping.")
            return []
        max_pages = 1
        try:
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.page"))
            )
            page_links = driver.find_elements(By.CSS_SELECTOR, "a.page")
            page_numbers = []
            for link in page_links:
                try:
                    num = int(link.get_attribute("data-page"))
                    page_numbers.append(num)
                except (TypeError, ValueError):
                    continue
            max_pages = max(page_numbers) if page_numbers else 1
        except Exception:
            max_pages = 1
        print(f"{category}: Found {max_pages} pages")
        for page in range(1, max_pages + 1):
            if page > 1:
                url = f"{base_url}?page={page}"
                driver.get(url)
                try:
                    WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='verticalTile']:first-child"))
                    )
                except Exception:
                    print(f"{category}: No products on page {page}")
                    break
            product_tiles = driver.find_elements(By.CSS_SELECTOR, "div[class*='verticalTile']")
            if not product_tiles:
                print(f"{category}: No products found on page {page}")
                break
            page_products = []
            for product in product_tiles:
                try:
                    name_elem = product.find_element(By.CSS_SELECTOR, "a[class*='titleLink']")
                    name = name_elem.text.strip() if name_elem else "N/A"
                    price_elems = product.find_elements(By.CSS_SELECTOR, "p[class*='priceText']")
                    price = price_elems[0].text.strip() if price_elems else "N/A"
                    page_products.append({
                        "Category": category,
                        "Name": name,
                        "Price": price
                    })
                except Exception:
                    continue
            category_products.extend(page_products)
            print(f"{category}: Page {page}/{max_pages} - {len(page_products)} products")
        print(f"{category}: Completed - {len(category_products)} total products")
        return category_products
    except Exception as e:
        print(f"Error in {category}: {e}")
        return []
    finally:
        driver.quit()

def scrape_tesco_optimized():
    categories = [
        ("https://www.tesco.com/groceries/en-GB/shop/fresh-food/all", "fresh-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/bakery/all", "bakery"),
        ("https://www.tesco.com/groceries/en-GB/shop/frozen-food/all", "frozen-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/treats-and-snacks/all", "treats-and-snacks"),
        ("https://www.tesco.com/groceries/en-GB/shop/food-cupboard/all", "food-cupboard"),
        ("https://www.tesco.com/groceries/en-GB/shop/drinks/all", "drinks"),
        ("https://www.tesco.com/groceries/en-GB/shop/baby-and-toddler/all", "baby-and-toddler")
    ]
    print("Starting optimized Tesco scraper with parallel processing...")
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_category = {
            executor.submit(scrape_single_category, url, name): name
            for url, name in categories
        }
        for future in as_completed(future_to_category):
            category_name = future_to_category[future]
            try:
                category_products = future.result()
                with products_lock:
                    all_products.extend(category_products)
            except Exception as e:
                print(f"Category {category_name} failed: {e}")
    if all_products:
        df = pd.DataFrame(all_products)
        df.to_csv("tesco.csv", index=False)
        end_time = time.time()
        duration = end_time - start_time
        print(f"\n{'='*50}")
        print(f"SCRAPING COMPLETED!")
        print(f"Total products: {len(all_products)}")
        print(f"Total time: {duration:.2f} seconds")
        print(f"Products per second: {len(all_products)/duration:.2f}")
        print(f"File saved: tesco.csv")
        print(f"{'='*50}")
    else:
        print("No products found.")

if __name__ == "__main__":
    scrape_tesco_optimized()