import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import time
import threading

# Thread-safe storage
products_lock = threading.Lock()
all_products = []
cookies_handled = threading.Event()

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

def setup_optimized_driver():
    """Setup optimized Chrome driver"""
    options = uc.ChromeOptions()
    # Performance optimizations
    options.add_argument('--disable-images')
    options.add_argument('--disable-plugins')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    try:
        driver = uc.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"Failed to create driver: {e}")
        return None

def handle_cookies_once(driver):
    """Handle cookies only once globally"""
    if not cookies_handled.is_set():
        try:
            WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(.,"Accept All Cookies") or contains(.,"Accept all cookies")]'))
            ).click()
            print("✓ Cookies accepted")
            cookies_handled.set()
            time.sleep(0.5)  # Brief pause after cookie acceptance
        except Exception:
            cookies_handled.set()  # Set even if not found to avoid repeated attempts

def scrape_single_category(base_url):
    """Scrape a single category with optimizations and improved page handling"""
    driver = None
    try:
        driver = setup_optimized_driver()
        if not driver:
            return []
            
        category_products = []
        seen = set()
        seen_product_count = 0
        last_product_count = 0
        
        # Extract category name properly from URL - use the last meaningful part
        url_parts = base_url.split('/')
        # Get the part before the category ID (c:xxxxx)
        for i, part in enumerate(url_parts):
            if part.startswith('c:'):
                if i > 0:
                    category_name = url_parts[i-1]
                    break
        else:
            # Fallback to last part of path
            category_name = url_parts[-1] if url_parts[-1] else "unknown"
        
        print(f"Starting: {category_name}")
        
        page_num = 1
        max_duplicate_pages = 3  # Maximum pages with same product count
        duplicate_page_count = 0
        max_pages = 30  # Hard limit on maximum pages to prevent infinite loops
        
        while page_num <= max_pages and duplicate_page_count < max_duplicate_pages:
            # Build URL
            if page_num == 1:
                url = base_url
            else:
                url = f"{base_url}/opt/page:{page_num}"
            
            print(f"{category_name}: Trying page {page_num}")
            driver.get(url)
            
            # Handle cookies only once per session
            if page_num == 1:
                handle_cookies_once(driver)
            
            # Quick check for end conditions
            try:
                if "404" in driver.title.lower() or "error" in driver.title.lower():
                    print(f"{category_name}: Error page detected on page {page_num}")
                    break
            except Exception:
                pass

            # Wait for and get products
            try:
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".pt__content"))
                )
                products = driver.find_elements(By.CSS_SELECTOR, ".pt__content")
            except Exception:
                print(f"{category_name}: No products found on page {page_num}")
                break
            
            # Track product counts to detect duplicates
            last_product_count = seen_product_count
            new_products_count = 0
            
            # Process products
            for product in products:
                try:
                    name_elem = product.find_element(By.CSS_SELECTOR, '.pt__link')
                    name = name_elem.text.strip()
                    
                    if not name:
                        continue
                    
                    # Extract price - return to simple format like before
                    price_elem = product.find_element(By.CSS_SELECTOR, '.pt__cost__retail-price')
                    price = price_elem.text.strip()
                    
                    # Extract Nectar price - simple approach
                    try:
                        nectar_elem = product.find_element(By.CSS_SELECTOR, '.pt__cost--price')
                        nectar_price = nectar_elem.text.strip()
                    except Exception:
                        nectar_price = 'N/A'
                    
                    # Check for duplicates
                    key = (name, category_name)
                    if key not in seen:
                        category_products.append({
                            "Category": category_name,
                            "Product Name": name,
                            "Price": price,
                            "Price with Nectar": nectar_price
                        })
                        seen.add(key)
                        new_products_count += 1
                        
                except Exception:
                    continue
            
            seen_product_count = len(seen)
            print(f"{category_name}: Page {page_num} - {new_products_count} new products")
            
            # Check if we found any new products
            if seen_product_count == last_product_count:
                duplicate_page_count += 1
                print(f"{category_name}: No new products (duplicate page {duplicate_page_count}/{max_duplicate_pages})")
            else:
                duplicate_page_count = 0
            
            page_num += 1
            time.sleep(0.3)
        
        print(f"{category_name}: Completed - {len(category_products)} total unique products")
        return category_products
        
    except Exception as e:
        print(f"Error in {category_name}: {e}")
        return []
    finally:
        try:
            if driver:
                driver.close()  # Close the window first
                driver.quit()   # Then quit the driver
        except Exception:
            pass  # Suppress cleanup errors

def scrape_sainsburys_optimized():
    """Main function with parallel processing"""
    print("Starting optimized Sainsbury's scraper...")
    start_time = time.time()
    
    # Reduce max_workers to avoid too many browser instances
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit all category tasks
        future_to_url = {
            executor.submit(scrape_single_category, url): url 
            for url in CATEGORY_URLS
        }
        
        # Collect results
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                category_products = future.result()
                
                # Thread-safe addition
                with products_lock:
                    all_products.extend(category_products)
                    
            except Exception as e:
                print(f"Category failed {url}: {e}")
    
    # Save results
    if all_products:
        df = pd.DataFrame(all_products)
        df.to_csv("sainsburys.csv", index=False)
        
        # Also save to app folder if it exists
        try:
            df.to_csv("../app/public/sainsburys.csv", index=False)
        except Exception:
            pass
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'='*50}")
        print(f"SCRAPING COMPLETED!")
        print(f"Total products: {len(all_products)}")
        print(f"Total time: {duration:.2f} seconds")
        print(f"Products per second: {len(all_products)/duration:.2f}")
        print(f"File saved: sainsburys.csv")
        print(f"{'='*50}")
    else:
        print("No products found.")

if __name__ == "__main__":
    scrape_sainsburys_optimized()