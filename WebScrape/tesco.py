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
    """Setup Chrome driver with performance optimizations and dynamic version detection"""
    # Get Chrome version
    chrome_version = get_chrome_version()
    
    def create_fresh_options():
        """Create completely fresh options for each attempt"""
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
        return options

    try:
        # Try with detected Chrome version first
        if chrome_version:
            print(f"Attempting to create driver with Chrome version {chrome_version}")
            try:
                driver = uc.Chrome(version_main=chrome_version, options=create_fresh_options())
                print("✅ Driver created successfully with detected version")
                return driver
            except Exception as e:
                print(f"Failed with detected version {chrome_version}: {e}")
        
        # Fallback: Let undetected-chromedriver auto-detect with fresh options
        print("Attempting auto-detection fallback...")
        driver = uc.Chrome(version_main=None, options=create_fresh_options())
        print("✅ Driver created successfully with auto-detection")
        return driver
        
    except Exception as e:
        print(f"Failed to create driver: {e}")
        return None

def scrape_single_category(base_url, category_name):
    """Scrape a single category with debugging"""
    driver = setup_optimized_driver()
    if driver is None:
        print(f"Failed to create driver for {category_name}")
        return []
        
    category_products = []
    
    try:
        category = base_url.split('/shop/')[1].split('/')[0]
        print(f"Starting category: {category}")
        
        # Load first page
        url = f"{base_url}?page=1"
        print(f"Loading URL: {url}")
        driver.get(url)
        
        # Wait longer and check page load
        time.sleep(1)
        
        # Debug: Check what actually loaded
        page_title = driver.title
        print(f"Page title: {page_title}")
        
        # Try multiple selectors for products
        product_selectors = [
            "div[class*='verticalTile']",
            "[data-testid*='product']", 
            ".product-tile",
            ".product",
            "[class*='product']",
            ".tile"
        ]
        
        products_found = False
        working_selector = None
        
        for selector in product_selectors:
            try:
                WebDriverWait(driver, 10).until(
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
            # Save page source for debugging
            try:
                with open(f"debug_{category}.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print(f"Saved page source to debug_{category}.html for inspection")
            except:
                pass
            return []
        
        # Get pagination info
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
        
        print(f"{category}: Found {max_pages} pages")
        
        # Scrape pages
        for page in range(1, max_pages + 1):
            if page > 1:
                url = f"{base_url}?page={page}"
                driver.get(url)
                time.sleep(1)
            
            # Use the working selector
            product_tiles = driver.find_elements(By.CSS_SELECTOR, working_selector)
            
            if not product_tiles:
                print(f"{category}: No products found on page {page}")
                break
            
            # Extract product data with multiple selector strategies
            page_products = []
            for product in product_tiles:
                try:
                    # Try multiple name selectors
                    name = "N/A"
                    name_selectors = [
                        "a[class*='titleLink']",
                        "h3", "h2", "h4",
                        "[data-testid*='name']",
                        "[class*='name']",
                        "[class*='title']"
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
                        "span[class*='price']"
                    ]
                    
                    for price_sel in price_selectors:
                        try:
                            price_elem = product.find_element(By.CSS_SELECTOR, price_sel)
                            if price_elem and price_elem.text.strip():
                                price = price_elem.text.strip()
                                break
                        except:
                            continue
                    
                    if name != "N/A" and price != "N/A":
                        page_products.append({
                            "Category": category,
                            "Name": name,
                            "Price": price
                        })
                except Exception as e:
                    continue
                
            category_products.extend(page_products)
            print(f"{category}: Page {page}/{max_pages} - {len(page_products)} products")
        
        print(f"{category}: Completed - {len(category_products)} total products")
        return category_products
        
    except Exception as e:
        print(f"Error in {category}: {e}")
        return []
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

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
    """Main function with single worker like Sainsburys"""
    categories = [
        ("https://www.tesco.com/groceries/en-GB/shop/fresh-food/all", "fresh-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/bakery/all", "bakery"),
        ("https://www.tesco.com/groceries/en-GB/shop/frozen-food/all", "frozen-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/treats-and-snacks/all", "treats-and-snacks"),
        ("https://www.tesco.com/groceries/en-GB/shop/food-cupboard/all", "food-cupboard"),
        ("https://www.tesco.com/groceries/en-GB/shop/drinks/all", "drinks"),
        ("https://www.tesco.com/groceries/en-GB/shop/baby-and-toddler/all", "baby-and-toddler")
    ]
    
    print("Starting optimized Tesco scraper with single worker (like Sainsburys)...")
    start_time = time.time()
    
    # Process categories sequentially like sainsburys.py (no threading)
    for i, (url, name) in enumerate(categories, 1):
        print(f"\n--- Processing category {i}/{len(categories)}: {name} ---")
        category_products = scrape_single_category(url, name)
        
        # Add to global products list (no lock needed for sequential processing)
        all_products.extend(category_products)
        print(f"Category {name} completed: {len(category_products)} products")
    
    # Save results
    if all_products:
        df = pd.DataFrame(all_products)
        
        # Clean data
        df = df.dropna(subset=['Name', 'Price'])
        df = df[df['Name'].str.strip() != '']
        df = df[df['Price'].str.strip() != '']
        df = df.drop_duplicates(subset=['Name', 'Price'])
        
        # Save to both locations
        save_csv_to_both_locations(df, "tesco")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'='*50}")
        print(f"SCRAPING COMPLETED!")
        print(f"Total products: {len(all_products)}")
        print(f"Total time: {duration:.2f} seconds")
        print(f"Products per second: {len(all_products)/duration:.2f}")
        print(f"Files saved: tesco.csv (local) and ../app/public/tesco.csv")
        print(f"{'='*50}")
    else:
        print("No products found.")

if __name__ == "__main__":
    scrape_tesco_optimized()