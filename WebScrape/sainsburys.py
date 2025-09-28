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

# ========== ENHANCED SCRAPER CONFIG ==========
MAX_THREADS = 1  # Sequential for GitHub Actions stability
BASE_URL = "https://www.sainsburys.co.uk"

# Global driver management
WORKING_DRIVER_CONFIG = None

# Enhanced anti-detection configuration
RANDOM_DELAYS = {
    'page_load': (2.5, 5.0),      # Longer delays between pages
    'category_switch': (3.0, 7.0),  # Random delays between categories
    'scroll_wait': (1.5, 3.0),    # Random scroll delays
    'initial_load': (5.0, 10.0)   # Initial page load delay
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
]

def print_progress(message, flush=True):
    """Print with immediate flush for GitHub Actions visibility"""
    print(message)
    if flush:
        import sys
        sys.stdout.flush()

def detect_blocking_indicators(driver):
    """Enhanced detection for blocking, CAPTCHAs, or limited content"""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        page_source = driver.page_source.lower()
        current_url = driver.current_url.lower()
        
        # Enhanced blocking detection
        blocking_indicators = [
            "blocked", "captcha", "unusual traffic", "verify you are human",
            "security check", "access denied", "temporarily unavailable",
            "robot", "automated", "suspicious activity", "rate limit",
            "please wait", "checking your browser", "cloudflare"
        ]
        
        for indicator in blocking_indicators:
            if indicator in body_text or indicator in page_source:
                print_progress(f"   🚫 BLOCKING DETECTED: Found '{indicator}' in page content")
                return True
        
        # Check for redirect to blocking page
        if "blocked" in current_url or "captcha" in current_url:
            print_progress(f"   🚫 BLOCKING DETECTED: Redirected to blocking URL")
            return True
            
        # Check for minimal product count (strong indicator of soft blocking)
        try:
            product_elements = driver.find_elements(By.CSS_SELECTOR, ".pt__content")
            if len(product_elements) > 0 and len(product_elements) <= 24:  # Typically one page
                # Check if pagination is missing (another blocking indicator)
                pagination = driver.find_elements(By.CSS_SELECTOR, '[rel="next"]')
                if not pagination:
                    print_progress(f"   ⚠️ SOFT BLOCKING SUSPECTED: Only {len(product_elements)} products and no pagination")
                    return True
        except:
            pass
        
        return False
        
    except Exception as e:
        print_progress(f"   ⚠️ Error checking for blocking: {e}")
        return False

def random_delay(delay_type='page_load'):
    """Apply random delay based on type"""
    if delay_type in RANDOM_DELAYS:
        delay = random.uniform(*RANDOM_DELAYS[delay_type])
        time.sleep(delay)
    else:
        time.sleep(random.uniform(1.0, 3.0))

def debug_product_structure(product_elements, category_name):
    """Debug function to inspect product HTML structure"""
    if len(product_elements) > 0:
        try:
            first_product = product_elements[0]
            print_progress(f"   🔍 DEBUG for {category_name}:")
            print_progress(f"   🔍 Product HTML (first 300 chars): {first_product.get_attribute('outerHTML')[:300]}")
            
            # Try to find any links
            links = first_product.find_elements(By.TAG_NAME, "a")
            print_progress(f"   🔍 Found {len(links)} links in product")
            
            if links:
                first_link = links[0]
                print_progress(f"   🔍 First link text: '{first_link.text.strip()}'")
                print_progress(f"   🔍 First link href: '{first_link.get_attribute('href')}'")
            
            # Look for any price-like text
            all_text = first_product.text
            price_matches = re.findall(r'£[\d.,]+|\d+p', all_text)
            print_progress(f"   🔍 Price-like text found: {price_matches}")
            
        except Exception as e:
            print_progress(f"   🔍 DEBUG error: {e}")

def extract_parent_category_from_url(url):
    """Extract the parent category name from URL"""
    try:
        # URL format: .../groceries/PARENT/SUBCATEGORY/c:1019895
        parts = url.split('/')
        groceries_index = parts.index('groceries')
        
        if groceries_index + 1 < len(parts):
            parent_category = parts[groceries_index + 1]
            return parent_category.replace('-', ' ')
        
        return "unknown"
    except:
        return "unknown"

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

def detect_environment():
    """Detect if running in GitHub Actions or local environment"""
    return os.environ.get('GITHUB_ACTIONS') == 'true'

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
    except Exception:
        pass

def get_chrome_version():
    """Get Chrome version for both Windows and Linux"""
    try:
        is_github = detect_environment()
        
        if is_github:
            # Linux (GitHub Actions)
            try:
                result = subprocess.run(['google-chrome', '--version'], 
                                     capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    version_match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', result.stdout)
                    if version_match:
                        major_version = int(version_match.group(1))
                        return major_version
            except:
                pass
        else:
            # Windows (local)
            try:
                result = subprocess.run([
                    'reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    version_match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', result.stdout)
                    if version_match:
                        major_version = int(version_match.group(1))
                        return major_version
            except:
                pass
        
        return None
        
    except Exception:
        return None

def cleanup_chromedriver_files():
    """Cleanup ChromeDriver files for both environments"""
    try:
        kill_chrome_processes()
        
        is_github = detect_environment()
        
        if is_github:
            # Linux cleanup paths
            cleanup_paths = [
                "/tmp/chromedriver",
                "/usr/local/bin/chromedriver_backup",
                os.path.join(os.path.expanduser("~"), ".cache", "undetected_chromedriver"),
                os.path.join(os.path.expanduser("~"), ".local", "share", "undetected_chromedriver"),
            ]
        else:
            # Windows cleanup paths
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
                    else:
                        shutil.rmtree(path)
                except Exception:
                    pass
        
        time.sleep(1)
        
    except Exception:
        pass

def setup_optimized_driver():
    """Setup Chrome driver optimized for both local and GitHub Actions with enhanced anti-detection"""
    global WORKING_DRIVER_CONFIG
    
    # If we have a working config, use it directly
    if WORKING_DRIVER_CONFIG:
        try:
            options = create_fresh_options()
            if WORKING_DRIVER_CONFIG['type'] == 'explicit_path':
                driver = uc.Chrome(
                    driver_executable_path='/usr/local/bin/chromedriver',
                    options=options,
                    version_main=None
                )
            elif WORKING_DRIVER_CONFIG['type'] == 'auto_detect':
                driver = uc.Chrome(version_main=None, options=options)
            else:  # version_specific
                driver = uc.Chrome(version_main=WORKING_DRIVER_CONFIG['version'], options=options)
            
            driver.delete_all_cookies()
            return driver
        except Exception:
            # Reset if previously working config fails
            WORKING_DRIVER_CONFIG = None
    
    # Original driver setup logic if no working config
    cleanup_chromedriver_files()
    
    is_github = detect_environment()
    chrome_version = get_chrome_version()
    
    try:
        # Strategy 1: Try with explicit ChromeDriver path (GitHub Actions)
        if is_github:
            try:
                options = create_fresh_options()
                driver = uc.Chrome(
                    driver_executable_path='/usr/local/bin/chromedriver',
                    options=options,
                    version_main=None
                )
                driver.delete_all_cookies()
                WORKING_DRIVER_CONFIG = {'type': 'explicit_path'}
                return driver
            except Exception:
                pass
        
        # Strategy 2: Auto-detection with version_main=None
        try:
            options = create_fresh_options()
            driver = uc.Chrome(version_main=None, options=options)
            driver.delete_all_cookies()
            WORKING_DRIVER_CONFIG = {'type': 'auto_detect'}
            return driver
        except Exception:
            pass
        
        # Strategy 3: Try with compatible versions
        compatible_versions = [140, 139, 129, 130, 131]
        for version in compatible_versions:
            try:
                options = create_fresh_options()
                driver = uc.Chrome(version_main=version, options=options)
                driver.delete_all_cookies()
                WORKING_DRIVER_CONFIG = {'type': 'version_specific', 'version': version}
                return driver
            except Exception:
                continue
        
        return None
        
    except Exception:
        return None

def create_fresh_options():
    """Create fresh Chrome options with enhanced anti-detection"""
    is_github = detect_environment()
    options = uc.ChromeOptions()
    
    # Enhanced anti-detection options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-features=VizDisplayCompositor")
    
    # Additional stealth options
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--aggressive-cache-discard")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-prompt-on-repost")
    options.add_argument("--disable-component-extensions-with-background-pages")
    
    # Disable images and media for faster loading (but keep some for realism)
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.geolocation": 2,
        "profile.default_content_settings.popups": 0,
        # Don't completely disable images - makes us look more like a bot
        "profile.managed_default_content_settings.media_stream": 2,
    }
    options.add_experimental_option("prefs", prefs)
    
    if is_github:
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-software-rasterizer")
    else:
        options.add_argument("--start-maximized")
    
    # Rotate user agent
    user_agent = random.choice(USER_AGENTS)
    options.add_argument(f"--user-agent={user_agent}")
    
    return options

def handle_cookies_once(driver):
    """Handle cookies banner if present with more realistic behavior"""
    try:
        # Add slight delay before looking for cookie banner
        random_delay('scroll_wait')
        
        # Wait for and click cookie accept button
        cookie_selectors = [
            '//button[contains(text(), "Accept") and contains(text(), "Cookies")]',
            '//button[contains(text(), "Accept") and contains(text(), "cookies")]',
            '//button[contains(text(), "Accept All")]',
            '//button[@id="onetrust-accept-btn-handler"]',
            '//button[contains(@class, "cookie") and contains(text(), "Accept")]'
        ]
        
        for selector in cookie_selectors:
            try:
                cookie_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                # Add small delay before clicking
                time.sleep(random.uniform(0.5, 1.5))
                cookie_button.click()
                time.sleep(random.uniform(1.0, 2.0))
                return True
            except:
                continue
        
        return False
        
    except Exception:
        return False

def scroll_to_load_all_products(driver, max_scrolls=5):
    """Enhanced scroll with more human-like behavior and blocking detection"""
    try:
        # Check if driver is still responsive
        try:
            driver.current_url
        except Exception:
            return False
            
        # Get initial page height
        last_height = driver.execute_script("return document.body.scrollHeight")
        scrolls = 0
        
        while scrolls < max_scrolls:
            try:
                # More human-like scrolling pattern
                if scrolls == 0:
                    # First scroll - check top of page
                    driver.execute_script("window.scrollTo(0, 300);")
                    time.sleep(random.uniform(0.8, 1.5))
                
                # Scroll down incrementally
                current_position = driver.execute_script("return window.pageYOffset;")
                scroll_height = driver.execute_script("return document.body.scrollHeight")
                
                # Scroll to 3/4 of page first
                three_quarter = scroll_height * 0.75
                driver.execute_script(f"window.scrollTo(0, {three_quarter});")
                random_delay('scroll_wait')
                
                # Then scroll to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for new content to load
                random_delay('scroll_wait')
                
                # Check for blocking after scrolling
                if detect_blocking_indicators(driver):
                    print_progress(f"   🚫 Blocking detected during scroll - stopping")
                    return False
                
                # Calculate new scroll height and compare to last height
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                # If height hasn't changed, we've reached the end
                if new_height == last_height:
                    print_progress(f"   📜 No more content to load after {scrolls + 1} scrolls")
                    break
                    
                last_height = new_height
                scrolls += 1
                
                # Random scroll back up a bit (human behavior)
                if random.random() < 0.3:  # 30% chance
                    driver.execute_script("window.scrollTo(0, window.pageYOffset - 200);")
                    time.sleep(random.uniform(0.3, 0.8))
                
            except Exception as e:
                print_progress(f"   ⚠️ Error during scroll {scrolls}: {e}")
                break
        
        # Scroll back to top for consistent scraping start point
        try:
            driver.execute_script("window.scrollTo(0, 0);")
            random_delay('scroll_wait')
        except:
            pass
        
        return True
        
    except Exception:
        return False

def scrape_category(driver, url, category_index=0):
    """Scrape all pages from a category with enhanced anti-detection"""
    products = []
    page = 1
    max_pages = 50

    # Extract parent category name from URL
    category_name = extract_parent_category_from_url(url)
    print_progress(f"🛒 Starting category {category_index + 1}: {category_name}")
    
    # Add random delay before starting category (varies by category index)
    if category_index > 0:
        base_delay = random.uniform(3.0, 7.0)
        # Add more delay for later categories to avoid pattern detection
        extra_delay = (category_index // 10) * random.uniform(1.0, 3.0)
        time.sleep(base_delay + extra_delay)
        print_progress(f"   ⏱️ Applied {base_delay + extra_delay:.1f}s delay before category")

    while page <= max_pages:
        try:
            if page == 1:
                paged_url = url
            else:
                paged_url = f"{url}/opt/page:{page}"
            
            print_progress(f"   📄 Scraping page {page}...")
            
            # Add random delay before page load
            if page > 1:
                random_delay('page_load')
            
            driver.get(paged_url)
            print_progress(f"   🔍 Page title: {driver.title}")
            print_progress(f"   🔍 Current URL: {driver.current_url}")

            # Add realistic delay after page load
            initial_delay = random.uniform(*RANDOM_DELAYS['initial_load']) if page == 1 else random.uniform(2.0, 4.0)
            time.sleep(initial_delay)
            
            # Check for blocking immediately after page load
            if detect_blocking_indicators(driver):
                print_progress(f"   🚫 Blocking detected - stopping category scraping")
                break

            if page == 1:
                cookies_handled = handle_cookies_once(driver)
                if cookies_handled:
                    print_progress(f"   🍪 Accepted cookies")

            # Scroll to load all products before scraping
            scroll_success = scroll_to_load_all_products(driver)
            if not scroll_success:
                print_progress(f"   ⚠️ Scroll failed or blocking detected")
                break

            # Find product elements
            product_elements = []
            
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, ".pt__content")
                if elements:
                    product_elements = elements
                    print_progress(f"   ✅ Found {len(elements)} product elements using selector: .pt__content")
            except:
                pass
            
            # If main selector fails, try alternatives
            if not product_elements:
                alternative_selectors = [
                    ".pt-grid-item", 
                    "article.pt",
                    ".ln-c-card.pt",
                    "*[class*='pt__content']",
                    ".pt__content--with-header",
                    ".ln-o-grid__column .pt",
                    "[data-testid*='product']"
                ]
                
                for selector in alternative_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            product_elements = elements
                            print_progress(f"   ✅ Found {len(elements)} product elements using selector: {selector}")
                            break
                    except:
                        continue

            if not product_elements:
                print_progress(f"   ⚠️ No product elements found on page {page}")
                # Check if this might be due to blocking
                if detect_blocking_indicators(driver):
                    print_progress(f"   🚫 Confirmed blocking - stopping")
                break

            # Check for suspiciously low product count (blocking indicator)
            if len(product_elements) <= 24 and page == 1:  # First page should have more
                print_progress(f"   ⚠️ Suspiciously low product count: {len(product_elements)}")
                if detect_blocking_indicators(driver):
                    print_progress(f"   🚫 Blocking suspected due to low product count")
                    break

            # Extract products from this page
            page_products = []
            
            for i, product in enumerate(product_elements):
                try:
                    # Add tiny delay between products to look more human
                    if i > 0 and i % 10 == 0:
                        time.sleep(random.uniform(0.1, 0.3))
                    
                    # Extract product name using the exact selector from your HTML
                    name = ""
                    name_selectors = [
                        '.pt__info__description .pt__link',  # From your HTML structure
                        '.pt__link',
                        'a.pt__link', 
                        '.pt__info .pt__link',
                        '.pt__content .pt__link',
                        'h2.pt__info__description a',
                        'h2 a',
                        "a[href*='/gol-ui/product/']",
                        "a[title]"
                    ]
                    
                    for name_selector in name_selectors:
                        try:
                            name_elem = product.find_element(By.CSS_SELECTOR, name_selector)
                            name = name_elem.text.strip()
                            
                            # Handle truncated names with full title
                            if not name:
                                name = name_elem.get_attribute('title') or ""
                            elif name.endswith('...'):
                                full_title = name_elem.get_attribute('title') or ""
                                if len(full_title) > len(name):
                                    name = full_title
                            
                            if name and len(name) > 3:
                                break
                        except:
                            continue
                    
                    if not name:
                        continue
                    
                    # Extract ONLY retail price (ignore Nectar prices completely)
                    price = "N/A"
                    retail_price_selectors = [
                        '[data-testid="pt-retail-price"]',  # From your HTML - this is the £5.10
                        '.pt__cost__retail-price',
                        '.pt__cost__retail-price--with-nectar-not-associated',
                        '.pt__cost span[data-testid="pt-retail-price"]'
                    ]
                    
                    for price_selector in retail_price_selectors:
                        try:
                            price_elem = product.find_element(By.CSS_SELECTOR, price_selector)
                            price_text = price_elem.text.strip()
                            
                            # Extract price using regex
                            price_match = re.search(r'£[\d.,]+|\d+p', price_text)
                            if price_match:
                                price = price_match.group()
                                break
                        except:
                            continue
                    
                    # If no retail price found, try broader search but avoid contextual prices
                    if price == "N/A":
                        try:
                            # Look for any price that's NOT in contextual price containers
                            all_price_elements = product.find_elements(By.CSS_SELECTOR, '*[class*="price"]:not([data-testid="contextual-price-text"])')
                            for elem in all_price_elements:
                                price_text = elem.text.strip()
                                price_match = re.search(r'£[\d.,]+|\d+p', price_text)
                                if price_match:
                                    price = price_match.group()
                                    break
                        except:
                            pass

                    # Add product if we have both name and price
                    if name and price != "N/A":
                        product_data = {
                            "Category": category_name,
                            "Product Name": name,
                            "Price": price
                        }
                        page_products.append(product_data)
                        
                except Exception as e:
                    continue

            print_progress(f"   ✅ Extracted {len(page_products)} valid products from {len(product_elements)} elements")

            # Add ALL products from this page (no duplicate checking)
            products.extend(page_products)
            print_progress(f"   ➕ Added {len(page_products)} products to total")
            print_progress(f"   📊 Running total: {len(products)} products")

            # Debug for categories with 0 products when elements exist
            if len(page_products) == 0 and len(product_elements) > 0:
                print_progress(f"   🔍 DEBUG: Found {len(product_elements)} elements but 0 valid products")
                debug_product_structure(product_elements, category_name)

            # Check if next button is disabled (ONLY way to stop)
            next_button_disabled = True
            try:
                # Look for enabled next buttons
                enabled_next_selectors = [
                    'button[rel="next"]:not(.is-disabled):not([disabled]):not([aria-disabled="true"])',
                    '.ln-c-pagination__link[rel="next"]:not(.is-disabled):not([disabled]):not([aria-disabled="true"])',
                    'a[rel="next"]:not(.is-disabled)',
                    '.pagination-next:not(.disabled)'
                ]
                
                for selector in enabled_next_selectors:
                    try:
                        next_button = driver.find_element(By.CSS_SELECTOR, selector)
                        if next_button and next_button.is_enabled() and next_button.is_displayed():
                            next_button_disabled = False
                            print_progress(f"   ▶️ Next button found and enabled")
                            break
                    except:
                        continue
                
                if next_button_disabled:
                    print_progress(f"   🔚 Next button is disabled - reached end of category")
                    break
                        
            except Exception:
                print_progress(f"   ⚠️ Error checking pagination - assuming end reached")
                break

            page += 1

        except Exception as e:
            print_progress(f"   ❌ Error on page {page}: {e}")
            break

    print_progress(f"✅ Category {category_name} completed: {len(products)} total products")
    return products

def scrape_single_category(url, category_index=0):
    """Run one category scrape with driver reuse"""
    driver = setup_optimized_driver()
    if not driver:
        return []

    try:
        products = scrape_category(driver, url, category_index)
        return products
    finally:
        try:
            driver.quit()
        except:
            pass
        # Don't cleanup ChromeDriver files between categories if using working config
        if not WORKING_DRIVER_CONFIG:
            time.sleep(0.5)

def scrape_all_categories():
    """Scrape all categories sequentially with enhanced anti-detection"""
    all_products = []
    total_categories = len(CATEGORY_URLS)
    
    # Shuffle the category URLs to avoid predictable patterns
    shuffled_urls = CATEGORY_URLS.copy()
    random.shuffle(shuffled_urls)
    print_progress(f"📋 Randomized category order to avoid detection patterns")
    
    for i, url in enumerate(shuffled_urls, 1):
        try:
            print_progress(f"📊 Progress: Starting {i}/{total_categories} categories")
            products = scrape_single_category(url, i - 1)
            all_products.extend(products)
            print_progress(f"📊 Progress: {i}/{total_categories} categories completed")
            
            # Early termination if we detect we're being blocked consistently
            if i > 5 and len(all_products) < 50:  # After 5 categories, should have more than 50 products
                print_progress(f"⚠️ WARNING: Very low product count ({len(all_products)}) after {i} categories - possible blocking")
                print_progress(f"⚠️ Consider stopping and investigating")
            
        except Exception as e:
            print_progress(f"❌ Error scraping category {url}: {e}")
        
        # Variable delays between categories
        if i < len(shuffled_urls):
            category_delay = random.uniform(2.0, 6.0)
            # Add extra delay every 10 categories
            if i % 10 == 0:
                category_delay += random.uniform(10.0, 20.0)
                print_progress(f"   💤 Extended delay after {i} categories: {category_delay:.1f}s")
            time.sleep(category_delay)

    return all_products

def save_products(products):
    """Save scraped data to CSV files with enhanced logging"""
    if not products:
        print_progress("⚠️ No products to save!")
        return

    fieldnames = ["Category", "Product Name", "Price"]

    # Save locally
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products)
    
    print_progress(f"💾 Saved {len(products)} products to {OUTPUT_FILE}")

    # Save to app folder if possible
    try:
        os.makedirs(os.path.dirname(APP_OUTPUT_FILE), exist_ok=True)
        with open(APP_OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(products)
        print_progress(f"💾 Saved {len(products)} products to {APP_OUTPUT_FILE}")
    except Exception as e:
        print_progress(f"⚠️ Could not save to app folder: {e}")

def main():
    env = "GitHub Actions" if detect_environment() else "Local"
    print_progress(f"🛒 Starting ENHANCED Sainsbury's scraper ({env})")
    print_progress(f"📋 Categories: {len(CATEGORY_URLS)} | Processing: Sequential with anti-detection")
    print_progress(f"🔧 Anti-bot measures: Random delays, user-agent rotation, blocking detection")

    start_time = time.time()
    products = scrape_all_categories()
    elapsed = time.time() - start_time

    save_products(products)

    print_progress(f"\n🎉 COMPLETED!")
    print_progress(f"📊 Total products: {len(products)}")
    print_progress(f"⏱️ Time: {elapsed:.0f}s | Speed: {len(products)/elapsed:.1f} products/sec")
    
    # Analysis of results
    if len(products) < 1000:
        print_progress(f"⚠️ WARNING: Low product count ({len(products)}) - possible blocking detected")
    elif len(products) > 10000:
        print_progress(f"✅ SUCCESS: Good product count indicates successful scraping")
    
    # Category breakdown
    if products:
        categories = {}
        for product in products:
            cat = product.get('Category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print_progress(f"📊 Top 10 categories by product count:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
            print_progress(f"   - {cat}: {count} products")

if __name__ == "__main__":
    main()