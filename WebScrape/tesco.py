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
    """Get installed Chrome version - adapted from sainsburys.py"""
    try:
        # Try Linux/GitHub Actions method first
        try:
            result = subprocess.run(['google-chrome', '--version'], 
                                  capture_output=True, text=True, timeout=10)
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

def setup_stealth_driver():
    """Setup stealth driver with maximum anti-detection measures"""
    with driver_creation_lock:
        time.sleep(random.uniform(2, 5))  # Random delay between driver creation
        
        chrome_version = get_chrome_version()
        
        def create_stealth_options():
            options = uc.ChromeOptions()
            
            # Basic stealth options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--disable-features=VizDisplayCompositor')
            
            # Enhanced stealth for Linux/GitHub Actions
            options.add_argument('--headless=new')  # Use new headless mode
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--start-maximized')
            
            # Anti-detection measures
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-automation')
            options.add_argument('--disable-dev-tools')
            options.add_argument('--no-first-run')
            options.add_argument('--no-default-browser-check')
            options.add_argument('--disable-default-apps')
            
            # Realistic user agent rotation
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
            options.add_argument(f'--user-agent={random.choice(user_agents)}')
            
            # Human-like preferences
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0,
                "profile.managed_default_content_settings.images": 2,  # Disable images for speed
                "profile.default_content_setting_values.geolocation": 2,
            }
            options.add_experimental_option("prefs", prefs)
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            return options

        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                print(f"Creating stealth driver (attempt {attempt + 1}/{max_attempts})")
                
                # Try with detected version first
                if chrome_version and attempt < 2:
                    try:
                        driver = uc.Chrome(version_main=chrome_version, options=create_stealth_options())
                    except Exception as e:
                        print(f"Failed with version {chrome_version}: {e}")
                        continue
                else:
                    # Auto-detection fallback
                    driver = uc.Chrome(options=create_stealth_options())
                
                # Configure timeouts
                driver.set_page_load_timeout(60)
                driver.implicitly_wait(10)
                
                # Remove automation indicators
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": driver.execute_script("return navigator.userAgent").replace("HeadlessChrome", "Chrome")
                })
                
                print("✅ Stealth driver created successfully")
                return driver
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    wait_time = (attempt + 1) * 10
                    print(f"Waiting {wait_time} seconds before next attempt...")
                    time.sleep(wait_time)
        
        print("❌ Failed to create stealth driver after all attempts")
        return None

def test_connection_and_scrape(base_url, category_name, max_retries=3):
    """Test connection and scrape with enhanced stealth measures"""
    category = base_url.split('/shop/')[1].split('/')[0]
    print(f"Starting category: {category}")
    
    all_category_products = []
    
    for retry_count in range(max_retries):
        driver = setup_stealth_driver()
        if driver is None:
            print(f"Failed to create driver for {category_name} (attempt {retry_count + 1})")
            continue
        
        try:
            print(f"Attempt {retry_count + 1}: Testing connection to {category}")
            
            # First, try to access the main Tesco page to test connection
            print("Testing connection to main Tesco page...")
            driver.get("https://www.tesco.com")
            time.sleep(random.uniform(3, 6))
            
            # Check if we can access the page
            if "tesco" not in driver.title.lower():
                print("❌ Failed to access main Tesco page")
                raise Exception("Cannot access Tesco main page")
            
            print("✅ Successfully accessed main Tesco page")
            
            # Handle cookies if present
            try:
                cookie_selectors = [
                    "#onetrust-accept-btn-handler",
                    "[id*='cookie'] button",
                    "[class*='cookie'] button",
                    "button[class*='accept']",
                    "[data-testid*='accept']"
                ]
                
                for selector in cookie_selectors:
                    try:
                        cookie_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        if cookie_btn.is_displayed():
                            print("🍪 Accepting cookies...")
                            driver.execute_script("arguments[0].click();", cookie_btn)
                            time.sleep(2)
                            break
                    except:
                        continue
            except:
                print("No cookies to handle")
            
            # Now try to access the category page
            print(f"Accessing category page: {category}")
            category_url = f"{base_url}?page=1"
            driver.get(category_url)
            time.sleep(random.uniform(4, 8))
            
            # Check page title
            page_title = driver.title
            print(f"Page title: {page_title}")
            
            # Check for blocking indicators
            page_source = driver.page_source.lower()
            if any(indicator in page_source for indicator in [
                "access denied", "blocked", "security check", "unusual traffic", 
                "robot", "automated", "captcha", "verification"
            ]):
                print("❌ Page indicates blocking or security check")
                raise Exception("Page blocked or security check detected")
            
            # Try to find products
            product_selectors = [
                "div[class*='verticalTile']",
                "[data-testid*='product']",
                ".product-tile",
                ".product",
                "[class*='product']"
            ]
            
            products_found = False
            working_selector = None
            
            for selector in product_selectors:
                try:
                    products = WebDriverWait(driver, 15).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    if len(products) > 5:  # Need at least 5 products to consider it working
                        print(f"✅ Found {len(products)} products using selector: {selector}")
                        products_found = True
                        working_selector = selector
                        break
                except:
                    continue
            
            if not products_found:
                print(f"❌ No products found on category page")
                raise Exception("No products found")
            
            # If we get here, connection is working - proceed with limited scraping
            print(f"✅ Connection successful! Starting limited scraping for {category}")
            
            # Scrape first few pages only to test
            max_test_pages = 5
            seen_products = set()
            
            for page in range(1, max_test_pages + 1):
                try:
                    if page > 1:
                        url = f"{base_url}?page={page}"
                        driver.get(url)
                        time.sleep(random.uniform(3, 6))
                    
                    products = driver.find_elements(By.CSS_SELECTOR, working_selector)
                    
                    page_products = []
                    for product in products:
                        try:
                            # Extract name
                            name = "N/A"
                            name_selectors = ["a[class*='titleLink']", "h3", "h2", "[class*='name']"]
                            for name_sel in name_selectors:
                                try:
                                    name_elem = product.find_element(By.CSS_SELECTOR, name_sel)
                                    if name_elem and name_elem.text.strip():
                                        name = name_elem.text.strip()
                                        break
                                except:
                                    continue
                            
                            # Extract price
                            price = "N/A"
                            price_selectors = ["p[class*='priceText']", "[data-testid*='price']", "[class*='price']"]
                            for price_sel in price_selectors:
                                try:
                                    price_elem = product.find_element(By.CSS_SELECTOR, price_sel)
                                    if price_elem and price_elem.text.strip() and '£' in price_elem.text:
                                        price = price_elem.text.strip()
                                        break
                                except:
                                    continue
                            
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
                    
                    # Add human-like delay
                    time.sleep(random.uniform(2, 4))
                
                except Exception as e:
                    print(f"Error on page {page}: {e}")
                    break
            
            print(f"✅ {category}: Test completed - {len(all_category_products)} products")
            return all_category_products
            
        except Exception as e:
            print(f"⚠️ {category}: Attempt {retry_count + 1} failed: {e}")
            if retry_count < max_retries - 1:
                wait_time = (retry_count + 1) * 30
                print(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    print(f"❌ {category}: All attempts failed")
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
    """Main function with enhanced stealth and connection testing"""
    categories = [
        ("https://www.tesco.com/groceries/en-GB/shop/fresh-food/all", "fresh-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/bakery/all", "bakery"),
        ("https://www.tesco.com/groceries/en-GB/shop/frozen-food/all", "frozen-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/treats-and-snacks/all", "treats-and-snacks"),
        ("https://www.tesco.com/groceries/en-GB/shop/food-cupboard/all", "food-cupboard"),
        ("https://www.tesco.com/groceries/en-GB/shop/drinks/all", "drinks"),
        ("https://www.tesco.com/groceries/en-GB/shop/baby-and-toddler/all", "baby-and-toddler")
    ]
    
    print("Starting enhanced stealth Tesco scraper with connection testing...")
    start_time = time.time()
    
    # Use single worker for maximum stealth
    with ThreadPoolExecutor(max_workers=1) as executor:
        future_to_category = {
            executor.submit(test_connection_and_scrape, url, name): name 
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
        print(f"ENHANCED STEALTH SCRAPING COMPLETED!")
        print(f"Total products: {len(df)}")
        print(f"Total time: {duration:.2f} seconds")
        print(f"Products per second: {len(df)/duration:.2f}")
        print(f"Files saved: tesco.csv (local) and ../app/public/tesco.csv")
        print(f"{'='*50}")
    else:
        print("❌ No products found - creating minimal test CSV")
        # Create a minimal CSV so the workflow doesn't fail completely
        test_df = pd.DataFrame([{
            'Category': 'Test',
            'Name': 'Connection Test Failed - Tesco Blocking',
            'Price': '£0.00'
        }])
        save_csv_to_both_locations(test_df, "tesco")

if __name__ == "__main__":
    scrape_tesco_optimized()