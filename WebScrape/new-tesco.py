import time
import random
import csv
import os
import re
import shutil
import subprocess
import psutil
from datetime import datetime
import pandas as pd
import uuid
import sys
import platform

def clean_price(price_text):
    """Extract numeric price from price text"""
    if not price_text:
        return None
    price_match = re.search(r'£(\d+\.?\d*)', price_text)
    return float(price_match.group(1)) if price_match else None

def get_chrome_version():
    """Get installed Chrome version (cross-platform)"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run([
                'reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                version_match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', result.stdout)
                if version_match:
                    major_version = int(version_match.group(1))
                    return major_version
        else:  # Linux/macOS
            result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version_match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', result.stdout)
                if version_match:
                    major_version = int(version_match.group(1))
                    return major_version
        return None
    except:
        return None

def setup_stealth_driver():
    """Setup stealth driver with fallback options"""
    driver = None
    
    # Try UC Chrome first
    try:
        import undetected_chromedriver as uc
        
        # Patch to prevent warnings
        uc.Chrome.__del__ = lambda self: None
        
        chrome_version = get_chrome_version()
        print(f"🔍 Detected Chrome version: {chrome_version}")
        
        options = uc.ChromeOptions()
        
        # Cross-platform options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        
        # Platform-specific options
        if platform.system() == "Linux":
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-first-run")
            options.add_argument("--disable-default-apps")
        else:
            options.add_argument("--start-maximized")
        
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Human-like prefs
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
        }
        options.add_experimental_option("prefs", prefs)
        
        # Try with detected version first
        if chrome_version:
            print(f"🚀 Trying UC Chrome with version {chrome_version}")
            try:
                driver = uc.Chrome(version_main=chrome_version, options=options)
            except Exception as e:
                print(f"⚠️ UC Chrome with version {chrome_version} failed: {e}")
                driver = None
        
        # Fallback to auto-detection
        if not driver:
            print("🚀 Trying UC Chrome with auto-detection")
            try:
                driver = uc.Chrome(options=options)
            except Exception as e:
                print(f"⚠️ UC Chrome auto-detection failed: {e}")
                driver = None
        
        if driver:
            print("✅ UC Chrome driver created successfully")
            # Human-like timeouts
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
            
            # Remove automation indicators
            try:
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except:
                pass
            
            return driver
            
    except ImportError:
        print("⚠️ undetected_chromedriver not available")
    except Exception as e:
        print(f"⚠️ UC Chrome setup failed: {e}")
    
    # Fallback to regular Selenium
    try:
        print("🔄 Falling back to regular Selenium WebDriver")
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        print("✅ Regular Selenium driver created successfully")
        return driver
        
    except Exception as e:
        print(f"❌ All driver creation methods failed: {e}")
        return None

def human_like_scrape(driver):
    """Human-like scraping with comprehensive selectors"""
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

def scrape_with_navigation(driver, base_url, category_name, max_pages):
    """Scrape using actual navigation like a human"""
    print(f"\n🤖 Starting human-like browsing for {category_name}")
    
    all_products = []
    seen_products = set()
    page = 1
    consecutive_blocks = 0
    consecutive_empty = 0
    
    # Start with the base URL
    try:
        driver.get(base_url)
        time.sleep(random.uniform(3, 5))  # Human-like initial wait
    except Exception as e:
        print(f"❌ Failed to load base URL: {e}")
        return all_products
    
    # Handle cookies once
    try:
        cookie_selectors = [
            "[id*='cookie'] button",
            "[class*='cookie'] button", 
            "#onetrust-accept-btn-handler",
            "button[class*='accept']",
            "[data-testid*='accept']",
            "[data-testid*='cookie']"
        ]
        
        for selector in cookie_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        print("🍪 Accepting cookies...")
                        driver.execute_script("arguments[0].scrollIntoView();", btn)
                        time.sleep(1)
                        btn.click()
                        time.sleep(2)
                        break
                if buttons:
                    break
            except:
                continue
    except Exception as e:
        print(f"⚠️ Cookie handling failed: {e}")
    
    while page <= max_pages and consecutive_blocks < 10 and consecutive_empty < 5:
        try:
            print(f"   🔄 {category_name}: Browsing page {page}")
            
            # Check for security block
            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                if any(phrase in page_text for phrase in ["not right", "security check", "unusual traffic", "robot"]):
                    print(f"   🚫 {category_name}: Security block detected on page {page}")
                    consecutive_blocks += 1
                    
                    if consecutive_blocks >= 3:
                        print(f"   ⚠️ {category_name}: Too many blocks, taking longer break...")
                        time.sleep(random.uniform(30, 60))  # Long break
                        consecutive_blocks = 0
                    else:
                        time.sleep(random.uniform(10, 20))  # Short break
                    
                    # Try to navigate to next page anyway
                    next_url = f"{base_url}?sortBy=relevance&page={page + 1}&count=24"
                    driver.get(next_url)
                    time.sleep(random.uniform(4, 7))
                    page += 1
                    continue
            except Exception as e:
                print(f"   ⚠️ Security check failed: {e}")
            
            # Reset block counter if we got through
            consecutive_blocks = 0
            
            # Wait for products to load
            try:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='verticalTile']"))
                )
                time.sleep(random.uniform(1, 2))
            except:
                print(f"   ⚪ {category_name}: No products found on page {page}")
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    print(f"   ⚠️ {category_name}: Too many empty pages, ending category")
                    break
                page += 1
                continue
            
            # Reset empty counter
            consecutive_empty = 0
            
            # Simulate human scrolling
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
                time.sleep(random.uniform(1, 2))
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(random.uniform(1, 2))
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(1, 2))
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            except:
                pass
            
            # Scrape products
            products_data = human_like_scrape(driver)
            
            if not products_data:
                print(f"   ⚪ {category_name}: No products extracted from page {page}")
                consecutive_empty += 1
                page += 1
                continue
            
            # Check for new products
            new_products = 0
            for product in products_data:
                product_id = f"{product['name']}_{product['price']}"
                if product_id not in seen_products:
                    seen_products.add(product_id)
                    all_products.append({
                        "Category": category_name,
                        "Name": product["name"],
                        "Price": product["price"]
                    })
                    new_products += 1
            
            print(f"   ✅ {category_name}: Page {page} - {new_products} new products (total: {len(all_products)})")
            
            # Human-like navigation to next page
            if page < max_pages:
                try:
                    # Try to find and click next button
                    next_selectors = [
                        "[data-testid='next']",
                        "[data-nextpreviousbtn='next']",
                        "a[aria-label*='Next']",
                        ".pagination-next",
                        "[class*='next']"
                    ]
                    
                    next_button = None
                    for selector in next_selectors:
                        try:
                            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                            for btn in buttons:
                                if btn.is_displayed() and btn.is_enabled():
                                    next_button = btn
                                    break
                            if next_button:
                                break
                        except:
                            continue
                    
                    if next_button:
                        # Human-like clicking
                        driver.execute_script("arguments[0].scrollIntoView();", next_button)
                        time.sleep(random.uniform(1, 2))
                        next_button.click()
                        time.sleep(random.uniform(3, 6))  # Wait for page load
                    else:
                        # Navigate directly
                        next_url = f"{base_url}?sortBy=relevance&page={page + 1}&count=24"
                        driver.get(next_url)
                        time.sleep(random.uniform(4, 7))
                except Exception as e:
                    # Navigate directly as fallback
                    next_url = f"{base_url}?sortBy=relevance&page={page + 1}&count=24"
                    driver.get(next_url)
                    time.sleep(random.uniform(4, 7))
            
            page += 1
            
            # Random longer breaks every 10 pages to seem more human
            if page % 10 == 0:
                print(f"   😴 {category_name}: Taking human-like break after page {page-1}")
                time.sleep(random.uniform(15, 30))
            
        except Exception as e:
            print(f"   ❌ {category_name}: Error on page {page}: {e}")
            time.sleep(random.uniform(5, 10))
            page += 1
            continue
    
    print(f"✅ {category_name}: Completed - {len(all_products)} products from {page-1} pages")
    return all_products

def save_csv_to_both_locations(df, filename):
    """Save CSV to both locations"""
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

def scrape_tesco_human_like():
    """Human-like sequential scraping to avoid detection"""
    print("🤖 Starting HUMAN-LIKE Tesco scraper...")
    print("👤 Mode: Sequential browsing with human behavior")
    print("⏱️ Strategy: Realistic delays and navigation")
    print("🔧 Driver: UC Chrome with Selenium fallback")
    print("🛡️ Anti-detection: Cookie handling, scrolling, breaks")
    print(f"🖥️ Platform: {platform.system()}")
    print()
    
    start_time = time.time()
    
    # Reduced page limits for testing
    categories = [
        ("Fresh Food", "https://www.tesco.com/groceries/en-GB/shop/fresh-food/all", 10),  # Test with 10 pages
        ("Bakery", "https://www.tesco.com/groceries/en-GB/shop/bakery/all", 5),
        ("Frozen Food", "https://www.tesco.com/groceries/en-GB/shop/frozen-food/all", 5),
    ]
    
    all_products = []
    
    # Use single driver for all categories (more human-like)
    driver = setup_stealth_driver()
    if not driver:
        print("❌ Failed to create driver")
        
        # Create minimal test CSV as fallback
        print("📄 Creating minimal test CSV...")
        test_df = pd.DataFrame([{
            'Category': 'Test',
            'Name': 'Test Product - Driver Failed',
            'Price': '£1.00'
        }])
        test_df.to_csv('tesco.csv', index=False)
        print("✅ Test CSV created")
        return
    
    try:
        for i, (cat_name, base_url, max_pages) in enumerate(categories):
            print(f"\n📊 Progress: Starting category {i+1}/{len(categories)}: {cat_name}")
            
            # Human-like break between categories
            if i > 0:
                break_time = random.uniform(10, 20)  # Shorter breaks for testing
                print(f"😴 Taking break between categories: {break_time:.1f} seconds")
                time.sleep(break_time)
            
            category_products = scrape_with_navigation(driver, base_url, cat_name, max_pages)
            all_products.extend(category_products)
            
            print(f"📊 Progress: Completed {i+1}/{len(categories)} categories - {len(category_products)} products")
        
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass
    
    # Process results
    if all_products:
        df = pd.DataFrame(all_products)
        df = df.dropna(subset=['Name', 'Price'])
        df = df[df['Name'].str.strip() != '']
        df = df[df['Price'].str.strip() != '']
        df = df.drop_duplicates(subset=['Name', 'Price'])
        df['Price_Numeric'] = df['Price'].apply(clean_price)
        df = df.sort_values(['Category', 'Name']).reset_index(drop=True)
        
        save_csv_to_both_locations(df, "tesco")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'='*60}")
        print(f"🤖 HUMAN-LIKE SCRAPING COMPLETED!")
        print(f"📦 Total unique products: {len(df)}")
        print(f"⏱️ Total time: {duration:.2f} seconds ({duration/60:.1f} minutes)")
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
        test_df.to_csv('tesco.csv', index=False)
        print("✅ Minimal test CSV created")

if __name__ == "__main__":
    # Import required modules
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        print("❌ Selenium not available")
        sys.exit(1)
    
    scrape_tesco_human_like()