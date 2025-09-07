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
import psutil
import shutil

# === Patch uc.Chrome destructor to prevent WinError 6 warnings ===
uc.Chrome.__del__ = lambda self: None

# Thread-safe list for collecting products
products_lock = threading.Lock()
all_products = []

def clean_price(price_text):
    """Extract numeric price from price text"""
    if not price_text:
        return None
    # Extract numeric value from price text
    price_match = re.search(r'£?(\d+\.?\d*)', str(price_text))
    return float(price_match.group(1)) if price_match else None

def get_chrome_version():
    """Get installed Chrome version on Windows"""
    try:
        # Try registry method first
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
        
        # Try PowerShell method
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
        
        # Try Linux/GitHub Actions method
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
        
        print("Could not detect Chrome version - will use auto-detection")
        return None
        
    except Exception as e:
        print(f"Error detecting Chrome version: {e}")
        return None

def kill_chrome_processes():
    """Kill all Chrome and ChromeDriver processes"""
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if any(name in proc.info['name'].lower() for name in ['chrome', 'chromedriver']):
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(1)
    except Exception as e:
        print(f"Error killing processes: {e}")

def cleanup_chromedriver_files():
    """Comprehensive cleanup of ChromeDriver files"""
    try:
        print("🧹 Starting comprehensive ChromeDriver cleanup...")
        
        # Kill all Chrome processes first
        kill_chrome_processes()
        
        # Clean up undetected_chromedriver directory
        cleanup_paths = [
            os.path.join(os.path.expanduser("~"), "appdata", "roaming", "undetected_chromedriver"),
            os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "undetected_chromedriver"),
            os.path.join(os.path.expanduser("~"), ".cache", "undetected_chromedriver"),
            os.path.join(os.getcwd(), "chromedriver.exe"),
            os.path.join(os.getcwd(), "chromedriver"),
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
        time.sleep(1)
        
    except Exception as e:
        print(f"Error during cleanup: {e}")

def setup_optimized_driver():
    """Setup optimized Chrome driver with proper version handling and conflict avoidance"""
    # Add a small random delay to avoid simultaneous access
    time.sleep(random.uniform(0.5, 2.0))
    
    # Clean up any existing conflicting files first
    cleanup_chromedriver_files()
    
    # Get Chrome version
    chrome_version = get_chrome_version()
    
    # Create completely fresh ChromeOptions for each call
    options = uc.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-extensions")
    options.add_argument("--headless")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    
    # Add unique user data directory for each instance
    import tempfile
    temp_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={temp_dir}")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")

    try:
        # Try with detected Chrome version first
        if chrome_version:
            print(f"Attempting to create driver with Chrome version {chrome_version}")
            try:
                driver = uc.Chrome(version_main=chrome_version, options=options)
                driver.delete_all_cookies()
                print("✅ Driver created successfully with detected version")
                return driver
            except Exception as e:
                print(f"Failed with detected version {chrome_version}: {e}")
        
        # Fallback: Let undetected-chromedriver auto-detect
        print("Attempting auto-detection fallback...")
        # Create fresh options again for fallback
        options2 = uc.ChromeOptions()
        options2.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        options2.add_argument("--no-sandbox")
        options2.add_argument("--disable-dev-shm-usage")
        options2.add_argument("--disable-gpu")
        options2.add_argument("--headless")
        
        # Different temp directory for fallback
        temp_dir2 = tempfile.mkdtemp()
        options2.add_argument(f"--user-data-dir={temp_dir2}")
        
        driver = uc.Chrome(version_main=None, options=options2)
        driver.delete_all_cookies()
        print("✅ Driver created successfully with auto-detection")
        return driver
        
    except Exception as e:
        print(f"Failed to create driver: {e}")
        return None

def enhanced_scrape(driver):
    """Enhanced scraping with comprehensive selectors"""
    js_script = """
    var products = [];
    var tiles = document.querySelectorAll('div[class*="verticalTile"], div[class*="product"], [data-testid*="product"]');
    
    console.log('Found ' + tiles.length + ' product containers');
    
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
    
    console.log('Successfully extracted ' + products.length + ' products');
    return products;
    """
    
    try:
        products = driver.execute_script(js_script)
        return products if products else []
    except Exception as e:
        print(f"⚠️ JavaScript execution failed: {e}")
        return []

def scrape_single_category(base_url, category_name):
    """Scrape a single category with optimizations"""
    driver = setup_optimized_driver()
    if not driver:
        print(f"❌ Failed to create driver for {category_name}")
        return []
    
    category_products = []
    
    try:
        # Extract simple category name from URL
        category = base_url.split('/shop/')[1].split('/')[0]
        print(f"🛒 Starting category: {category}")
        
        # Start with page 1
        page = 1
        # Removed max_pages limit - will scrape all available pages
        
        while True:  # Continue until no more pages found
            try:
                url = f"{base_url}?page={page}"
                print(f"   📄 Scraping page {page}...")
                
                driver.get(url)
                time.sleep(random.uniform(1.0, 2.0))

                # Wait for products to load
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='verticalTile'], div[class*='product']"))
                    )
                    time.sleep(1)
                except Exception:
                    print(f"   No products found on page {page}")
                    break
                
                # Use enhanced scraping
                products_data = enhanced_scrape(driver)
                
                if not products_data:
                    print(f"   No products extracted from page {page}")
                    break
                
                # Process products
                page_products = []
                for product in products_data:
                    page_products.append({
                        "Category": category,
                        "Name": product["name"],
                        "Price": product["price"]
                    })
                
                category_products.extend(page_products)
                print(f"   {category}: Page {page} - {len(page_products)} products")
                
                # Check for next page - look for pagination
                try:
                    # Look for next page button or pagination links
                    next_page_exists = False
                    
                    # Check for next button
                    next_buttons = driver.find_elements(By.CSS_SELECTOR, "a[aria-label='Next'], button[aria-label='Next'], .pagination a[rel='next']")
                    if next_buttons:
                        for btn in next_buttons:
                            if btn.is_displayed() and btn.is_enabled() and 'disabled' not in btn.get_attribute('class'):
                                next_page_exists = True
                                break
                    
                    # Check for page links
                    if not next_page_exists:
                        page_links = driver.find_elements(By.CSS_SELECTOR, "a[data-page], .pagination a")
                        for link in page_links:
                            try:
                                page_num = int(link.get_attribute("data-page") or link.text)
                                if page_num > page:
                                    next_page_exists = True
                                    break
                            except (TypeError, ValueError):
                                continue
                    
                    if not next_page_exists:
                        print(f"   {category}: No more pages after page {page}")
                        break
                        
                except Exception as e:
                    print(f"   ⚠️ Error checking pagination: {e}")
                    # If pagination check fails, try a few more pages before giving up
                    if page >= 10:  # Only give up after trying at least 10 pages
                        print(f"   {category}: Stopping after 10+ pages due to pagination errors")
                        break
                
                page += 1
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"   ❌ Error on page {page}: {e}")
                break
        
        print(f"✅ {category}: Completed - {len(category_products)} total products from {page-1} pages")
        return category_products
        
    except Exception as e:
        print(f"❌ Error in {category}: {e}")
        return []
    finally:
        try:
            driver.quit()
        except:
            pass
        # Clean up after each category
        time.sleep(1)

def save_csv_to_both_locations(df, filename):
    """Save CSV to both local directory and app/public folder"""
    # Save to local directory
    local_path = f"{filename}.csv"
    df.to_csv(local_path, index=False, encoding="utf-8")
    print(f"✅ Saved to local: {local_path}")
    
    # Save to app/public directory
    public_dir = "../app/public"
    if not os.path.exists(public_dir):
        try:
            os.makedirs(public_dir, exist_ok=True)
        except:
            pass
    
    if os.path.exists(public_dir):
        public_path = os.path.join(public_dir, f"{filename}.csv")
        df.to_csv(public_path, index=False, encoding="utf-8")
        print(f"✅ Saved to public: {public_path}")
    else:
        print("⚠️ Could not create public directory")

def scrape_tesco_optimized():
    """Main function with reduced parallel processing to avoid conflicts"""
    categories = [
        ("https://www.tesco.com/groceries/en-GB/shop/fresh-food/all", "fresh-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/bakery/all", "bakery"),
        ("https://www.tesco.com/groceries/en-GB/shop/frozen-food/all", "frozen-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/treats-and-snacks/all", "treats-and-snacks"),
        ("https://www.tesco.com/groceries/en-GB/shop/food-cupboard/all", "food-cupboard"),
        ("https://www.tesco.com/groceries/en-GB/shop/drinks/all", "drinks"),
        ("https://www.tesco.com/groceries/en-GB/shop/baby-and-toddler/all", "baby-and-toddler")
    ]
    
    print("🛒 Starting optimized Tesco scraper with unlimited pagination...")
    print(f"📋 Categories to scrape: {len(categories)}")
    print(f"🧵 Max workers: 1 (reduced to avoid conflicts)")
    print(f"🔧 ChromeDriver: Enhanced cleanup and version detection")
    print(f"📄 Pagination: Complete scraping of ALL pages")
    print(f"🚫 No page limit - will scrape until exhausted\n")
    
    start_time = time.time()
    
    # Reduce to 1 worker to avoid ChromeDriver conflicts
    with ThreadPoolExecutor(max_workers=1) as executor:
        # Submit all category scraping tasks
        future_to_category = {
            executor.submit(scrape_single_category, url, name): name 
            for url, name in categories
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_category):
            category_name = future_to_category[future]
            try:
                category_products = future.result()
                
                # Thread-safe addition to global products list
                with products_lock:
                    all_products.extend(category_products)
                    
            except Exception as e:
                print(f"Category {category_name} failed: {e}")
    
    # Save results
    if all_products:
        df = pd.DataFrame(all_products)
        
        # Clean data
        df = df.dropna(subset=['Name', 'Price'])
        df = df[df['Name'].str.strip() != '']
        df = df[df['Price'].str.strip() != '']
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['Name', 'Price'])
        
        # Add cleaned price for sorting
        df['Price_Numeric'] = df['Price'].apply(clean_price)
        
        # Sort by category and name
        df = df.sort_values(['Category', 'Name']).reset_index(drop=True)
        
        # Save to both locations
        save_csv_to_both_locations(df, "tesco")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'='*60}")
        print(f"🎉 TESCO SCRAPING COMPLETED!")
        print(f"📦 Total unique products: {len(df)}")
        print(f"⏱️ Total time: {duration:.2f} seconds ({duration/60:.1f} minutes)")
        if duration > 0:
            print(f"🚀 Products per second: {len(df)/duration:.2f}")
        print(f"📊 Results by category:")
        
        category_counts = df['Category'].value_counts()
        for category, count in category_counts.items():
            print(f"   {category}: {count} products")
        print("="*60)
    else:
        print("❌ No products found - this may indicate anti-bot measures or site changes")
        # Create a minimal CSV for testing
        test_df = pd.DataFrame([{
            'Category': 'Test',
            'Name': 'Test Product - No Data Found',
            'Price': '£1.00'
        }])
        save_csv_to_both_locations(test_df, "tesco")
        print("✅ Minimal test CSV created for pipeline compatibility")

if __name__ == "__main__":
    scrape_tesco_optimized()