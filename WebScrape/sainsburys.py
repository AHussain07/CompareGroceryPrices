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
from concurrent.futures import ThreadPoolExecutor, as_completed

# === Patch uc.Chrome destructor to prevent WinError 6 warnings ===
uc.Chrome.__del__ = lambda self: None


# ========== SCRAPER CONFIG ==========
MAX_THREADS = 1  # Reduced to 1 for better stability with ChromeDriver issues
BASE_URL = "https://www.sainsburys.co.uk"

CATEGORY_URLS = [
    "https://www.sainsburys.co.uk/gol-ui/groceries/frozen/chips-potatoes-and-rice/c:1019895",
    "https://www.sainsburys.co.uk/gol-ui/groceries/frozen/desserts-and-pastry/c:1019902",
    "https://www.sainsburys.co.uk/gol-ui/groceries/frozen/fish-and-seafood/c:1019924",
    "https://www.sainsburys.co.uk/gol-ui/groceries/frozen/freefrom/c:1019909",
    "https://www.sainsburys.co.uk/gol-ui/groceries/frozen/frozen-essentials/c:1019910",
    "https://www.sainsburys.co.uk/gol-ui/groceries/frozen/fruit-vegetables-and-herbs/c:1019934",
    "https://www.sainsburys.co.uk/gol-ui/groceries/frozen/ice-cream-and-ice/c:1019943",
    "https://www.sainsburys.co.uk/gol-ui/groceries/frozen/meat-and-poultry/c:1019966",
    "https://www.sainsburys.co.uk/gol-ui/groceries/frozen/pizza-and-garlic-bread/c:1019974",
    "https://www.sainsburys.co.uk/gol-ui/groceries/frozen/ready-meals-pies-and-party-food/c:1019986",
    "https://www.sainsburys.co.uk/gol-ui/groceries/frozen/vegan/c:1019988",
    "https://www.sainsburys.co.uk/gol-ui/groceries/frozen/vegetarian-and-meat-free/c:1019999",
    "https://www.sainsburys.co.uk/gol-ui/groceries/frozen/yorkshire-puddings-and-roast-accompaniments/c:1020000",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/tea-coffee-and-hot-drinks/c:1019428",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/squash-and-cordials/c:1019393",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/fizzy-drinks/c:1019310",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/water/c:1019437",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/juice-and-smoothies/c:1019333",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/juice-shots/c:1019334",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/kids-and-lunchbox/c:1019335",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/beer-and-cider/c:1019285",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/wine/c:1019462",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/champagne-and-sparkling-wine/c:1019292",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/spirits-and-liqueurs/c:1019377",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/low-and-no-alcohol/c:1019340",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/mixers-and-adult-soft-drinks/c:1019352",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/sports-energy-and-wellbeing/c:1019387",
    "https://www.sainsburys.co.uk/gol-ui/groceries/drinks/milk-and-milk-drinks/c:1019346",
    "https://www.sainsburys.co.uk/gol-ui/groceries/occasions-by-sainsburys/cakes/c:1046175",
    "https://www.sainsburys.co.uk/gol-ui/groceries/occasions-by-sainsburys/desserts/c:1046176",
    "https://www.sainsburys.co.uk/gol-ui/groceries/occasions-by-sainsburys/dining/c:1046179",
    "https://www.sainsburys.co.uk/gol-ui/groceries/occasions-by-sainsburys/gluten-free/c:1046184",
    "https://www.sainsburys.co.uk/gol-ui/groceries/occasions-by-sainsburys/party-food/c:1046177",
    "https://www.sainsburys.co.uk/gol-ui/groceries/occasions-by-sainsburys/salads-and-fruit/c:1046180",
    "https://www.sainsburys.co.uk/gol-ui/groceries/occasions-by-sainsburys/sandwiches-and-wraps/c:1046173",
    "https://www.sainsburys.co.uk/gol-ui/groceries/occasions-by-sainsburys/sushi/c:1046178",
    "https://www.sainsburys.co.uk/gol-ui/groceries/occasions-by-sainsburys/vegan/c:1046183",
    "https://www.sainsburys.co.uk/gol-ui/groceries/occasions-by-sainsburys/vegetarian/c:1046182",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/biscuits-and-crackers/c:1019495",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/canned-tinned-and-packaged-foods/c:1019540",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/cereals/c:1019573",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/confectionery/c:1019598",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/cooking-ingredients-and-oils/c:1019630",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/cooking-sauces-and-meal-kits/c:1019666",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/crisps-nuts-and-snacking-fruit/c:1019694",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/food-cupboard-essentials/c:1019697",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/freefrom/c:1019730",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/fruit-and-desserts/c:1019744",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/jams-honey-and-spreads/c:1019754",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/rice-pasta-and-noodles/c:1019794",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/stock-up-the-cupboards/c:1019798",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/sugar-and-home-baking/c:1019837",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/table-sauces-dressings-and-condiments/c:1019850",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/tea-coffee-and-hot-drinks/c:1019869",
    "https://www.sainsburys.co.uk/gol-ui/groceries/food-cupboard/world-foods/c:1019882",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dietary-and-world-foods/free-from/c:1019216",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dietary-and-world-foods/low-and-no-alcohol/c:1019223",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dietary-and-world-foods/organic/c:1019232",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dietary-and-world-foods/plant-based-drinks/c:1019233",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dietary-and-world-foods/sports-nutrition/c:1019241",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dietary-and-world-foods/sustainable-seafood/c:1019242",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dietary-and-world-foods/vegetarian-and-plant-based/c:1019250",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dietary-and-world-foods/vitamins-and-supplements/c:1019263",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dietary-and-world-foods/weight-management/c:1019264",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dietary-and-world-foods/world-foods/c:1034136",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dietary-and-world-foods/vegan/c:1019249",
    "https://www.sainsburys.co.uk/gol-ui/groceries/bakery/bread/c:1018785",
    "https://www.sainsburys.co.uk/gol-ui/groceries/bakery/bread-rolls-and-bagels/c:1018791",
    "https://www.sainsburys.co.uk/gol-ui/groceries/bakery/cakes-and-tarts/c:1018800",
    "https://www.sainsburys.co.uk/gol-ui/groceries/bakery/croissants-and-breakfast-bakery/c:1018812",
    "https://www.sainsburys.co.uk/gol-ui/groceries/bakery/doughnuts-cookies-and-muffins/c:1018820",
    "https://www.sainsburys.co.uk/gol-ui/groceries/bakery/freefrom-bread-and-cakes/c:1018825",
    "https://www.sainsburys.co.uk/gol-ui/groceries/bakery/from-our-in-store-bakery/c:1018834",
    "https://www.sainsburys.co.uk/gol-ui/groceries/bakery/naans-and-meal-sides/c:1018841",
    "https://www.sainsburys.co.uk/gol-ui/groceries/bakery/scones-fruited-and-buns/c:1018850",
    "https://www.sainsburys.co.uk/gol-ui/groceries/bakery/wraps-thins-and-pittas/c:1018858",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dairy-eggs-and-chilled/cooked-meats-olives-and-dips/c:1019021",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dairy-eggs-and-chilled/dairy-and-chilled-essentials/c:1019022",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dairy-eggs-and-chilled/meal-kits/c:1053925",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dairy-eggs-and-chilled/dairy-and-eggs/c:1019075",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dairy-eggs-and-chilled/desserts/c:1019084",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dairy-eggs-and-chilled/fresh-soup/c:1019093",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dairy-eggs-and-chilled/fruit-juice-and-drinks/c:1019106",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dairy-eggs-and-chilled/pies-pasties-and-quiche/c:1019116",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dairy-eggs-and-chilled/pizza-pasta-and-garlic-bread/c:1019123",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dairy-eggs-and-chilled/ready-meals/c:1019143",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dairy-eggs-and-chilled/sandwiches-and-food-to-go/c:1019152",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dairy-eggs-and-chilled/savoury-snacks/c:1019161",
    "https://www.sainsburys.co.uk/gol-ui/features/bbq-sides",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dairy-eggs-and-chilled/vegetarian-vegan-and-dairy-free/c:1019176",
    "https://www.sainsburys.co.uk/gol-ui/groceries/dairy-eggs-and-chilled/world-foods-kosher-and-halal/c:1019183",
    "https://www.sainsburys.co.uk/gol-ui/groceries/fruit-and-vegetables/fresh-fruit/c:1020020",
    "https://www.sainsburys.co.uk/gol-ui/groceries/fruit-and-vegetables/fresh-herbs-and-ingredients/c:1020027",
    "https://www.sainsburys.co.uk/gol-ui/groceries/fruit-and-vegetables/fresh-salad/c:1020040",
    "https://www.sainsburys.co.uk/gol-ui/groceries/fruit-and-vegetables/fresh-vegetables/c:1020057",
    "https://www.sainsburys.co.uk/gol-ui/groceries/fruit-and-vegetables/frozen-fruit-and-vegetables/c:1020067",
    "https://www.sainsburys.co.uk/gol-ui/features/thesaladhub",
    "https://www.sainsburys.co.uk/gol-ui/groceries/meat-and-fish/bacon-and-sausages/c:1020327",
    "https://www.sainsburys.co.uk/gol-ui/groceries/meat-and-fish/beef/c:1020335",
    "https://www.sainsburys.co.uk/gol-ui/groceries/meat-and-fish/chicken/c:1020345",
    "https://www.sainsburys.co.uk/gol-ui/groceries/meat-and-fish/cooked-meats-ham-and-pate/c:1020370",
    "https://www.sainsburys.co.uk/gol-ui/groceries/meat-and-fish/duck/c:1054762",
    "https://www.sainsburys.co.uk/gol-ui/groceries/meat-and-fish/fish-and-seafood/c:1020363",
    "https://www.sainsburys.co.uk/gol-ui/groceries/meat-and-fish/game-and-venison/c:1020352",
    "https://www.sainsburys.co.uk/gol-ui/groceries/meat-and-fish/gammon/c:1054771",
    "https://www.sainsburys.co.uk/gol-ui/groceries/meat-and-fish/just-cook-and-slow-cooked/c:1020371",
    "https://www.sainsburys.co.uk/gol-ui/groceries/meat-and-fish/lamb/c:1020376",
    "https://www.sainsburys.co.uk/gol-ui/groceries/meat-and-fish/meat-free/c:1020378",
    "https://www.sainsburys.co.uk/gol-ui/groceries/meat-and-fish/pork/c:1020384",
    "https://www.sainsburys.co.uk/gol-ui/groceries/meat-and-fish/turkey/c:1054773"
]



OUTPUT_FILE = "sainsburys.csv"
APP_OUTPUT_FILE = "../app/public/sainsburys.csv"

# ====================================


def kill_chrome_processes():
    """Kill all Chrome and ChromeDriver processes"""
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if any(name in proc.info['name'].lower() for name in ['chrome', 'chromedriver']):
                    proc.kill()
                    print(f"Killed process: {proc.info['name']} (PID: {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(1)  # Wait for processes to terminate
    except Exception as e:
        print(f"Error killing processes: {e}")


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
        
        print("Could not detect Chrome version - will use auto-detection")
        return None
        
    except Exception as e:
        print(f"Error detecting Chrome version: {e}")
        return None


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
        time.sleep(1)  # Wait for cleanup
        
    except Exception as e:
        print(f"Error during cleanup: {e}")


def setup_optimized_driver():
    """Setup optimized Chrome driver with proper version handling"""
    # Clean up any existing conflicting files first
    cleanup_chromedriver_files()
    
    # Get Chrome version
    chrome_version = get_chrome_version()
    
    options = uc.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}  # disable images
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
        driver = uc.Chrome(version_main=None, options=options)
        driver.delete_all_cookies()
        print("✅ Driver created successfully with auto-detection")
        return driver
        
    except Exception as e:
        print(f"Failed to create driver: {e}")
        return None


def check_pagination_and_duplicates(driver, current_page_products, all_seen_products):
    """Check pagination status and detect duplicate content"""
    
    # Check for duplicate products (indicates we've hit the end)
    current_product_names = {p["Product Name"] for p in current_page_products}
    overlap = current_product_names.intersection(all_seen_products)
    
    # Only stop if we have a very high overlap (90%+) indicating true duplicates
    if len(overlap) > len(current_product_names) * 0.9:  # More than 90% overlap
        print(f"   🔄 Detected {len(overlap)} duplicate products - likely reached end")
        return True
    
    # Check URL for actual page number
    try:
        current_url = driver.current_url
        if "page=" in current_url:
            page_match = re.search(r'page=(\d+)', current_url)
            if page_match:
                current_page_num = int(page_match.group(1))
                print(f"   📍 Current URL page: {current_page_num}")
    except:
        pass
    
    # Check for disabled next button
    try:
        disabled_selectors = [
            'button[rel="next"].ln-c-pagination__link.is-disabled',
            'button[rel="next"][disabled]',
            'button[rel="next"][aria-disabled="true"]',
            '.ln-c-pagination__link[rel="next"].is-disabled',
            '.ln-c-pagination__link[rel="next"][aria-disabled="true"]'
        ]
        
        for selector in disabled_selectors:
            try:
                disabled_button = driver.find_element(By.CSS_SELECTOR, selector)
                if disabled_button:
                    print("   ✅ Next button is disabled - reached last page")
                    return True
            except:
                continue
        
        # Check for enabled next button
        enabled_selectors = [
            'button[rel="next"]:not(.is-disabled):not([disabled]):not([aria-disabled="true"])',
            '.ln-c-pagination__link[rel="next"]:not(.is-disabled):not([disabled]):not([aria-disabled="true"])'
        ]
        
        has_enabled_next = False
        for selector in enabled_selectors:
            try:
                enabled_button = driver.find_element(By.CSS_SELECTOR, selector)
                if enabled_button and enabled_button.is_enabled():
                    has_enabled_next = True
                    break
            except:
                continue
        
        if not has_enabled_next:
            print("   ✅ No enabled next button found - reached last page")
            return True
        else:
            print("   ➡️ Next button is enabled - checking for actual new content")
    
    except Exception as e:
        print(f"   ⚠️ Error checking pagination: {e}")
        return True  # Assume last page on error
    
    return False


def scrape_category(driver, url):
    """Scrape all pages from a category with improved pagination and duplicate detection"""
    products = []
    page = 1
    all_seen_product_names = set()
    consecutive_duplicate_pages = 0
    max_pages = 50  # Increased safety limit for larger categories

    # Extract category name from URL
    # Extract category name - get the last meaningful part before the ID
    url_parts = url.rstrip('/').split('/')
    # Find the part just before the category ID (c:xxxxx)
    for i, part in enumerate(url_parts):
        if part.startswith('c:'):
            if i > 0:
                category_name = url_parts[i-1]
                break
    else:
        # Fallback to groceries section
        try:
            category_name = url.split('/groceries/')[1].split('/')[0]
        except:
            category_name = "unknown"

    print(f"🛒 Starting category: {category_name}")

    while page <= max_pages:
        try:
            if page == 1:
                paged_url = url
            else:
                paged_url = f"{url}/opt/page:{page}"
            print(f"   📄 Scraping page {page}...")
            
            driver.get(paged_url)
            time.sleep(random.uniform(1.0, 2.0))

            # Wait for products to load
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".pt__content"))
                )
            except:
                print(f"   ⚠️ No products found on page {page}")
                break

            product_elements = driver.find_elements(By.CSS_SELECTOR, ".pt__content")
            if not product_elements:
                print(f"   ⚠️ No product elements found on page {page}")
                break

            page_products = []
            page_products_count = 0
            
            for product in product_elements:
                try:
                    name = product.find_element(By.CSS_SELECTOR, ".pt__info a").text.strip()
                    
                    # Extract regular price and nectar price separately
                    try:
                        # Try to get regular price first
                        regular_price_elem = product.find_element(By.CSS_SELECTOR, '.pt__cost__retail-price')
                        price = regular_price_elem.text.strip()
                        # Clean the price - extract just the £X.XX part
                        price_match = re.search(r'£[\d.]+', price)
                        price = price_match.group() if price_match else price.split()[0] if price else "N/A"
                    except:
                        price = "N/A"

                    try:
                        # Try to get nectar price
                        nectar_elem = product.find_element(By.CSS_SELECTOR, '.pt__cost--price')
                        nectar_text = nectar_elem.text.strip()
                        # Extract the nectar price (usually the first £X.XX in the nectar element)
                        nectar_match = re.search(r'£[\d.]+', nectar_text)
                        nectar_price = nectar_match.group() if nectar_match else "N/A"
                    except:
                        nectar_price = "N/A"

                    if name and price:
                        product_data = {
                            "Category": category_name,
                            "Product Name": name,
                            "Price": price,
                            "Price with Nectar": nectar_price
                        }
                        page_products.append(product_data)
                        page_products_count += 1
                except Exception:
                    continue

            print(f"   ✅ Found {page_products_count} products on page {page}")

            # Check for duplicates and pagination
            if check_pagination_and_duplicates(driver, page_products, all_seen_product_names):
                print(f"   🏁 Reached last page for {category_name}")
                break

            # Add new products only (no duplicates)
            new_products = []
            for product in page_products:
                if product["Product Name"] not in all_seen_product_names:
                    new_products.append(product)
                    all_seen_product_names.add(product["Product Name"])

            products.extend(new_products)
            
            # Check if we found any new products
            new_products_this_page = len(new_products)
            if new_products_this_page == 0:
                consecutive_duplicate_pages += 1
                print(f"   ⚠️ No new products on page {page} (consecutive: {consecutive_duplicate_pages})")
                if consecutive_duplicate_pages >= 5:  # Increased tolerance to 5 pages
                    print(f"   🛑 Stopping due to {consecutive_duplicate_pages} consecutive pages with no new products")
                    break
            else:
                consecutive_duplicate_pages = 0
                print(f"   ➕ Added {new_products_this_page} new products")

            page += 1
            time.sleep(random.uniform(1.0, 2.0))

        except Exception as e:
            print(f"   ❌ Error on page {page}: {e}")
            break

    print(f"✅ Category {category_name} completed: {len(products)} total unique products\n")
    return products


def scrape_single_category(url):
    """Run one thread for a category"""
    driver = setup_optimized_driver()
    if not driver:
        print(f"❌ Failed to create driver for {url}")
        return []

    try:
        products = scrape_category(driver, url)
        return products
    finally:
        try:
            driver.quit()
        except:
            pass
        # Clean up after each category
        time.sleep(1)


def scrape_all_categories():
    """Scrape all categories sequentially for better stability"""
    all_products = []
    
    # Use sequential processing instead of threading for better stability
    for i, url in enumerate(CATEGORY_URLS, 1):
        print(f"\n📊 Progress: Starting {i}/{len(CATEGORY_URLS)} categories")
        try:
            products = scrape_single_category(url)
            all_products.extend(products)
            print(f"📊 Progress: {i}/{len(CATEGORY_URLS)} categories completed")
        except Exception as e:
            print(f"❌ Error scraping category {url}: {e}")
        
        # Wait between categories to avoid issues
        if i < len(CATEGORY_URLS):
            time.sleep(1)

    return all_products


def save_products(products):
    """Save scraped data to CSV files"""
    if not products:
        print("❌ No products found.")
        return

    fieldnames = ["Category", "Product Name", "Price", "Price with Nectar"]

    # Save locally
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products)

    # Save to app/public folder
    os.makedirs(os.path.dirname(APP_OUTPUT_FILE), exist_ok=True)
    with open(APP_OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products)

    print(f"✅ Files saved: {OUTPUT_FILE} (local) and {APP_OUTPUT_FILE}")


def main():
    print("🛒 Starting optimized Sainsbury's scraper...")
    print(f"📋 Categories to scrape: {len(CATEGORY_URLS)}")
    print(f"🧵 Processing: Sequential (no threading)")
    print(f"🔧 ChromeDriver: Enhanced cleanup and version detection")
    print(f"📄 Pagination: Duplicate detection + disabled Next button")
    print(f"🛑 Safety: Max 50 pages per category\n")  # ✅ Match the actual max_pages value

    start_time = time.time()
    products = scrape_all_categories()
    elapsed = time.time() - start_time

    save_products(products)

    print("\n" + "="*60)
    print("🎉 SCRAPING COMPLETED!")
    print(f"📊 Total products: {len(products)}")
    print(f"⏱️ Total time: {elapsed:.2f} seconds")
    if products:
        print(f"🚀 Products per second: {len(products)/elapsed:.2f}")
    print("="*60)


if __name__ == "__main__":
    main()