import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import time
import threading
import random
import re
import subprocess
import os
import shutil

# === Patch uc.Chrome destructor to prevent WinError 6 warnings ===
uc.Chrome.__del__ = lambda self: None

# Thread-safe list for collecting products
products_lock = threading.Lock()
all_products = []

# GitHub Actions timeout management
GITHUB_ACTIONS_TIMEOUT = 110 * 60  # 110 minutes in seconds
CATEGORY_TIMEOUT = 15 * 60  # 15 minutes per category max
start_time_global = None

def clean_price(price_text):
    """Extract numeric price from price text"""
    if not price_text:
        return None
    # Extract numeric value from price text
    price_match = re.search(r'£?(\d+\.?\d*)', str(price_text))
    return float(price_match.group(1)) if price_match else None

def check_timeout(category_start_time=None):
    """Check if we're approaching GitHub Actions timeout"""
    global start_time_global
    
    current_time = time.time()
    
    # Check global timeout (110 minutes)
    if start_time_global and (current_time - start_time_global) > (GITHUB_ACTIONS_TIMEOUT - 300):  # 5 min buffer
        print("⏰ Approaching GitHub Actions timeout - stopping")
        return True
    
    # Check category timeout (15 minutes)
    if category_start_time and (current_time - category_start_time) > CATEGORY_TIMEOUT:
        print("⏰ Category timeout reached - moving to next category")
        return True
    
    return False

def get_chrome_version():
    """Get installed Chrome version for GitHub Actions (Linux)"""
    try:
        # GitHub Actions method only
        result = subprocess.run(['google-chrome', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_match = re.search(r'(\d+)', result.stdout)
            if version_match:
                major_version = int(version_match.group(1))
                print(f"🌐 Detected Chrome version: {major_version}")
                return major_version
        
        print("⚠️ Could not detect Chrome version - using auto-detection")
        return None
        
    except Exception as e:
        print(f"⚠️ Error detecting Chrome version: {e}")
        return None

def cleanup_chromedriver_files():
    """Comprehensive cleanup for GitHub Actions (Linux)"""
    try:
        print("🧹 Starting ChromeDriver cleanup for GitHub Actions...")
        
        # Clean up Linux cache directories
        cleanup_paths = [
            os.path.join(os.path.expanduser("~"), ".cache", "undetected_chromedriver"),
            os.path.join(os.getcwd(), "chromedriver"),
            "/tmp/undetected_chromedriver"
        ]
        
        for path in cleanup_paths:
            if os.path.exists(path):
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                        print(f"   ✅ Removed file: {path}")
                    else:
                        shutil.rmtree(path)
                        print(f"   ✅ Removed directory: {path}")
                except Exception as e:
                    print(f"   ⚠️ Could not remove {path}: {e}")
        
        print("✅ ChromeDriver cleanup completed")
        time.sleep(0.5)
        
    except Exception as e:
        print(f"⚠️ Error during cleanup: {e}")

def setup_optimized_driver():
    """Setup Chrome driver optimized for GitHub Actions"""
    # Clean up any existing files
    cleanup_chromedriver_files()
    
    # Get Chrome version
    chrome_version = get_chrome_version()
    
    # Create ChromeOptions optimized for GitHub Actions
    options = uc.ChromeOptions()
    
    # GitHub Actions optimizations
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument("--disable-javascript")
    options.add_argument("--disable-css")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--window-size=1920,1080")
    
    # User agent for GitHub Actions
    options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")
    
    # Disable image loading for speed
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
    }
    options.add_experimental_option("prefs", prefs)
    
    # Unique temp directory
    import tempfile
    temp_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={temp_dir}")

    try:
        # Try with detected Chrome version first
        if chrome_version:
            print(f"🚀 Creating driver with Chrome version {chrome_version}")
            try:
                driver = uc.Chrome(version_main=chrome_version, options=options)
                print("✅ Driver created successfully with detected version")
                return driver
            except Exception as e:
                print(f"❌ Failed with detected version {chrome_version}: {e}")
        
        # Fallback: auto-detection
        print("🔄 Attempting auto-detection fallback...")
        driver = uc.Chrome(version_main=None, options=options)
        print("✅ Driver created successfully with auto-detection")
        return driver
        
    except Exception as e:
        print(f"❌ Failed to create driver: {e}")
        return None

def enhanced_scrape(driver):
    """Enhanced scraping with comprehensive selectors"""
    js_script = """
    var products = [];
    var tiles = document.querySelectorAll('div[class*="verticalTile"], div[class*="product"], [data-testid*="product"]');
    
    for(var i = 0; i < tiles.length; i++) {
        var tile = tiles[i];
        var name = null, price = null;
        
        // Try multiple name selectors
        var nameSelectors = [
            "a[class*='titleLink']", 
            "h3 a", "h2 a", "h4 a",
            "[data-testid*='name'] a",
            "[class*='name'] a",
            "[class*='title'] a",
            "a[href*='/product/']"
        ];
        
        for(var j = 0; j < nameSelectors.length; j++) {
            var nameEl = tile.querySelector(nameSelectors[j]);
            if(nameEl && nameEl.textContent && nameEl.textContent.trim()) {
                name = nameEl.textContent.trim();
                break;
            }
        }
        
        // Try multiple price selectors
        var priceSelectors = [
            "p[class*='priceText']", 
            "[data-testid*='price']",
            "[class*='price']",
            ".price",
            "span[class*='price']"
        ];
        
        for(var k = 0; k < priceSelectors.length; k++) {
            var priceEl = tile.querySelector(priceSelectors[k]);
            if(priceEl && priceEl.textContent && priceEl.textContent.trim()) {
                var priceText = priceEl.textContent.trim();
                if(priceText.includes('£') && priceText.length > 1) {
                    price = priceText;
                    break;
                }
            }
        }
        
        if(name && price) {
            products.push({name: name, price: price});
        }
    }
    
    return products;
    """
    
    try:
        products = driver.execute_script(js_script)
        return products if products else []
    except Exception as e:
        print(f"⚠️ JavaScript execution failed: {e}")
        return []

def scrape_single_category(base_url, category_name):
    """Scrape a single category with unlimited pages but timeout protection"""
    driver = setup_optimized_driver()
    if not driver:
        print(f"❌ Failed to create driver for {category_name}")
        return []
    
    category_products = []
    category_start_time = time.time()
    
    try:
        # Extract category name from URL
        category = base_url.split('/shop/')[1].split('/')[0]
        print(f"🛒 Starting category: {category} (timeout: {CATEGORY_TIMEOUT//60}min)")
        
        page = 1
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while True:  # No page limit!
            try:
                # Check timeouts before each page
                if check_timeout(category_start_time):
                    print(f"   ⏰ Timeout reached for {category} at page {page}")
                    break
                
                url = f"{base_url}?page={page}"
                print(f"   📄 Page {page}... (elapsed: {(time.time() - category_start_time)/60:.1f}min)")
                
                driver.get(url)
                time.sleep(1.5)  # Reduced delay for speed

                # Wait for products to load
                try:
                    WebDriverWait(driver, 10).until(  # Reduced timeout
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='verticalTile'], div[class*='product']"))
                    )
                    time.sleep(0.5)
                except Exception:
                    print(f"   ⏭️ No products found on page {page}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        print(f"   🛑 {consecutive_failures} consecutive failures - stopping")
                        break
                    page += 1
                    continue
                
                # Extract products
                products_data = enhanced_scrape(driver)
                
                if not products_data:
                    print(f"   ⏭️ No products extracted from page {page}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        print(f"   🛑 {consecutive_failures} consecutive failures - stopping")
                        break
                    page += 1
                    continue
                
                # Reset failure counter on success
                consecutive_failures = 0
                
                # Process products
                page_products = []
                for product in products_data:
                    page_products.append({
                        "Category": category,
                        "Name": product["name"],
                        "Price": product["price"]
                    })
                
                category_products.extend(page_products)
                print(f"   ✅ {category}: Page {page} - {len(page_products)} products (total: {len(category_products)})")
                
                # Simple pagination check
                try:
                    # Check if there are next page elements
                    next_elements = driver.find_elements(By.CSS_SELECTOR, "a[aria-label*='Next'], button[aria-label*='Next']")
                    has_next = any(el.is_displayed() and el.is_enabled() for el in next_elements)
                    
                    if not has_next:
                        print(f"   🏁 {category}: No more pages after page {page}")
                        break
                        
                except Exception:
                    # If we can't detect pagination, continue but check for empty pages
                    if page >= 10:  # Safety check after 10 pages
                        print(f"   🔍 {category}: Pagination detection failed after page {page}")
                        break
                
                page += 1
                time.sleep(1)  # Minimal delay
                
            except Exception as e:
                print(f"   ❌ Error on page {page}: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    print(f"   🛑 Too many consecutive errors - stopping")
                    break
                page += 1
        
        duration = time.time() - category_start_time
        print(f"🎯 {category}: Completed - {len(category_products)} products from {page-1} pages in {duration/60:.1f}min")
        return category_products
        
    except Exception as e:
        print(f"❌ Error in {category}: {e}")
        return []
    finally:
        try:
            driver.quit()
        except:
            pass
        time.sleep(0.5)  # Reduced cleanup delay

def save_csv_to_both_locations(df, filename):
    """Save CSV for GitHub Actions"""
    # Save to local directory
    local_path = f"{filename}.csv"
    df.to_csv(local_path, index=False, encoding="utf-8")
    print(f"✅ Saved to local: {local_path}")
    
    # Save to app/public directory
    public_dir = "../app/public"
    try:
        os.makedirs(public_dir, exist_ok=True)
        public_path = os.path.join(public_dir, f"{filename}.csv")
        df.to_csv(public_path, index=False, encoding="utf-8")
        print(f"✅ Saved to public: {public_path}")
    except Exception as e:
        print(f"⚠️ Could not save to public directory: {e}")

def scrape_tesco_optimized():
    """Main function with unlimited pages but timeout protection"""
    global start_time_global
    start_time_global = time.time()
    
    categories = [
        ("https://www.tesco.com/groceries/en-GB/shop/fresh-food/all", "fresh-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/bakery/all", "bakery"),
        ("https://www.tesco.com/groceries/en-GB/shop/frozen-food/all", "frozen-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/treats-and-snacks/all", "treats-and-snacks"),
        ("https://www.tesco.com/groceries/en-GB/shop/food-cupboard/all", "food-cupboard"),
        ("https://www.tesco.com/groceries/en-GB/shop/drinks/all", "drinks"),
        ("https://www.tesco.com/groceries/en-GB/shop/baby-and-toddler/all", "baby-and-toddler")
    ]
    
    print("🛒 TESCO SCRAPER - UNLIMITED PAGES WITH TIMEOUT PROTECTION")
    print(f"📋 Categories: {len(categories)}")
    print(f"🔧 Mode: Sequential processing")
    print(f"📄 Pages: UNLIMITED (until exhausted or timeout)")
    print(f"⏰ Global timeout: {GITHUB_ACTIONS_TIMEOUT//60}min")
    print(f"⏰ Per category timeout: {CATEGORY_TIMEOUT//60}min")
    print(f"🛡️ Smart failure detection: 3 consecutive failures = stop")
    print("")
    
    # Sequential processing with timeout protection
    for i, (url, name) in enumerate(categories):
        # Check global timeout before starting each category
        if check_timeout():
            print(f"🛑 Global timeout reached - stopping at category {i+1}/{len(categories)}")
            break
        
        print(f"📂 Processing category {i+1}/{len(categories)}: {name}")
        try:
            category_products = scrape_single_category(url, name)
            with products_lock:
                all_products.extend(category_products)
        except Exception as e:
            print(f"❌ Category {name} failed: {e}")
        
        # Quick timeout check between categories
        elapsed = time.time() - start_time_global
        remaining = (GITHUB_ACTIONS_TIMEOUT - elapsed) / 60
        print(f"⏱️ Time remaining: {remaining:.1f} minutes\n")
    
    # Save results
    if all_products:
        df = pd.DataFrame(all_products)
        
        # Clean data
        df = df.dropna(subset=['Name', 'Price'])
        df = df[df['Name'].str.strip() != '']
        df = df[df['Price'].str.strip() != '']
        df = df.drop_duplicates(subset=['Name', 'Price'])
        
        # Add price numeric for sorting
        df['Price_Numeric'] = df['Price'].apply(clean_price)
        df = df.sort_values(['Category', 'Name']).reset_index(drop=True)
        
        # Save files
        save_csv_to_both_locations(df, "tesco")
        
        end_time = time.time()
        duration = end_time - start_time_global
        
        print(f"\n{'='*60}")
        print(f"🎉 TESCO SCRAPING COMPLETED!")
        print(f"📦 Total products: {len(df)}")
        print(f"⏱️ Duration: {duration:.1f}s ({duration/60:.1f}m)")
        print(f"🚀 Products per minute: {len(df)/(duration/60):.1f}")
        print(f"📊 Categories scraped:")
        
        category_counts = df['Category'].value_counts()
        for category, count in category_counts.items():
            print(f"   • {category}: {count} products")
        print("="*60)
        
    else:
        print("❌ No products scraped - creating test CSV")
        test_df = pd.DataFrame([{
            'Category': 'Test',
            'Name': 'GitHub Actions Test - No Data',
            'Price': '£0.00'
        }])
        save_csv_to_both_locations(test_df, "tesco")
        print("✅ Test CSV created for GitHub Actions compatibility")

if __name__ == "__main__":
    scrape_tesco_optimized()