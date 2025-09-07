import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import time
import threading
import os
import re
import subprocess
import random
from selenium.common.exceptions import TimeoutException, WebDriverException

# === Patch uc.Chrome destructor to prevent WinError 6 warnings ===
uc.Chrome.__del__ = lambda self: None

# Thread-safe list for collecting products
products_lock = threading.Lock()
driver_creation_lock = threading.Lock()
all_products = []

def get_chrome_version():
    """Get installed Chrome version"""
    try:
        result = subprocess.run(['google-chrome', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_match = re.search(r'(\d+)', result.stdout)
            if version_match:
                major_version = int(version_match.group(1))
                print(f"Detected Chrome version: {major_version}")
                return major_version
    except:
        pass
    
    print("Could not detect Chrome version - using auto-detection")
    return None

def setup_simple_driver():
    """Setup driver with simple, compatible options"""
    with driver_creation_lock:
        time.sleep(random.uniform(1, 3))
        
        chrome_version = get_chrome_version()
        
        def create_simple_options():
            options = uc.ChromeOptions()
            
            # Basic required options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            # Simple stealth options (compatible)
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--no-first-run')
            options.add_argument('--disable-default-apps')
            
            # Realistic user agent
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Simple prefs (avoid experimental options)
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "profile.managed_default_content_settings.images": 2
            }
            options.add_experimental_option("prefs", prefs)
            
            return options

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                print(f"Creating driver (attempt {attempt + 1}/{max_attempts})")
                
                if chrome_version and attempt == 0:
                    driver = uc.Chrome(version_main=chrome_version, options=create_simple_options())
                else:
                    driver = uc.Chrome(options=create_simple_options())
                
                # Set timeouts
                driver.set_page_load_timeout(60)
                driver.implicitly_wait(10)
                
                # Simple anti-detection
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                print("✅ Driver created successfully")
                return driver
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    print(f"Waiting 10 seconds before retry...")
                    time.sleep(10)
        
        print("❌ Failed to create driver")
        return None

def scrape_category_simple(base_url, category_name, max_retries=2):
    """Simple category scraping with minimal features"""
    category = base_url.split('/shop/')[1].split('/')[0]
    print(f"Starting category: {category}")
    
    all_category_products = []
    
    for retry_count in range(max_retries):
        driver = setup_simple_driver()
        if driver is None:
            print(f"Failed to create driver for {category}")
            continue
        
        try:
            print(f"Attempt {retry_count + 1}: Accessing {category}")
            
            # Go directly to category page
            url = f"{base_url}?page=1"
            print(f"Loading: {url}")
            driver.get(url)
            time.sleep(5)
            
            # Check page title
            page_title = driver.title
            print(f"Page title: {page_title}")
            
            # Simple product detection
            selectors_to_try = [
                "div[class*='verticalTile']",
                "[data-testid*='product']",
                ".product-tile",
                ".product"
            ]
            
            products_found = False
            working_selector = None
            
            for selector in selectors_to_try:
                try:
                    products = driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(products) > 0:
                        print(f"✅ Found {len(products)} products with selector: {selector}")
                        products_found = True
                        working_selector = selector
                        break
                except:
                    continue
            
            if not products_found:
                print(f"❌ No products found in {category}")
                continue
            
            # Scrape limited pages
            max_pages = 3  # Very limited for testing
            seen_products = set()
            
            for page in range(1, max_pages + 1):
                try:
                    if page > 1:
                        page_url = f"{base_url}?page={page}"
                        driver.get(page_url)
                        time.sleep(3)
                    
                    products = driver.find_elements(By.CSS_SELECTOR, working_selector)
                    print(f"Page {page}: Found {len(products)} product elements")
                    
                    page_products = []
                    for product in products[:10]:  # Limit to first 10 products per page
                        try:
                            # Simple name extraction
                            name = "N/A"
                            try:
                                name_elem = product.find_element(By.CSS_SELECTOR, "a, h3, h2")
                                if name_elem and name_elem.text.strip():
                                    name = name_elem.text.strip()
                            except:
                                pass
                            
                            # Simple price extraction
                            price = "N/A"
                            try:
                                price_elem = product.find_element(By.CSS_SELECTOR, "[class*='price'], [class*='cost']")
                                if price_elem and price_elem.text.strip() and '£' in price_elem.text:
                                    price = price_elem.text.strip()
                            except:
                                pass
                            
                            if name != "N/A" and price != "N/A":
                                product_id = f"{name}_{price}"
                                if product_id not in seen_products:
                                    page_products.append({
                                        "Category": category,
                                        "Name": name,
                                        "Price": price
                                    })
                                    seen_products.add(product_id)
                        except:
                            continue
                    
                    all_category_products.extend(page_products)
                    print(f"{category}: Page {page} - {len(page_products)} products (Total: {len(all_category_products)})")
                    
                    time.sleep(2)
                
                except Exception as e:
                    print(f"Error on page {page}: {e}")
                    break
            
            print(f"✅ {category}: Completed - {len(all_category_products)} products")
            break  # Success, exit retry loop
            
        except Exception as e:
            print(f"⚠️ {category}: Attempt {retry_count + 1} failed: {e}")
            if retry_count < max_retries - 1:
                print(f"Waiting 30 seconds before retry...")
                time.sleep(30)
        
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    return all_category_products

def save_csv_to_both_locations(df, filename):
    """Save CSV to both locations"""
    local_path = f"{filename}.csv"
    df.to_csv(local_path, index=False, encoding="utf-8")
    print(f"✅ Saved to local: {local_path}")
    
    public_dir = "../app/public"
    if not os.path.exists(public_dir):
        os.makedirs(public_dir, exist_ok=True)
    
    public_path = os.path.join(public_dir, f"{filename}.csv")
    df.to_csv(public_path, index=False, encoding="utf-8")
    print(f"✅ Saved to public: {public_path}")

def scrape_tesco_optimized():
    """Main function with simple approach"""
    categories = [
        ("https://www.tesco.com/groceries/en-GB/shop/fresh-food/all", "fresh-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/bakery/all", "bakery"),
        ("https://www.tesco.com/groceries/en-GB/shop/frozen-food/all", "frozen-food")
    ]
    
    print("Starting simple Tesco scraper (compatibility mode)...")
    start_time = time.time()
    
    # Sequential processing for maximum compatibility
    for url, name in categories:
        try:
            category_products = scrape_category_simple(url, name)
            with products_lock:
                all_products.extend(category_products)
            print(f"✅ {name}: {len(category_products)} products collected")
        except Exception as e:
            print(f"❌ Category {name} failed: {e}")
    
    if all_products:
        df = pd.DataFrame(all_products)
        df = df.dropna(subset=['Name', 'Price'])
        df = df[df['Name'].str.strip() != '']
        df = df[df['Price'].str.strip() != '']
        df = df.drop_duplicates(subset=['Name', 'Price'])
        
        save_csv_to_both_locations(df, "tesco")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'='*50}")
        print(f"SIMPLE SCRAPING COMPLETED!")
        print(f"Total products: {len(df)}")
        print(f"Total time: {duration:.2f} seconds")
        print(f"Files saved: tesco.csv")
        print(f"{'='*50}")
    else:
        print("❌ No products found - creating test CSV")
        test_df = pd.DataFrame([{
            'Category': 'Test',
            'Name': 'Simple scraper test - checking connection',
            'Price': '£0.00'
        }])
        save_csv_to_both_locations(test_df, "tesco")

if __name__ == "__main__":
    scrape_tesco_optimized()