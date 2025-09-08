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
import psutil
import shutil
import random

# === Patch uc.Chrome destructor to prevent WinError 6 warnings ===
uc.Chrome.__del__ = lambda self: None

# Thread-safe list for collecting products
products_lock = threading.Lock()
driver_creation_lock = threading.Lock()
all_products = []

def clean_price(price_text):
    """Extract numeric price from price text"""
    if not price_text:
        return None
    # Extract numeric value from price text
    price_match = re.search(r'£?(\d+\.?\d*)', str(price_text))
    return float(price_match.group(1)) if price_match else None

def get_chrome_version():
    """Get installed Chrome version - cross-platform"""
    try:
        # Try Linux/GitHub Actions method first
        try:
            result = subprocess.run(['google-chrome', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Extract the actual version number
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
        kill_chrome_processes()
        
        cleanup_paths = [
            os.path.join(os.path.expanduser("~"), "appdata", "roaming", "undetected_chromedriver"),
            os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "undetected_chromedriver"),
            os.path.join(os.path.expanduser("~"), ".cache", "undetected_chromedriver"),
            os.path.join(os.path.expanduser("~"), ".local", "share", "undetected_chromedriver"),
            os.path.join(os.getcwd(), "chromedriver.exe"),
            os.path.join(os.getcwd(), "chromedriver"),
        ]
        
        for path in cleanup_paths:
            if os.path.exists(path):
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                    else:
                        shutil.rmtree(path)
                except:
                    pass
        
        time.sleep(1)
        
    except Exception as e:
        print(f"Error during cleanup: {e}")

def setup_optimized_driver():
    """Setup Chrome driver with performance optimizations and thread-safe creation"""
    with driver_creation_lock:
        time.sleep(random.uniform(0.5, 1.5))
        
        # Clean up any existing conflicting files first
        cleanup_chromedriver_files()
        
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
            options.add_argument('--timeout=300')
            options.add_argument('--page-load-strategy=none')
            return options

        try:
            # Try with detected Chrome version first
            if chrome_version:
                print(f"Attempting to create driver with Chrome version {chrome_version}")
                try:
                    driver = uc.Chrome(version_main=chrome_version, options=create_options())
                    print("✅ Driver created successfully with detected version")
                    return driver
                except Exception as e:
                    print(f"Failed with detected version {chrome_version}: {e}")
            
            # Fallback: Let undetected-chromedriver auto-detect
            print("Attempting auto-detection fallback...")
            driver = uc.Chrome(version_main=None, options=create_options())
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
    """Scrape a single category with enhanced debugging"""
    driver = setup_optimized_driver()
    if driver is None:
        print(f"❌ Failed to create driver for {category_name}")
        return []
        
    category_products = []
    
    try:
        category = base_url.split('/shop/')[1].split('/')[0]
        print(f"🛒 Starting category: {category}")
        
        # Start with page 1
        page = 1
        max_pages = 50  # Safety limit
        
        while page <= max_pages:
            try:
                url = f"{base_url}?page={page}"
                print(f"   📄 Loading page {page}: {url}")
                driver.get(url)
                
                # Wait for products to load
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='verticalTile'], div[class*='product']"))
                    )
                    time.sleep(random.uniform(1, 2))
                except Exception:
                    print(f"   ⚠️ No products found on page {page} - ending pagination")
                    break
                
                # Use enhanced scraping
                products_data = enhanced_scrape(driver)
                
                if not products_data:
                    print(f"   ⚠️ No products extracted from page {page} - ending pagination")
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
                print(f"   ✅ {category}: Page {page} - {len(page_products)} products")
                
                # Simple pagination check - if we got fewer than expected products, probably last page
                if len(page_products) < 10:  # Threshold for last page
                    print(f"   ℹ️ {category}: Small page size ({len(page_products)}), likely last page")
                    break
                
                page += 1
                time.sleep(random.uniform(1, 3))
                
                # Safety check - don't go beyond reasonable limits
                if page > max_pages:
                    print(f"   ⚠️ {category}: Reached safety limit of {max_pages} pages")
                    break
                
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

def save_csv_to_both_locations(df, filename):
    """Save CSV to both local directory and app/public folder"""
    local_path = f"{filename}.csv"
    df.to_csv(local_path, index=False, encoding="utf-8")
    print(f"✅ Saved to local: {local_path}")
    
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
    """Main function with sequential processing"""
    categories = [
        ("https://www.tesco.com/groceries/en-GB/shop/fresh-food/all", "fresh-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/bakery/all", "bakery"),
        ("https://www.tesco.com/groceries/en-GB/shop/frozen-food/all", "frozen-food"),
        ("https://www.tesco.com/groceries/en-GB/shop/treats-and-snacks/all", "treats-and-snacks"),
        ("https://www.tesco.com/groceries/en-GB/shop/food-cupboard/all", "food-cupboard"),
        ("https://www.tesco.com/groceries/en-GB/shop/drinks/all", "drinks"),
        ("https://www.tesco.com/groceries/en-GB/shop/baby-and-toddler/all", "baby-and-toddler")
    ]
    
    print("🛒 Starting optimized Tesco scraper...")
    print(f"📋 Categories to scrape: {len(categories)}")
    print(f"🔄 Processing: Sequential (1 worker)")
    print(f"🔧 ChromeDriver: Enhanced with version detection")
    print(f"🛡️ Anti-detection: UC Chrome with randomized delays")
    print(f"📄 Pagination: Full traversal with enhanced detection\n")
    
    start_time = time.time()
    
    # Process categories sequentially (not in parallel)
    for i, (url, name) in enumerate(categories, 1):
        print(f"\n{'='*60}")
        print(f"🏷️ Category {i}/{len(categories)}: {name}")
        print(f"{'='*60}")
        
        try:
            category_products = scrape_single_category(url, name)
            
            with products_lock:
                all_products.extend(category_products)
                
            print(f"📦 Total products so far: {len(all_products)}")
            
        except Exception as e:
            print(f"❌ Category {name} failed: {e}")
        
        # Brief pause between categories
        if i < len(categories):
            time.sleep(random.uniform(2, 5))
    
    # Save results
    if all_products:
        df = pd.DataFrame(all_products)
        
        # Clean data
        print(f"\n📊 Processing {len(df)} raw products...")
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
        print(f"🛒 SCRAPING COMPLETED!")
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
        print("❌ No products found - creating minimal CSV for testing")
        test_df = pd.DataFrame([{
            'Category': 'Test',
            'Name': 'Test Product - No Data Found',
            'Price': '£1.00'
        }])
        save_csv_to_both_locations(test_df, "tesco")
        print("✅ Minimal test CSV created")

if __name__ == "__main__":
    scrape_tesco_optimized()