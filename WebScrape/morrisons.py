import pandas as pd
import time
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import threading
import os

# Set up minimal logging
logging.basicConfig(level=logging.WARNING)  # Reduced logging level
logger = logging.getLogger(__name__)

# Thread-safe storage
products_lock = threading.Lock()
all_products = []

class OptimizedMorrisonsProductScraper:
    def __init__(self, max_scrolls=None):
        self.max_scrolls = max_scrolls
        self.driver = None
        self.products = []

    def setup_driver(self):
        """Setup optimized Chrome driver"""
        chrome_options = Options()
        # Performance optimizations
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-images")  # Major speed boost
        chrome_options.add_argument("--disable-javascript")  # If not needed
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise

    def scroll_and_load_products(self, url, category_name):
        """Optimized scrolling and product loading"""
        print(f"Starting: {category_name}")
        self.driver.get(url)

        # Handle cookies with reduced timeout
        try:
            WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            ).click()
            time.sleep(1)  # Reduced from 2 seconds
        except TimeoutException:
            pass  # Continue if no cookie banner

        # Wait for initial products with reduced timeout
        try:
            WebDriverWait(self.driver, 5).until(  # Reduced from 15 seconds
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-test^='fop-wrapper']"))
            )
        except TimeoutException:
            print(f"{category_name}: No products loaded")
            return

        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        processed_ids = set()
        no_new_products_count = 0

        while True:
            # Get products on current view
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[data-test^='fop-wrapper']")
            
            new_products_found = 0
            for element in product_elements:
                try:
                    product_id = element.get_attribute('data-test')
                    if not product_id or product_id in processed_ids:
                        continue

                    # Extract product data efficiently
                    try:
                        name = element.find_element(By.CSS_SELECTOR, "h3[data-test='fop-title']").text
                        price_text = element.find_element(By.CSS_SELECTOR, "span[data-test='fop-price']").text
                        price = re.sub(r'[^\d.,]', '', price_text) or "N/A"

                        if name and name != "N/A":
                            self.products.append({
                                'name': name,
                                'price': price,
                                'category': category_name
                            })
                            processed_ids.add(product_id)
                            new_products_found += 1

                    except (NoSuchElementException, StaleElementReferenceException):
                        continue

                except Exception:
                    continue
            
            if new_products_found == 0:
                no_new_products_count += 1
                if no_new_products_count >= 3:  # Stop after 3 scrolls with no new products
                    break
            else:
                no_new_products_count = 0
                print(f"{category_name}: Scroll {scroll_count + 1} - {new_products_found} new products (Total: {len(self.products)})")
            
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.0)  # Reduced from 3-4 seconds
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count += 1
            
            # Stop conditions
            if (new_height == last_height or 
                (self.max_scrolls and scroll_count >= self.max_scrolls) or
                scroll_count >= 50):  # Add maximum scroll limit
                break
            
            last_height = new_height

        print(f"{category_name}: Completed - {len(self.products)} products")

    def scrape_url(self, url, category_name):
        """Main scraping method for a single category"""
        try:
            self.setup_driver()
            self.scroll_and_load_products(url, category_name)
            return self.products
        except Exception as e:
            print(f"Error in {category_name}: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()

def scrape_single_category(url):
    """Wrapper function for single category scraping"""
    try:
        category_name = re.search(r'/categories/([^/]+)/', url).group(1).replace('-', ' ').title()
    except AttributeError:
        category_name = "Unknown Category"
    
    scraper = OptimizedMorrisonsProductScraper(max_scrolls=40)  # Limit scrolls per category
    return scraper.scrape_url(url, category_name)

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

def main():
    """Optimized main function with parallel processing"""
    
    # Reduced category list for faster execution - add more as needed
    category_urls = [
        "https://groceries.morrisons.com/categories/fruit-veg-flowers/094cee3b-0f6c-40f1-b5ab-08026d73b02c?source=navigation",
        "https://groceries.morrisons.com/categories/meat-poultry/7fd143ec-3236-4177-94d1-aff4913c9a2e?source=navigation",
        "https://groceries.morrisons.com/categories/fish-seafood/36283c1e-0a1b-4f99-8db2-fb313165f41d?source=navigation",
        "https://groceries.morrisons.com/categories/fresh-chilled-foods/d681723f-f927-455b-ae83-cd2b8b253840?source=navigation",
        "https://groceries.morrisons.com/categories/bakery-cakes/5998e059-ce69-48d4-b0db-2f773459dcdf?source=navigation",
        "https://groceries.morrisons.com/categories/frozen-food/21f2fb19-934f-42f0-a2a0-a87853f8d16c?source=navigation",
        "https://groceries.morrisons.com/categories/food-cupboard/c2fe6663-6cbf-4ed5-86f1-c306d0360dfb?source=navigation",
        "https://groceries.morrisons.com/categories/dietary-lifestyle-foods/4850370a-3a5e-4956-ade7-00d0bf47783d?source=navigation",
        "https://groceries.morrisons.com/categories/world-foods/f4d47513-e02c-41a2-99bc-cc01763c3467?source=navigation",
        "https://groceries.morrisons.com/categories/drinks/d36e4c96-e988-4e43-84e3-f1fd513f4778?source=navigation",
        "https://groceries.morrisons.com/categories/beer-wines-spirits/b182dd9d-bdfe-487e-b583-74007e5b1e69?source=navigation"
    ]
    
    print("Starting optimized Morrisons scraper with parallel processing...")
    start_time = time.time()

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all category tasks
        future_to_url = {
            executor.submit(scrape_single_category, url): url 
            for url in category_urls
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                category_products = future.result()
                
                # Thread-safe addition to global products list
                with products_lock:
                    all_products.extend(category_products)
                    
            except Exception as e:
                print(f"Category failed {url}: {e}")

    # Save results
    if all_products:
        df = pd.DataFrame(all_products)
        # Clean up column names
        cols = ['name', 'price', 'category']
        df = df[[col for col in cols if col in df.columns]]
        
        # Clean data
        df = df.dropna(subset=['name', 'price'])
        df = df[df['name'].str.strip() != '']
        df = df[df['price'].str.strip() != '']
        df = df.drop_duplicates(subset=['name', 'price'])
        
        # Save to both locations
        save_csv_to_both_locations(df, "morrisons")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'='*50}")
        print(f"SCRAPING COMPLETED!")
        print(f"Total products: {len(all_products)}")
        print(f"Total time: {duration:.2f} seconds")
        print(f"Products per second: {len(all_products)/duration:.2f}")
        print(f"Files saved: morrisons.csv (local) and ../app/public/morrisons.csv")
        print(f"{'='*50}")
    else:
        print("No products were scraped. CSV files not generated.")

if __name__ == "__main__":
    main()