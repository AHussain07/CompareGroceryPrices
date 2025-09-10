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
MAX_THREADS = 1  # Sequential for GitHub Actions stability
BASE_URL = "https://www.sainsburys.co.uk"

# Global driver management
WORKING_DRIVER_CONFIG = None

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
    """Setup Chrome driver optimized for both local and GitHub Actions"""
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
    
    def create_fresh_options():
        options = uc.ChromeOptions()
        
        # Common options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-features=VizDisplayCompositor")
        
        # Disable images and media for faster loading
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.media_stream": 2,
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.geolocation": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        # Additional performance options
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-translate")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--aggressive-cache-discard")
        options.add_argument("--disable-background-timer-throttling")
        
        if is_github:
            options.add_argument("--headless")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--window-size=1920,1080")
        else:
            options.add_argument("--start-maximized")
        
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
        return options

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
    """Create fresh Chrome options - standalone function for reuse"""
    is_github = detect_environment()
    options = uc.ChromeOptions()
    
    # Common options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-features=VizDisplayCompositor")
    
    # Disable images and media for faster loading
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.media_stream": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.geolocation": 2,
    }
    options.add_experimental_option("prefs", prefs)
    
    # Additional performance options
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--aggressive-cache-discard")
    options.add_argument("--disable-background-timer-throttling")
    
    if is_github:
        options.add_argument("--headless")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")
    
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    return options

def handle_cookies_once(driver):
    """Handle cookies banner if present"""
    try:
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
                cookie_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                cookie_button.click()
                time.sleep(1)
                return True
            except:
                continue
        
        return False
        
    except Exception:
        return False

def scroll_to_load_all_products(driver, max_scrolls=3):
    """Scroll down to load all products with lazy loading - safer version"""
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
                # Scroll down more gradually
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for new content to load
                time.sleep(2)
                
                # Calculate new scroll height and compare to last height
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                # If height hasn't changed, we've reached the end
                if new_height == last_height:
                    break
                    
                last_height = new_height
                scrolls += 1
                
            except Exception as e:
                break
        
        # Scroll back to top for consistent scraping start point
        try:
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
        except:
            pass
        
        return True
        
    except Exception:
        return False

def check_pagination_and_duplicates(driver, current_page_products, all_seen_products):
    """Check pagination status and detect duplicate content"""
    
    # Check for duplicate products
    current_product_names = {p["Product Name"] for p in current_page_products}
    overlap = current_product_names.intersection(all_seen_products)
    
    if len(overlap) > len(current_page_products) * 0.9:  # 90% overlap
        return True
    
    # Check pagination buttons
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
                    return True
            except:
                continue
        
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
            return True
    
    except Exception:
        return True
    
    return False

def scrape_category(driver, url):
    """Scrape all pages from a category"""
    products = []
    page = 1
    all_seen_product_names = set()
    consecutive_duplicate_pages = 0
    max_pages = 50

    # Extract category name
    url_parts = url.rstrip('/').split('/')
    for i, part in enumerate(url_parts):
        if part.startswith('c:'):
            if i > 0:
                category_name = url_parts[i-1]
                break
    else:
        try:
            category_name = url.split('/groceries/')[1].split('/')[0]
        except:
            category_name = "unknown"

    while page <= max_pages:
        try:
            if page == 1:
                paged_url = url
            else:
                paged_url = f"{url}/opt/page:{page}"
            
            driver.get(paged_url)

            if page == 1:
                handle_cookies_once(driver)

            time.sleep(random.uniform(0.5, 1.0))

            # Check for any content at all
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                if "blocked" in body_text.lower() or "captcha" in body_text.lower():
                    break
            except:
                pass

            # Scroll to load all products before scraping (with crash protection)
            scroll_success = scroll_to_load_all_products(driver)
            if not scroll_success:
                pass  # Continue without scroll

            # Enhanced product container detection with multiple attempts
            product_elements = []
            
            # Try multiple selector approaches
            selector_attempts = [
                ".pt__content",
                ".pt-grid-item", 
                "article.pt",
                ".ln-c-card.pt",
                "*[class*='pt__content']",
                ".pt__content--with-header"
            ]
            
            for selector in selector_attempts:
                try:
                    # Wait for elements to be present
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        product_elements = elements
                        break
                except Exception:
                    continue
            
            # If still no products, try without WebDriverWait
            if not product_elements:
                for selector in selector_attempts:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            product_elements = elements
                            break
                    except Exception:
                        continue

            if not product_elements:
                break

            # Initialize page_products list before extracting products
            page_products = []
            
            for product in product_elements:
                try:
                    # Enhanced product name - handle truncated names
                    try:
                        name_elem = product.find_element(By.CSS_SELECTOR, ".pt__link")
                        name = name_elem.text.strip()
                        
                        # Handle truncated names with full title
                        full_title = name_elem.get_attribute('title')
                        if name.endswith('...') and full_title and len(full_title) > len(name):
                            name = full_title.strip()
                        elif not name and full_title:
                            name = full_title.strip()
                    except:
                        continue
                    
                    if not name:
                        continue
                    
                    # Enhanced price extraction - include pence prices
                    try:
                        price_elem = product.find_element(By.CSS_SELECTOR, '[data-testid="pt-retail-price"]')
                        price_text = price_elem.text.strip()
                        # Enhanced regex to catch £X.XX, £X, and Xp formats
                        price_match = re.search(r'£[\d.,]+|\d+p', price_text)
                        price = price_match.group() if price_match else "N/A"
                    except:
                        price = "N/A"

                    # Nectar price - handle cases where it doesn't exist
                    nectar_price = "N/A"
                    try:
                        # Check if there's a contextual price wrapper first
                        contextual_wrapper = product.find_element(By.CSS_SELECTOR, '[data-testid="whole-contextual-price"]')
                        if contextual_wrapper:
                            try:
                                nectar_elem = product.find_element(By.CSS_SELECTOR, '[data-testid="contextual-price-text"]')
                                nectar_text = nectar_elem.text.strip()
                                nectar_match = re.search(r'£[\d.,]+|\d+p', nectar_text)
                                if nectar_match:
                                    nectar_price = nectar_match.group()
                            except:
                                pass
                    except:
                        # No contextual price wrapper means no Nectar price available
                        pass

                    if name and price != "N/A":
                        product_data = {
                            "Category": category_name,
                            "Product Name": name,
                            "Price": price,
                            "Price with Nectar": nectar_price
                        }
                        page_products.append(product_data)
                        
                except Exception:
                    continue

            # Check for end conditions
            if check_pagination_and_duplicates(driver, page_products, all_seen_product_names):
                break

            # Add new products only
            new_products = []
            for product in page_products:
                if product["Product Name"] not in all_seen_product_names:
                    new_products.append(product)
                    all_seen_product_names.add(product["Product Name"])

            products.extend(new_products)
            
            # Track consecutive pages with no new products
            if len(new_products) == 0:
                consecutive_duplicate_pages += 1
                if consecutive_duplicate_pages >= 3:  # Reduced from 5 to 3 for efficiency
                    break
            else:
                consecutive_duplicate_pages = 0

            page += 1
            # Shorter delays for GitHub Actions
            time.sleep(random.uniform(0.5, 1.0))

        except Exception:
            break

    print(f"✅ {category_name}: {len(products)} products")
    return products

def scrape_single_category(url):
    """Run one category scrape with driver reuse"""
    driver = setup_optimized_driver()
    if not driver:
        return []

    try:
        products = scrape_category(driver, url)
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
    """Scrape all categories sequentially"""
    all_products = []
    
    for i, url in enumerate(CATEGORY_URLS, 1):
        try:
            products = scrape_single_category(url)
            all_products.extend(products)
        except Exception:
            pass
        
        # Shorter delays for GitHub Actions
        if i < len(CATEGORY_URLS):
            time.sleep(0.5)

    return all_products

def save_products(products):
    """Save scraped data to CSV files"""
    if not products:
        return

    fieldnames = ["Category", "Product Name", "Price", "Price with Nectar"]

    # Save locally
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products)

    # Save to app folder if possible
    try:
        os.makedirs(os.path.dirname(APP_OUTPUT_FILE), exist_ok=True)
        with open(APP_OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(products)
    except:
        pass

def main():
    env = "GitHub Actions" if detect_environment() else "Local"
    print(f"🛒 Starting Sainsbury's scraper ({env})")
    print(f"📋 Categories: {len(CATEGORY_URLS)} | Processing: Sequential")

    start_time = time.time()
    products = scrape_all_categories()
    elapsed = time.time() - start_time

    save_products(products)

    print(f"\n🎉 COMPLETED!")
    print(f"📊 Total products: {len(products)}")
    print(f"⏱️ Time: {elapsed:.0f}s | Speed: {len(products)/elapsed:.1f} products/sec")

if __name__ == "__main__":
    main()