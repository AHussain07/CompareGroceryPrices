from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import pandas as pd
import re

# Thread-safe list for collecting products
products_lock = threading.Lock()
all_products = []

def clean_price(price_text):
    """Extract numeric price from price text"""
    if not price_text:
        return None
    # Remove "actual price" prefix and extract price
    cleaned = re.sub(r'actual price\s*', '', price_text, flags=re.IGNORECASE)
    price_match = re.search(r'£(\d+\.?\d*)', cleaned)
    return float(price_match.group(1)) if price_match else None

def setup_optimized_driver():
    """Setup Chrome driver optimized for speed and parallel processing"""
    service = Service()
    options = webdriver.ChromeOptions()
    
    # Performance optimizations
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")  # Major speed boost
    options.add_argument("--disable-css")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    
    # Anti-detection (minimal for speed)
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Network optimizations
    prefs = {
        "profile.managed_default_content_settings.images": 2,  # Block images
        "profile.default_content_setting_values.notifications": 2,  # Block notifications
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def get_all_categories():
    """Get all available categories from ASDA website"""
    driver = setup_optimized_driver()
    wait = WebDriverWait(driver, 10)
    
    try:
        print("📂 Getting all categories...")
        
        # Navigate to ASDA groceries
        driver.get("https://www.asda.com/groceries/search/*")
        time.sleep(1.5)
        
        # Handle cookies
        try:
            accept_cookies = wait.until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            accept_cookies.click()
            time.sleep(1)
        except TimeoutException:
            pass
        
        # Open category dropdown
        category_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='div-category-dropdown']"))
        )
        driver.execute_script("arguments[0].click();", category_btn)
        time.sleep(1)
        
        # Get all category elements
        category_elements = driver.find_elements(By.CSS_SELECTOR, "button[data-testid='btn-category-options']")
        categories = []
        
        # Skip categories from asda.py
        skip_categories = ["Home & Entertainment", "Health & Wellness", "Category"]
        
        for cat_element in category_elements:
            cat_text = cat_element.text.strip()
            if cat_text:
                # Clean category name (remove counts in parentheses)
                clean_name = cat_text.split("(")[0].strip()
                
                if clean_name not in skip_categories and clean_name:
                    # Create XPath selector for this category
                    xpath_selector = f"//button[@data-testid='btn-category-options' and contains(., '{clean_name}')]"
                    categories.append((clean_name, xpath_selector))
        
        print(f"✅ Found {len(categories)} valid categories")
        for cat_name, _ in categories:
            print(f"   - {cat_name}")
        
        return categories
        
    except Exception as e:
        print(f"❌ Error getting categories: {e}")
        return []
    finally:
        driver.quit()

def optimized_scroll_load(driver):
    """Optimized scrolling for parallel processing"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_step = 800  # Larger steps for speed
    max_scrolls = 20    # Reduced for speed
    scroll_count = 0
    
    while scroll_count < max_scrolls:
        driver.execute_script(f"window.scrollBy(0, {scroll_step});")
        time.sleep(0.3)  # Shorter pause
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        current_position = driver.execute_script("return window.pageYOffset + window.innerHeight")
        
        if current_position >= new_height - 100:
            time.sleep(0.5)  # Shorter final wait
            final_height = driver.execute_script("return document.body.scrollHeight")
            if final_height == new_height:
                break
            new_height = final_height
            
        last_height = new_height
        scroll_count += 1
    
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)

def thorough_scroll_load(driver):
    """More thorough scrolling to match asda.py"""
    print("🔄 Loading all products...")
    
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_step = 800  # Keep same as asda.py
    max_scrolls = 50   # Increase from 20 to match thoroughness
    scroll_count = 0
    no_change_count = 0
    
    while scroll_count < max_scrolls and no_change_count < 5:
        # Scroll down
        driver.execute_script(f"window.scrollBy(0, {scroll_step});")
        time.sleep(0.5)  # Match asda.py timing
        
        # Check if we hit bottom
        new_height = driver.execute_script("return document.body.scrollHeight")
        current_position = driver.execute_script("return window.pageYOffset + window.innerHeight")
        
        # If we're at the bottom, wait longer for lazy loading
        if current_position >= new_height - 100:
            time.sleep(1.5)  # Longer wait like asda.py
            final_height = driver.execute_script("return document.body.scrollHeight")
            if final_height == new_height:
                no_change_count += 1
            else:
                no_change_count = 0
            new_height = final_height
        
        # Check for "Load More" buttons like asda.py
        try:
            load_more_buttons = driver.find_elements(By.CSS_SELECTOR, 
                "button[data-testid*='load'], button[class*='load'], button[class*='more']")
            for btn in load_more_buttons:
                if btn.is_displayed() and btn.is_enabled():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(2)
                    break
        except:
            pass
            
        last_height = new_height
        scroll_count += 1
    
    # Final pause and back to top - match asda.py
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    print("✅ All products loaded")

def enhanced_bulk_scrape(driver):
    """Enhanced scraping with debug info like asda.py"""
    print("🚀 Enhanced bulk scraping...")
    
    # More comprehensive JavaScript with debug output
    js_script = """
    var products = [];
    var productElements = document.querySelectorAll('div.product-module, .product-item, .product-card');
    
    console.log('Found ' + productElements.length + ' product containers');
    
    productElements.forEach(function(product, index) {
        var name = null;
        var price = null;
        
        // Comprehensive name selectors - match asda.py exactly
        var nameSelectors = [
            "a[data-locator='txt-product-name']",
            "[data-testid='product-name'] a",
            "h3 a",
            ".product-name a",
            ".product-title a",
            "a[href*='/product/']",
            ".product-link"
        ];
        
        for (var i = 0; i < nameSelectors.length; i++) {
            var nameElem = product.querySelector(nameSelectors[i]);
            if (nameElem && nameElem.textContent && nameElem.textContent.trim()) {
                name = nameElem.textContent.trim();
                break;
            }
        }
        
        // Comprehensive price selectors - match asda.py exactly
        var priceSelectors = [
            "p[data-locator='txt-product-price']",
            "[data-testid='product-price']",
            ".product-price",
            ".price",
            ".price-current",
            ".co-product__price",
            "[class*='price']"
        ];
        
        for (var i = 0; i < priceSelectors.length; i++) {
            var priceElem = product.querySelector(priceSelectors[i]);
            if (priceElem && priceElem.textContent && priceElem.textContent.trim()) {
                var priceText = priceElem.textContent.trim();
                // Skip if it's just currency symbol or empty
                if (priceText.length > 1 && priceText.includes('£')) {
                    price = priceText;
                    break;
                }
            }
        }
        
        if (name && price) {
            products.push({name: name, price: price, index: index});
        } else {
            // Debug info for missed products
            console.log('Missed product at index ' + index + ':', {
                name: name,
                price: price,
                html: product.innerHTML.substring(0, 200)
            });
        }
    });
    
    console.log('Successfully extracted ' + products.length + ' products');
    return products;
    """
    
    # Execute the script
    products_data = driver.execute_script(js_script)
    print(f"📦 Extracted {len(products_data)} products")
    
    return products_data

def get_max_pages(driver, wait):
    """Get maximum number of pages from pagination"""
    try:
        # Look for the pagination maximum element
        max_page_element = driver.find_element(By.CSS_SELECTOR, "div[data-locator='txt-pagination-page-maximum']")
        max_page_text = max_page_element.text.strip()
        
        # Extract number from text like "of 86"
        import re
        page_match = re.search(r'of (\d+)', max_page_text)
        if page_match:
            max_pages = int(page_match.group(1))
            print(f"   Found {max_pages} total pages")
            return max_pages
        else:
            print(f"   Could not parse max pages from: {max_page_text}")
            return 50  # Fallback
            
    except NoSuchElementException:
        print("   No pagination info found, using default limit")
        return 50  # Fallback if no pagination found
    except Exception as e:
        print(f"   Error getting max pages: {e}")
        return 50  # Fallback

def scrape_single_category(category_info):
    """Scrape a single category with more thorough processing"""
    category_name, category_selector = category_info
    driver = setup_optimized_driver()
    category_products = []
    
    try:
        print(f"Starting category: {category_name}")
        
        # Navigate to ASDA groceries
        driver.get("https://www.asda.com/groceries/search/*")
        time.sleep(3)  # Longer initial wait like asda.py
        
        # Handle cookies
        try:
            wait = WebDriverWait(driver, 10)  # Longer timeout
            accept_cookies = wait.until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            accept_cookies.click()
            time.sleep(1.5)  # Longer wait
        except TimeoutException:
            pass
        
        # Select category with longer waits
        try:
            category_btn = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='div-category-dropdown']"))
            )
            driver.execute_script("arguments[0].click();", category_btn)
            time.sleep(1)
            
            cat_button = driver.find_element(By.XPATH, category_selector)
            driver.execute_script("arguments[0].click();", cat_button)
            time.sleep(3)  # Match asda.py timing
        except Exception as e:
            print(f"Could not select {category_name}: {e}")
            return []
        
        # Wait for initial page load and get max pages
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-module")))
            time.sleep(1)  # Extra wait like asda.py
            max_pages = get_max_pages(driver, wait)
        except TimeoutException:
            print(f"   {category_name}: No products found")
            return []
        
        page_count = 0
        products_in_category = 0
        
        while page_count < max_pages:
            page_count += 1
            print(f"   {category_name}: Page {page_count}/{max_pages}")
            
            # Wait for products with longer timeout
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-module")))
                time.sleep(1)  # Extra wait for dynamic content
            except TimeoutException:
                print(f"   {category_name}: No products on page {page_count}")
                break
            
            # Use the more thorough scrolling
            thorough_scroll_load(driver)
            products_data = enhanced_bulk_scrape(driver)
            
            # Process scraped data with duplicate checking
            page_products = 0
            seen_products = set()
            
            for product in products_data:
                # Create unique identifier to avoid duplicates
                product_id = f"{product['name']}_{product['price']}"
                if product_id not in seen_products:
                    category_products.append({
                        "Category": category_name,
                        "Name": product["name"],
                        "Price": product["price"]
                    })
                    seen_products.add(product_id)
                    page_products += 1
            
            products_in_category += page_products
            print(f"   {category_name}: {page_products} products from page {page_count}")
            
            # Check if we've reached the last page
            if page_count >= max_pages:
                print(f"   {category_name}: Reached last page ({max_pages})")
                break
            
            # Check for next page with longer wait
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "button[data-testid='btn-pagination-next']")
                if not next_btn.is_enabled() or "disabled" in next_btn.get_attribute("class"):
                    print(f"   {category_name}: Next button disabled at page {page_count}")
                    break
                
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(2.5)  # Longer wait between pages like asda.py
                
            except (NoSuchElementException, Exception):
                print(f"   {category_name}: No more pages at page {page_count}")
                break
        
        print(f"{category_name}: Completed - {products_in_category} total products from {page_count} pages")
        return category_products
        
    except Exception as e:
        print(f"Error in {category_name}: {e}")
        return []
    finally:
        driver.quit()

def scrape_asda_parallel():
    """Main function with parallel processing"""
    print("Starting parallel ASDA scraper...")
    start_time = time.time()
    
    # Get all categories dynamically
    categories = get_all_categories()
    
    if not categories:
        print("❌ No categories found!")
        return
    
    print(f"\n🚀 Starting parallel scraping of {len(categories)} categories...")
    
    # Use ThreadPoolExecutor for parallel processing
    # Limit to 3 concurrent threads to be respectful to the server
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all category scraping tasks
        future_to_category = {
            executor.submit(scrape_single_category, category): category[0] 
            for category in categories
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
    
    # Process and save results
    if all_products:
        df = pd.DataFrame(all_products)
        
        # Clean data
        df = df.dropna(subset=['Name', 'Price'])
        df = df[df['Name'].str.strip() != '']
        df = df[df['Price'].str.strip() != '']
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['Name', 'Price'])
        
        # Add cleaned price
        df['Price_Numeric'] = df['Price'].apply(clean_price)
        
        # Sort by category and name
        df = df.sort_values(['Category', 'Name']).reset_index(drop=True)
        
        # Save
        df.to_csv("asda.csv", index=False, encoding="utf-8")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'='*50}")
        print(f"SCRAPING COMPLETED!")
        print(f"Total products: {len(df)}")
        print(f"Total time: {duration:.2f} seconds")
        print(f"Products per second: {len(df)/duration:.2f}")
        print(f"File saved: asda_products_parallel_complete.csv")
        print(f"{'='*50}")
        print(f"📊 By category:")
        category_counts = df['Category'].value_counts()
        for category, count in category_counts.items():
            print(f"   {category}: {count}")
    else:
        print("No products found.")

if __name__ == "__main__":
    scrape_asda_parallel()