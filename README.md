# CompareGroceryPrices 🛒

**🌐 Live Website: [https://www.comparegroceryprices.uk/](https://www.comparegroceryprices.uk/)**

A modern web application that helps users compare grocery prices across major UK supermarkets to find the best deals and save money on their weekly shopping.

![CompareGroceryPrices](https://img.shields.io/badge/Status-Live-brightgreen)
![Next.js](https://img.shields.io/badge/Next.js-13+-black)
![React](https://img.shields.io/badge/React-18+-blue)
![CSS3](https://img.shields.io/badge/CSS3-Responsive-orange)

## 🌟 Features

- **Multi-Supermarket Comparison**: Compare prices across ASDA, Tesco, Morrisons, Sainsbury's, and ALDI
- **Smart Product Matching**: Advanced algorithm matches products across different stores using fuzzy search
- **Intelligent Suggestions**: Real-time product suggestions with autocomplete functionality
- **Savings Calculator**: Calculate potential monthly and annual savings
- **Mobile-First Design**: Fully responsive design optimized for all devices
- **Shopping List Builder**: Create and manage your shopping list with ease
- **Missing Product Reporting**: Report products not found in our database

## 🛠️ Tech Stack

- **Framework**: Next.js 13+
- **Frontend**: React 18+
- **Styling**: Custom CSS with CSS Variables
- **Data Processing**: Custom CSV parser
- **Search Algorithm**: Levenshtein distance for fuzzy matching
- **Routing**: React Router
- **State Management**: React Hooks (useState, useEffect, useRef)

---

## 🤖 Webscraping & Automation

To ensure up-to-date and accurate supermarket prices, this project uses automated webscraping scripts for each supported supermarket.

- **Scripts Location**: `scrapers/` directory (`asda.py`, `tesco.py`, `aldi.py`, `morrisons.py`). Each writes `<store>.csv`.
- **Automation**: A single GitHub Actions workflow, `.github/workflows/scrapers.yml`, runs twice a week (Monday & Thursday) to scrape every store.
- **Safety guard**: `scrapers/apply_update.py` only publishes a store's new CSV to `app/public/` if its row count is within 10% of the previous week's — a broken or partial scrape is discarded rather than shipped.
- **Dependencies**: Listed in `scrapers/requirements.txt` (Playwright for ALDI/Morrisons, curl_cffi + BeautifulSoup for Tesco; ASDA uses the stdlib only).

> Note: Sainsbury's has no 2026 scraper yet, so `app/public/sainsburys.csv` is not refreshed by this workflow.


## 📋 How It Works

1. **Select Your Preferred Supermarket**: Choose your primary shopping destination
2. **Build Your Shopping List**: Add items with intelligent autocomplete suggestions
3. **Compare Prices**: Our algorithm finds matching products across all supermarkets
4. **View Results**: See detailed price comparisons and potential savings
5. **Make Informed Decisions**: Choose where to shop for maximum savings

## 🧮 Key Algorithms

### Product Matching Algorithm
- **Fuzzy String Matching**: Uses Levenshtein distance to find similar products
- **Keyword Extraction**: Identifies key product attributes (brand, size, type)
- **Relevance Scoring**: Ranks matches based on similarity and relevance
- **Price Normalization**: Handles different pricing formats and units

### Search & Suggestions
- **Real-time Filtering**: Instant search results as you type
- **Smart Autocomplete**: Suggests products based on partial input
- **Category Awareness**: Groups similar products for better matching

## 💰 Savings Calculation

The app calculates potential savings by:
- Comparing prices across all supported supermarkets
- Identifying the cheapest option for each product
- Calculating total basket savings
- Projecting monthly and annual savings potential

## 🔮 Future Enhancements

- [ ] User accounts and saved shopping lists
- [ ] Price history tracking and trends
- [ ] Push notifications for price drops
- [ ] Store location finder with distance calculation
- [ ] Barcode scanning functionality
- [ ] Recipe-based shopping lists
- [ ] Meal planning integration
- [ ] API integration for real-time prices

## 🤝 Contributing

We welcome contributions! Please feel free to submit issues, feature requests, or pull requests.