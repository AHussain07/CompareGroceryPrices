import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def setup_driver():
    """
    Sets up the Selenium WebDriver.
    
    Returns:
        A Selenium WebDriver instance.
    """
    # Note: Make sure you have the appropriate WebDriver (e.g., chromedriver)
    # in your system's PATH or in the same directory as this script.
    # You can also specify the path to the driver executable like this:
    # driver = webdriver.Chrome(executable_path='/path/to/chromedriver')
    
    options = webdriver.ChromeOptions()
    # Uncomment the line below to run Chrome in headless mode (without a UI)
    # options.add_argument('--headless')
    options.add_argument('--start-maximized')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print(f"Error setting up the WebDriver: {e}")
        print("Please ensure you have Google Chrome and the correct version of ChromeDriver installed.")
        return None
    return driver

def scrape_aldi_page(url, driver, category_name):
    """
    Scrapes product name, brand, price, and image URL from a single Aldi page
    using Selenium to handle dynamic content.

    Args:
        url (str): The URL of the Aldi product page to scrape.
        driver: The Selenium WebDriver instance.
        category_name (str): The name of the category being scraped.

    Returns:
        list: A list of dictionaries, where each dictionary contains data for one product.
    """
    try:
        driver.get(url)
        # Wait for the product grid to be present on the page before scraping.
        # This is the crucial step for handling dynamically loaded content.
        wait = WebDriverWait(driver, 15) # Wait for a maximum of 15 seconds
        product_container_selector_css = 'a.product-tile__link'
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, product_container_selector_css)))
    except TimeoutException:
        print(f"Timed out waiting for page content to load at {url}. It's possible there are no products on this page.")
        return []
    except Exception as e:
        print(f"An error occurred while loading the page {url}: {e}")
        return []

    # Get the page source after JavaScript has rendered the content.
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # CSS selectors for the product details.
    product_container_selector = 'a.product-tile__link'
    product_brand_selector = 'div.product-tile__brandname p'
    product_name_selector = 'div.product-tile__name p'
    product_price_selector = 'span.base-price__regular'
    #product_image_selector = 'img.base-image'

    products = soup.select(product_container_selector)
    scraped_data = []

    for product in products:
        try:
            brand_element = product.select_one(product_brand_selector)
            name_element = product.select_one(product_name_selector)
            price_element = product.select_one(product_price_selector)

            brand = brand_element.get_text(strip=True) if brand_element else ''
            name = name_element.get_text(strip=True) if name_element else 'N/A'
            price = price_element.get_text(strip=True) if price_element else 'N/A'
            
            # Combine brand and name if brand exists
            full_name = f"{brand} {name}" if brand else name
            
            scraped_data.append({
                'category': category_name,
                'name': full_name.strip(),
                'price': price
            })
        except Exception as e:
            print(f"Error parsing a product: {e}")
            continue

    return scraped_data

if __name__ == '__main__':
    # --- CONFIGURATION ---
    # List of all the base URLs for the categories you want to scrape.
    CATEGORY_URLS = [
        "https://www.aldi.co.uk/products/fresh-food/k/1588161416978050",
        "https://www.aldi.co.uk/products/bakery/k/1588161416978049",
        "https://www.aldi.co.uk/products/chilled-food/k/1588161416978051",
        "https://www.aldi.co.uk/products/food-cupboard/k/1588161416978053",
        "https://www.aldi.co.uk/products/drinks/k/1588161416978054",
        "https://www.aldi.co.uk/products/alcohol/k/1588161416978055",
        "https://www.aldi.co.uk/products/frozen-food/k/1588161416978056",
        "https://www.aldi.co.uk/products/vegetarian-plant-based/k/1588161421881163",
        "https://www.aldi.co.uk/products/baby-toddler/k/1588161416978057",
        "https://www.aldi.co.uk/products/pet-care/k/1588161416978060"
    ]
    OUTPUT_FILE = "aldi.csv"
    # --- END CONFIGURATION ---

    driver = setup_driver()
    if driver is None:
        exit() # Exit if the driver could not be initialized.
        
    all_products_data = []
    
    print("Starting the Aldi product scraper for all categories...")

    # Loop through each category URL.
    for base_url in CATEGORY_URLS:
        # Extract the category name from the URL for the new column.
        try:
            category_name = base_url.split('/')[4].replace('-', ' ').title()
        except IndexError:
            category_name = "Unknown"

        print(f"\n--- Scraping Category: {category_name} ---")
        page = 1
        
        while True:
            current_url = f"{base_url}?page={page}"
            print(f"Scraping page {page}: {current_url}")
            
            products_on_page = scrape_aldi_page(current_url, driver, category_name)

            if not products_on_page:
                print("No more products found in this category. Moving to the next one.")
                break
            
            all_products_data.extend(products_on_page)
            page += 1
            time.sleep(1) # Be polite to the server

    # Close the browser once all categories are scraped.
    driver.quit()

    if all_products_data:
        df = pd.DataFrame(all_products_data)
        # Remove duplicate products based on category, combined name, and price
        df.drop_duplicates(subset=['category', 'name', 'price'], inplace=True)
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print(f"\nScraping complete. Found {len(df)} unique products across all categories.")
        print(f"Data saved to {OUTPUT_FILE}")
    else:
        print("Scraping failed or no products were found across all specified URLs.")
