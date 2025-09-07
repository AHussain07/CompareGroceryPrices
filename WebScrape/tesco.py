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
from selenium.common.exceptions import TimeoutException, WebDriverException

# === Patch uc.Chrome destructor to prevent WinError 6 warnings ===
uc.Chrome.__del__ = lambda self: None

# Thread-safe list for collecting products
products_lock = threading.Lock()
driver_creation_lock = threading.Lock()
all_products = []

def get_chrome_version():
    """Get installed Chrome version - adapted from sainsburys.py"""
    try:
        # Try Linux/GitHub Actions method first
        try:
            result = subprocess.run(['google-chrome', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Extract the actual version number, not just major
                version_match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', result.stdout)
                if version_match:
                    full_version = version_match.group(0)
                    major_version = int(version_match.group(1))
                    print(f"Detected Chrome version: {full_version} (major: {major_version})")
                    return major_version
        except:
            pass
        
        # Try registry method (Windows)
        try:
            result = subprocess.run([
                'reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                version_match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', result.stdout)
                if version_match:
                    full_version = version_match.group(0)
                    major_version = int(version_match.group(1))
                    print(f"Detected Chrome version: {full_version} (major: {major_version})")
                    return major_version
        except:
            pass
        
        # Try PowerShell method (Windows)
        try:
            result = subprocess.run([
                'powershell', '-command', 
                '(Get-Item "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe").VersionInfo.ProductVersion'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                version_match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', result.stdout)
                if version_match:
                    full_version = version_match.group(0)
                    major_version = int(version_match.group(1))
                    print(f"Detected Chrome version: {full_version} (major: {major_version})")
                    return major_version
        except:
            pass
        
        print("Could not detect Chrome version - will use auto-detection")
        return None
        
    except Exception as e:
        print(f"Error detecting Chrome version: {e}")
        return None

def setup_optimized_driver():
    """Setup Chrome driver with performance optimizations and thread-safe creation"""
    with driver_creation_lock:
        time.sleep(0.5)
        
        chrome_version = get_chrome_version()
        
        # Create fresh options for each attempt
        def create_options():
            options = uc.ChromeOptions()
            options.add_argument('--disable-images')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--headless')
            options.add_argument('--user-agent=Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36')
            # Increase timeouts to handle slow pages
            options.add_argument('--timeout=300')
            options.add_argument('--page-load-strategy=normal')
            return options

        try:
            # Try with detected Chrome version first
            if chrome_version:
                print(f"Attempting to create driver with Chrome version {chrome_version}")
                try:
                    driver = uc.Chrome(version_main=chrome_version, options=create_options())
                    # Set longer timeouts
                    driver.set_page_load_timeout(180)  # Increased from default
                    driver.implicitly_wait(15)  # Increased from default
                    print("✅ Driver created successfully with detected version")
                    return driver
                except Exception as e:
                    print(f"Failed with detected version {chrome_version}: {e}")
            
            # Fallback 1: Try with version 139 (the actual Chrome version shown in error)
            print("Attempting with Chrome version 139...")
            try:
                driver = uc.Chrome(version_main=139, options=create_options())
                driver.set_page_load_timeout(180)
                driver.implicitly_wait(15)
                print("✅ Driver created successfully with version 139")
                return driver
            except Exception as e:
                print(f"Failed with version 139: {e}")
            
            # Fallback 2: Let undetected-chromedriver auto-detect
            print("Attempting auto-detection fallback...")
            driver = uc.Chrome(version_main=None, options=create_options())
            driver.set_page_load_timeout(180)
            driver.implicitly_wait(15)
            print("✅ Driver created successfully with auto-detection")
            return driver
            
        except Exception as e:
            print(f"Failed to create driver: {e}")
            return None

def scrape_category_with_retry(base_url, category_name, max_retries=3):
    """Scrape a category with retry logic for timeout handling"""
    category = base_url.split('/shop/')[1].split('/')[0]
    print(f"Starting category: {category}")
    
    all_category_products = []
    last_successful_page = 0
    retry_count = 0
    
    while retry_count < max_retries:
        driver = setup_optimized_driver()
        if driver is None:
            print(f"Failed to create driver for {category_name} (attempt {retry_count + 1})")
            retry_count += 1
            if retry_count < max_retries:
                print(f"Waiting 30 seconds before retry...")
                time.sleep(30)
            continue
        
        try:
            # If this is a retry, start from where we left off
            start_page = last_successful_page + 1 if retry_count > 0 else 1
            print(f"Starting from page {start_page} (attempt {retry_count + 1})")
            
            # Load first page to get pagination info
            url = f"{base_url}?page={start_page}"
            print(f"Loading URL: {url}")
            driver.get(url)
            time.sleep(3)
            
            # Debug: Check what actually loaded
            page_title = driver.title
            print(f"Page title: {page_title}")
            
            # Try multiple selectors for products - expanded list
            product_selectors = [
                "div[class*='verticalTile']",           # Current main selector
                "[data-testid*='product']",             # TestID products  
                ".product-tile",                        # Standard product tiles
                ".product",                             # Generic products
                "[class*='product']",                   # Any product class
                ".tile",                                # Tile elements
                "article[data-testid*='product']",      # Article products
                "[class*='tile'][class*='product']",    # Combined tile+product
                "div[class*='product'][class*='tile']", # Div product tiles
                "li[class*='product']",                 # List item products
                "[data-auto*='product']"                # Auto-test products
            ]
            
            products_found = False
            working_selector = None
            
            for selector in product_selectors:
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    product_tiles = driver.find_elements(By.CSS_SELECTOR, selector)
                    if product_tiles:
                        print(f"✅ Found {len(product_tiles)} products using selector: {selector}")
                        products_found = True
                        working_selector = selector
                        break
                    else:
                        print(f"Selector {selector} found no products")
                except Exception as e:
                    print(f"Selector {selector} failed: {e}")
                    continue
            
            if not products_found:
                print(f"❌ No products found with any selector in {category}")
                retry_count += 1
                if retry_count < max_retries:
                    print(f"Waiting 30 seconds before retry...")
                    time.sleep(30)
                continue
            
            # Get pagination info only if this is the first attempt
            if retry_count == 0:
                max_pages = 1
                try:
                    page_elements = driver.find_elements(By.CSS_SELECTOR, "a.page, [data-testid*='page'], .pagination a")
                    if page_elements:
                        page_numbers = []
                        for elem in page_elements:
                            try:
                                # Try different attributes
                                for attr in ['data-page', 'aria-label', 'text']:
                                    if attr == 'text':
                                        text = elem.text.strip()
                                        if text.isdigit():
                                            page_numbers.append(int(text))
                                    else:
                                        value = elem.get_attribute(attr)
                                        if value and value.isdigit():
                                            page_numbers.append(int(value))
                            except:
                                continue
                        max_pages = max(page_numbers) if page_numbers else 1
                except Exception as e:
                    print(f"Pagination detection failed: {e}")
                
                # NO PAGE LIMIT - scrape all pages found
                print(f"{category}: Found {max_pages} pages - will scrape ALL pages")
            else:
                # Use the max_pages from previous attempt
                max_pages = getattr(scrape_category_with_retry, '_max_pages', 1)
            
            # Store max_pages for retry attempts
            scrape_category_with_retry._max_pages = max_pages
            
            # Scrape pages with timeout handling
            consecutive_empty_pages = 0
            seen_products = set()
            
            for page in range(start_page, max_pages + 1):
                try:
                    if page > start_page:
                        url = f"{base_url}?page={page}"
                        print(f"Loading page {page}/{max_pages}...")
                        driver.get(url)
                        time.sleep(2)
                    
                    # Use the working selector
                    product_tiles = driver.find_elements(By.CSS_SELECTOR, working_selector)
                    print(f"DEBUG: Found {len(product_tiles)} product tiles on page {page}")
                    
                    if not product_tiles:
                        print(f"{category}: No products found on page {page}")
                        consecutive_empty_pages += 1
                        if consecutive_empty_pages >= 3:
                            print(f"🛑 Stopping {category} after {consecutive_empty_pages} empty pages")
                            break
                        continue
                    
                    consecutive_empty_pages = 0
                    
                    # Extract product data with detailed tracking
                    page_products = []
                    new_products_count = 0
                    extraction_failures = 0
                    
                    for i, product in enumerate(product_tiles):
                        try:
                            # Try multiple name selectors
                            name = "N/A"
                            name_selectors = [
                                "a[class*='titleLink']",
                                "h3", "h2", "h4",
                                "[data-testid*='name']",
                                "[class*='name']",
                                "[class*='title']",
                                "a[href*='/product/']",
                                ".title",
                                "[class*='product-name']"
                            ]
                            
                            for name_sel in name_selectors:
                                try:
                                    name_elem = product.find_element(By.CSS_SELECTOR, name_sel)
                                    if name_elem and name_elem.text.strip():
                                        name = name_elem.text.strip()
                                        break
                                except:
                                    continue
                            
                            # Try multiple price selectors
                            price = "N/A"
                            price_selectors = [
                                "p[class*='priceText']",
                                "[data-testid*='price']",
                                "[class*='price']",
                                ".price",
                                "span[class*='price']",
                                "[class*='cost']",
                                "[class*='amount']"
                            ]
                            
                            for price_sel in price_selectors:
                                try:
                                    price_elem = product.find_element(By.CSS_SELECTOR, price_sel)
                                    if price_elem and price_elem.text.strip():
                                        price_text = price_elem.text.strip()
                                        if '£' in price_text:  # Only accept prices with £ symbol
                                            price = price_text
                                            break
                                except:
                                    continue
                            
                            if name != "N/A" and price != "N/A":
                                # Create unique identifier to avoid duplicates
                                product_id = f"{name}_{price}"
                                
                                if product_id not in seen_products:
                                    page_products.append({
                                        "Category": category,
                                        "Name": name,
                                        "Price": price
                                    })
                                    seen_products.add(product_id)
                                    new_products_count += 1
                            else:
                                extraction_failures += 1
                                    
                        except Exception as e:
                            extraction_failures += 1
                            continue
                    
                    all_category_products.extend(page_products)
                    print(f"{category}: Page {page}/{max_pages} - {new_products_count} new products, {extraction_failures} extraction failures (Total: {len(all_category_products)})")
                    
                    # Update last successful page
                    last_successful_page = page
                    
                    # Only stop if we have multiple consecutive pages with no new products
                    if new_products_count == 0:
                        consecutive_empty_pages += 1
                        if consecutive_empty_pages >= 3:  # Increased threshold
                            print(f"🛑 Stopping {category} - no new products found in {consecutive_empty_pages} consecutive pages")
                            break
                    else:
                        consecutive_empty_pages = 0  # Reset if we found products
                    
                    # Add a small delay to prevent overwhelming the server
                    time.sleep(1)
                    
                except (TimeoutException, WebDriverException) as e:
                    print(f"⚠️ Timeout/WebDriver error on page {page}: {e}")
                    print(f"💾 Saved progress: {len(all_category_products)} products up to page {last_successful_page}")
                    
                    # Break inner loop to trigger retry
                    raise e
                    
                except Exception as e:
                    print(f"❌ Unexpected error on page {page}: {e}")
                    continue
            
            # If we get here, scraping completed successfully
            print(f"✅ {category}: Completed successfully - {len(all_category_products)} total products from {last_successful_page} pages")
            return all_category_products
            
        except (TimeoutException, WebDriverException) as e:
            print(f"⚠️ {category}: Connection timeout/error after page {last_successful_page}")
            retry_count += 1
            
            if retry_count < max_retries:
                wait_time = 30 * retry_count  # Exponential backoff
                print(f"🔄 Retrying in {wait_time} seconds... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"❌ {category}: Max retries reached. Returning partial results: {len(all_category_products)} products from {last_successful_page} pages")
                return all_category_products
                
        except Exception as e:
            print(f"❌ Unexpected error in {category}: {e}")
            retry_count += 1
            if retry_count < max_retries:
                print(f"Waiting 30 seconds before retry...")
                time.sleep(30)
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    print(f"⚠️ {category}: Returning partial results after all retries: {len(all_category_products)} products from {last_successful_page} pages")
    return all_category_products

def save_csv_to_both_locations(df, filename):
    """Save CSV to both local directory and app/public folder"""
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
    """Main function with retry logic and timeout handling"""
    categories = [
        ("https://www.tesco.com/groceries/en-GB/shop/fresh-food/all", "fresh-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/bakery/all", "bakery"),
        ("https://www.tesco.com/groceries/en-GB/shop/frozen-food/all", "frozen-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/treats-and-snacks/all", "treats-and-snacks"),
        ("https://www.tesco.com/groceries/en-GB/shop/food-cupboard/all", "food-cupboard"),
        ("https://www.tesco.com/groceries/en-GB/shop/drinks/all", "drinks"),
        ("https://www.tesco.com/groceries/en-GB/shop/baby-and-toddler/all", "baby-and-toddler")
    ]
    
    print("Starting optimized Tesco scraper with NO PAGE LIMITS...")
    start_time = time.time()
    
    # Use single worker like Sainsburys for stability
    with ThreadPoolExecutor(max_workers=1) as executor:
        future_to_category = {
            executor.submit(scrape_category_with_retry, url, name): name 
            for url, name in categories
        }
        
        for future in as_completed(future_to_category):
            category_name = future_to_category[future]
            try:
                category_products = future.result()
                
                with products_lock:
                    all_products.extend(category_products)
                    
                print(f"✅ {category_name}: {len(category_products)} products collected")
                    
            except Exception as e:
                print(f"❌ Category {category_name} failed: {e}")
    
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
        print(f"SCRAPING COMPLETED WITH NO PAGE LIMITS!")
        print(f"Total products: {len(df)}")
        print(f"Total time: {duration:.2f} seconds")
        print(f"Products per second: {len(df)/duration:.2f}")
        print(f"Files saved: tesco.csv (local) and ../app/public/tesco.csv")
        print(f"{'='*50}")
    else:
        print("❌ No products found.")

if __name__ == "__main__":
    scrape_tesco_optimized()