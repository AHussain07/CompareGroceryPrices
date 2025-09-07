import time
import random
import csv
import os
import re
import shutil
import subprocess
import psutil
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import uuid

# === Patch uc.Chrome destructor to prevent WinError 6 warnings ===
uc.Chrome.__del__ = lambda self: None

def clean_price(price_text):
    """Extract numeric price from price text"""
    if not price_text:
        return None
    price_match = re.search(r'£(\d+\.?\d*)', price_text)
    return float(price_match.group(1)) if price_match else None

def get_chrome_version():
    """Get installed Chrome version on Windows"""
    try:
        result = subprocess.run([
            'reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            version_match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', result.stdout)
            if version_match:
                major_version = int(version_match.group(1))
                return major_version
        return None
    except:
        return None

def setup_stealth_driver():
    """Setup ultra-stealth UC Chrome driver to avoid detection"""
    try:
        chrome_version = get_chrome_version()
        
        options = uc.ChromeOptions()
        
        # Minimal stealth options - look as human as possible
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")  # Human-like
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Keep some features enabled to look more human
        # Don't disable images, CSS, JavaScript - too suspicious
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Human-like prefs
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
        }
        options.add_experimental_option("prefs", prefs)
        
        if chrome_version:
            driver = uc.Chrome(version_main=chrome_version, options=options)
        else:
            driver = uc.Chrome(options=options)
        
        # Human-like timeouts
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        # Remove automation indicators
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
        
    except Exception as e:
        print(f"❌ Driver creation failed: {e}")
        return None

def human_like_scrape(driver):
    """Human-like scraping with realistic behavior"""
    js_script = """
    var products = [];
    var tiles = document.querySelectorAll('div[class*="verticalTile"]');
    
    for(var i = 0; i < tiles.length; i++) {
        var tile = tiles[i];
        var name = null, price = null;
        
        // Try name selectors
        var nameEl = tile.querySelector("a[class*='titleLink']") || tile.querySelector("h3 a");
        if(nameEl && nameEl.textContent.trim()) {
            name = nameEl.textContent.trim();
        }
        
        // Try price selectors
        var priceEl = tile.querySelector("p[class*='priceText']") || tile.querySelector("[class*='price']");
        if(priceEl && priceEl.textContent.trim()) {
            var priceText = priceEl.textContent.trim();
            if(priceText.includes('£')) {
                price = priceText;
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
        return products
    except:
        return []

def scrape_with_navigation(driver, base_url, category_name, max_pages):
    """Scrape using actual navigation like a human"""
    print(f"\n🤖 Starting human-like browsing for {category_name}")
    
    all_products = []
    seen_products = set()
    page = 1
    consecutive_blocks = 0
    
    # Start with the base URL
    driver.get(base_url)
    time.sleep(random.uniform(3, 5))  # Human-like initial wait
    
    # Handle cookies once
    try:
        cookie_buttons = driver.find_elements(By.CSS_SELECTOR, 
            "[id*='cookie'], [class*='cookie'] button, #onetrust-accept-btn-handler, button[class*='accept']")
        for btn in cookie_buttons:
            if btn.is_displayed():
                # Human-like clicking
                driver.execute_script("arguments[0].scrollIntoView();", btn)
                time.sleep(1)
                btn.click()
                time.sleep(2)
                break
    except:
        pass
    
    while page <= max_pages and consecutive_blocks < 10:
        try:
            print(f"   🔄 {category_name}: Browsing page {page}")
            
            # Check for security block
            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                if "not right" in page_text or "security check" in page_text:
                    print(f"   🚫 {category_name}: Security block on page {page}")
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
            except:
                pass
            
            # Reset block counter if we got through
            consecutive_blocks = 0
            
            # Wait for products to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='verticalTile']"))
                )
                time.sleep(random.uniform(1, 2))
            except:
                print(f"   ⚪ {category_name}: No products on page {page}")
                break
            
            # Simulate human scrolling
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
            time.sleep(random.uniform(1, 2))
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(random.uniform(1, 2))
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1, 2))
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Scrape products
            products_data = human_like_scrape(driver)
            
            if not products_data:
                print(f"   ⚪ {category_name}: No products extracted from page {page}")
                break
            
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
                    next_button = driver.find_element(By.CSS_SELECTOR, "[data-testid='next'], [data-nextpreviousbtn='next']")
                    if next_button and next_button.is_enabled():
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
                except:
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
        os.makedirs(public_dir, exist_ok=True)
    
    public_path = os.path.join(public_dir, f"{filename}.csv")
    df.to_csv(public_path, index=False, encoding="utf-8")
    print(f"✅ Saved to public: {public_path}")

def scrape_tesco_human_like():
    """Human-like sequential scraping to avoid detection"""
    print("🤖 Starting HUMAN-LIKE Tesco scraper...")
    print("👤 Mode: Sequential browsing with human behavior")
    print("⏱️ Strategy: Realistic delays and navigation")
    print("🔧 Driver: UC Chrome with minimal stealth")
    print("🛡️ Anti-detection: Cookie handling, scrolling, breaks")
    print()
    
    start_time = time.time()
    
    categories = [
        ("Fresh Food", "https://www.tesco.com/groceries/en-GB/shop/fresh-food/all", 184),
        ("Food Cupboard", "https://www.tesco.com/groceries/en-GB/shop/food-cupboard/all", 286),
        ("Drinks", "https://www.tesco.com/groceries/en-GB/shop/drinks/all", 267),
        ("Baby & Toddler", "https://www.tesco.com/groceries/en-GB/shop/baby-and-toddler/all", 152),
        ("Treats & Snacks", "https://www.tesco.com/groceries/en-GB/shop/treats-and-snacks/all", 89),
        ("Frozen Food", "https://www.tesco.com/groceries/en-GB/shop/frozen-food/all", 45),
        ("Bakery", "https://www.tesco.com/groceries/en-GB/shop/bakery/all", 32)
    ]
    
    all_products = []
    
    # Use single driver for all categories (more human-like)
    driver = setup_stealth_driver()
    if not driver:
        print("❌ Failed to create driver")
        return
    
    try:
        for i, (cat_name, base_url, max_pages) in enumerate(categories):
            print(f"\n📊 Progress: Starting category {i+1}/{len(categories)}: {cat_name}")
            
            # Human-like break between categories
            if i > 0:
                break_time = random.uniform(20, 40)
                print(f"😴 Taking break between categories: {break_time:.1f} seconds")
                time.sleep(break_time)
            
            category_products = scrape_with_navigation(driver, base_url, cat_name, max_pages)
            all_products.extend(category_products)
            
            print(f"📊 Progress: Completed {i+1}/{len(categories)} categories")
        
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
        print("❌ No products found.")

if __name__ == "__main__":
    scrape_tesco_human_like()