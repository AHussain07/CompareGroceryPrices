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

# Thread-safe list for collecting products
products_lock = threading.Lock()
all_products = []

def get_chrome_version():
    """Get installed Chrome version - adapted from sainsburys.py"""
    try:
        # Try registry method first (Windows)
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

def setup_optimized_driver():
    """Setup Chrome driver with performance optimizations and dynamic version detection"""
    # Get Chrome version
    chrome_version = get_chrome_version()
    
    options = uc.ChromeOptions()
    # Performance optimizations
    options.add_argument('--disable-images')  # Don't load images - major speed boost
    options.add_argument('--disable-javascript')  # Disable JS if not needed
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

    try:
        # Try with detected Chrome version first
        if chrome_version:
            print(f"Attempting to create driver with Chrome version {chrome_version}")
            try:
                driver = uc.Chrome(version_main=chrome_version, options=options)
                print("✅ Driver created successfully with detected version")
                return driver
            except Exception as e:
                print(f"Failed with detected version {chrome_version}: {e}")
        
        # Fallback: Let undetected-chromedriver auto-detect
        print("Attempting auto-detection fallback...")
        driver = uc.Chrome(version_main=None, options=options)
        print("✅ Driver created successfully with auto-detection")
        return driver
        
    except Exception as e:
        print(f"Failed to create driver: {e}")
        return None

def scrape_single_category(base_url, category_name):
    """Scrape a single category with optimizations"""
    driver = setup_optimized_driver()
    category_products = []
    
    try:
        # Extract simple category name from URL
        category = base_url.split('/shop/')[1].split('/')[0]
        print(f"Starting category: {category}")
        
        # Load first page to get pagination info
        url = f"{base_url}?page=1"
        driver.get(url)
        
        # Reduced wait time from 10 to 3 seconds
        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='verticalTile']:first-child"))
            )
        except Exception:
            print(f"No products found in {category}. Skipping.")
            return []
        
        # Get pagination info once
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
        
        # Scrape all pages
        for page in range(1, max_pages + 1):
            if page > 1:  # First page already loaded
                url = f"{base_url}?page={page}"
                driver.get(url)
                
                # Shorter wait for subsequent pages
                try:
                    WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='verticalTile']:first-child"))
                    )
                except Exception:
                    print(f"{category}: No products on page {page}")
                    break
            
            # Get all products at once instead of individual waits
            product_tiles = driver.find_elements(By.CSS_SELECTOR, "div[class*='verticalTile']")
            
            if not product_tiles:
                print(f"{category}: No products found on page {page}")
                break
            
            # Process products efficiently
            page_products = []
            for product in product_tiles:
                try:
                    name_elem = product.find_element(By.CSS_SELECTOR, "a[class*='titleLink']")
                    name = name_elem.text.strip() if name_elem else "N/A"
                    
                    price_elems = product.find_elements(By.CSS_SELECTOR, "p[class*='priceText']")
                    price = price_elems[0].text.strip() if price_elems else "N/A"
                    
                    page_products.append({
                        "Category": category,  # Using simplified category name
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
        driver.quit()

def save_csv_to_both_locations(df, filename):
    """Save CSV to both local directory and app/public folder"""
    # Save to local directory
    local_path = f"{filename}.csv"
    df.to_csv(local_path, index=False, encoding="utf-8")
    print(f"✅ Saved to local: {local_path}")
    
    # Save to app/public directory
    public_dir = "../app/public"
    if not os.path.exists(public_dir):
        os.makedirs(public_dir, exist_ok=True)
    
    public_path = os.path.join(public_dir, f"{filename}.csv")
    df.to_csv(public_path, index=False, encoding="utf-8")
    print(f"✅ Saved to public: {public_path}")

def scrape_tesco_optimized():
    """Main function with parallel processing"""
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
    
    # Use ThreadPoolExecutor for parallel processing
    # Limit to 3 concurrent threads to be respectful to the server
    with ThreadPoolExecutor(max_workers=3) as executor:
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