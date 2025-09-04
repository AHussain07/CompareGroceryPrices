"use client"

import { useState, useEffect, useRef } from "react"
import { ShoppingCart, ArrowRight, ArrowLeft, Plus, X, AlertTriangle } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"

// CSV Parser functions
const parseCSV = (csvText) => {
  try {
    const lines = csvText.trim().split("\n")
    console.log("Total lines in CSV:", lines.length)

    if (lines.length < 2) {
      throw new Error("CSV must have at least a header and one data row")
    }

    const headers = lines[0].split(",").map((header) => header.replace(/"/g, "").trim())
    console.log("CSV headers:", headers)

    const products = []

    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim()
      if (!line) continue // Skip empty lines

      // Handle CSV parsing with quoted values
      const values = []
      let current = ""
      let inQuotes = false

      for (let j = 0; j < line.length; j++) {
        const char = line[j]
        if (char === '"') {
          inQuotes = !inQuotes
        } else if (char === "," && !inQuotes) {
          values.push(current.trim())
          current = ""
        } else {
          current += char
        }
      }
      values.push(current.trim()) // Add the last value

      if (values.length >= headers.length) {
        const product = {}
        headers.forEach((header, index) => {
          product[header] = values[index]?.replace(/"/g, "").trim() || ""
        })

        // Handle different CSV structures
        const name = product.name || product.Name || product["Product Name"]
        const price = product.price || product.Price
        const category = product.category || product.Category

        if (name && name.length > 2 && price) {
          products.push({
            name: name,
            price: price,
            category: category || "General"
          })
        }
      }
    }

    console.log(`Successfully parsed ${products.length} valid products`)
    return products
  } catch (error) {
    console.error("Error parsing CSV:", error)
    return []
  }
}

const loadSupermarketProducts = async (supermarketName) => {
  console.log(`🔍 Debug: Attempting to load products for: "${supermarketName}"`)
  
  try {
    // Map supermarket names to their CSV files - include all possible variations
    const csvFiles = {
      "ALDI": "/aldi.csv",
      "Tesco": "/tesco.csv",
      "TESCO": "/tesco.csv",
      "Sainsbury's": "/sainsburys.csv",
      "SAINSBURY'S": "/sainsburys.csv",    // This is the key line you were missing!
      "Sainsburys": "/sainsburys.csv",
      "SAINSBURYS": "/sainsburys.csv",
      "Morrisons": "/morrisons.csv", 
      "MORRISONS": "/morrisons.csv",
      "ASDA": "/asda.csv"
    }

    console.log(`🔍 Debug: Available CSV files:`, Object.keys(csvFiles))
    console.log(`🔍 Debug: Looking for mapping for: "${supermarketName}"`)

    let csvFile = csvFiles[supermarketName]
    
    if (!csvFile) {
      console.warn(`No CSV file found for "${supermarketName}", available options:`, Object.keys(csvFiles))
      console.warn(`Using ALDI as fallback`)
      csvFile = "/aldi.csv"
    } else {
      console.log(`✅ Found CSV file: ${csvFile} for ${supermarketName}`)
    }

    console.log(`Attempting to fetch CSV from: ${csvFile} for ${supermarketName}`)
    const response = await fetch(csvFile)

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status} for ${csvFile}`)
    }

    const csvText = await response.text()
    console.log("CSV text length:", csvText.length)
    console.log("First 200 characters:", csvText.substring(0, 200))

    if (!csvText || csvText.trim().length === 0) {
      throw new Error("CSV file is empty")
    }

    const products = parseCSV(csvText)
    console.log(`Successfully parsed ${products.length} products from ${supermarketName}`)

    if (products.length > 0) {
      console.log("Sample products:", products.slice(0, 3))
    }

    return products
  } catch (error) {
    console.error(`Error loading ${supermarketName} products:`, error)
    
    // Return fallback data
    return [
      { name: "Milk Whole 2 Pint", category: "Dairy", price: "£1.15" },
      { name: "Bread White Loaf", category: "Bakery", price: "£0.36" },
      { name: "Eggs Free Range 12 Pack", category: "Dairy", price: "£2.29" },
    ]
  }
}

// Enhanced search function with relevance scoring
const searchProducts = (products, searchTerm, maxResults = 8) => {
  if (!searchTerm || searchTerm.length < 2) return [];
  
  const searchValue = searchTerm.toLowerCase().trim();
  
  // Calculate relevance score for each product
  const scoredProducts = products
    .map(product => {
      const name = product.name.toLowerCase();
      const category = (product.category || '').toLowerCase();
      
      let score = 0;
      
      // Exact match gets highest score
      if (name === searchValue) {
        score += 1000;
      }
      
      // Starts with search term gets very high score
      else if (name.startsWith(searchValue)) {
        score += 500;
      }
      
      // Word boundary matches (whole word at start or after space)
      else if (name.startsWith(searchValue + ' ') || name.includes(' ' + searchValue)) {
        score += 300;
      }
      
      // Contains search term
      else if (name.includes(searchValue)) {
        score += 100;
        
        // Bonus for appearing early in the name
        const position = name.indexOf(searchValue);
        score += Math.max(0, 50 - position);
      }
      
      // Category matches get lower priority
      if (category.includes(searchValue)) {
        score += 20;
      }
      
      // Penalize very long names (they're often less relevant)
      if (name.length > 50) {
        score -= 10;
      }
      
      // Bonus for common product types based on search term
      const commonTerms = {
        'milk': ['milk', 'dairy'],
        'bread': ['bread', 'loaf', 'bakery'],
        'eggs': ['eggs', 'egg', 'free range'],
        'chicken': ['chicken', 'breast', 'thigh'],
        'cheese': ['cheese', 'cheddar', 'mozzarella'],
        'apple': ['apple', 'fruit'],
        'banana': ['banana', 'fruit'],
        'rice': ['rice', 'grain'],
        'pasta': ['pasta', 'spaghetti', 'penne'],
        'yogurt': ['yogurt', 'yoghurt', 'dairy']
      };
      
      Object.entries(commonTerms).forEach(([term, keywords]) => {
        if (searchValue.includes(term)) {
          keywords.forEach(keyword => {
            if (name.includes(keyword)) {
              score += 50;
            }
          });
        }
      });
      
      return { ...product, relevanceScore: score };
    })
    .filter(product => product.relevanceScore > 0)
    .sort((a, b) => {
      // First sort by relevance score (descending)
      if (b.relevanceScore !== a.relevanceScore) {
        return b.relevanceScore - a.relevanceScore;
      }
      
      // Then by name length (shorter names first for same relevance)
      if (a.name.length !== b.name.length) {
        return a.name.length - b.name.length;
      }
      
      // Finally alphabetically
      return a.name.localeCompare(b.name);
    })
    .slice(0, maxResults);
  
  return scoredProducts;
};

export default function ShoppingListPage() {
  const [selectedSupermarket, setSelectedSupermarket] = useState("")
  const [shoppingList, setShoppingList] = useState([""])
  const [suggestions, setSuggestions] = useState([])
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(-1)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [focusedInputIndex, setFocusedInputIndex] = useState(-1)
  const [aldiProducts, setAldiProducts] = useState([])
  const [isLoadingProducts, setIsLoadingProducts] = useState(true)
  const [isSelectingSuggestion, setIsSelectingSuggestion] = useState(false)
  const [isMobile, setIsMobile] = useState(false);
  const navigate = useNavigate()
  const inputRefs = useRef([])

  useEffect(() => {
    // Get the selected supermarket from localStorage
    const supermarket = localStorage.getItem("selectedSupermarket")
    if (supermarket) {
      setSelectedSupermarket(supermarket)
    } else {
      // If no supermarket selected, redirect back
      navigate("/select-supermarket")
      return
    }

    // Load products from the selected supermarket's CSV
    const loadProducts = async () => {
      setIsLoadingProducts(true)
      try {
        const products = await loadSupermarketProducts(supermarket)
        setAldiProducts(products) // Keep the same state name for now
        console.log(`Products loaded successfully for ${supermarket}:`, products.length)
      } catch (error) {
        console.error("Failed to load products:", error)
      } finally {
        setIsLoadingProducts(false)
      }
    }

    loadProducts()
  }, [navigate])

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    // Initial check
    handleResize();

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const addItem = () => {
    // Check if the last item is empty (trim to handle spaces)
    const lastItem = shoppingList[shoppingList.length - 1]
    if (lastItem.trim() === "") {
      // If the last item is empty, focus on it instead of adding a new one
      const lastIndex = shoppingList.length - 1
      if (inputRefs.current[lastIndex]) {
        inputRefs.current[lastIndex].focus()
      }
      return
    }

    // Only add a new item if the last item has content
    setShoppingList([...shoppingList, ""])
    // Focus the new input after a short delay
    setTimeout(() => {
      const newIndex = shoppingList.length
      if (inputRefs.current[newIndex]) {
        inputRefs.current[newIndex].focus()
      }
    }, 100)
  }

  const removeItem = (index) => {
    if (shoppingList.length > 1) {
      // Multiple items: remove the item at the specified index
      setShoppingList(shoppingList.filter((_, i) => i !== index))
      setShowSuggestions(false)
    } else if (shoppingList.length === 1 && shoppingList[0].trim() !== "") {
      // Single item with content: clear it instead of removing
      setShoppingList([""])
      setShowSuggestions(false)
    }
    // If it's the last empty item, do nothing (X button shouldn't be visible anyway)
  }

  const updateItem = (index, value) => {
    if (isSelectingSuggestion) return // Prevent overwriting when a suggestion is selected

    const newList = [...shoppingList]
    newList[index] = value
    setShoppingList(newList)

    // Only show suggestions if typing (not selecting)
    if (value.length > 1 && !value.includes("£") && aldiProducts.length > 0) {
      // Use the improved search function
      const filteredSuggestions = searchProducts(aldiProducts, value, 8);

      setSuggestions(filteredSuggestions)
      setShowSuggestions(filteredSuggestions.length > 0)
      setFocusedInputIndex(index)
      setActiveSuggestionIndex(-1)
    } else {
      setShowSuggestions(false)
    }
  }

  const handleKeyDown = (e, index) => {
    if (!showSuggestions || suggestions.length === 0) return

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault()
        setActiveSuggestionIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0))
        break
      case "ArrowUp":
        e.preventDefault()
        setActiveSuggestionIndex((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1))
        break
      case "Enter":
        e.preventDefault()
        if (activeSuggestionIndex >= 0) {
          selectSuggestion(suggestions[activeSuggestionIndex], index)
        }
        break
      case "Escape":
        setShowSuggestions(false)
        setActiveSuggestionIndex(-1)
        break
      default:
        // Handle any other keys normally
        break
    }
  }

  const capitalizeFirstLetter = (string) => {
    return string.charAt(0).toUpperCase() + string.slice(1)
  }

  const renderSuggestion = (suggestion) => {
    // Clean the price to handle both formats (£1.50 and actual price£1.50)
    let cleanPrice = suggestion.price.replace(/actual price/i, '').trim()
    if (!cleanPrice.startsWith('£')) {
      cleanPrice = `£${cleanPrice}`
    }
    
    const formattedName = capitalizeFirstLetter(suggestion.name)
    const formattedCategory = suggestion.category ? capitalizeFirstLetter(suggestion.category) : ''

    return (
      <div className="suggestion-content">
        <div className="suggestion-text">
          <div className="suggestion-main">
            <span className="suggestion-name">{formattedName}</span>
            {formattedCategory && (
              <span className="suggestion-brand">{formattedCategory}</span>
            )}
          </div>
          <span className="suggestion-price">{cleanPrice}</span>
        </div>
      </div>
    )
  }

  const selectSuggestion = (suggestion, index, e) => {
    if (e) {
      e.preventDefault()
      e.stopPropagation()
    }

    // Temporarily disable the onChange handler
    setIsSelectingSuggestion(true)

    // Clean the price to handle both formats
    let cleanPrice = suggestion.price.replace(/actual price/i, '').replace(/[£$]/g, '').trim()
    const numericPrice = parseFloat(cleanPrice)

    // Function to remove brand names from selected products (mobile only)
    const removeBrandNames = (productName) => {
      if (!isMobile) return productName; // Only apply on mobile
    
      const commonBrands = [
        // Major supermarket own brands
        'ALDI', 'TESCO', 'SAINSBURY\'S', 'SAINSBURYS', 'MORRISONS', 'ASDA',
        'EVERYDAY VALUE', 'SAVERS', 'SMARTPRICE', 'VALUE', 'BASICS',
        
        // Common food brands
        'COCA COLA', 'COCA-COLA', 'PEPSI', 'HEINZ', 'KELLOGG\'S', 'KELLOGGS',
        'NESTLE', 'NESTLÉ', 'CADBURY', 'MARS', 'WALKER\'S', 'WALKERS',
        'MCVITIE\'S', 'MCVITIES', 'TETLEY', 'PG TIPS', 'NESCAFE', 'NESCAFÉ',
        'BIRDSEYE', 'BIRDS EYE', 'FINDUS', 'YOUNG\'S', 'YOUNGS',
        'HOVIS', 'WARBURTONS', 'MOTHER PRIDE', 'KINGSMILL',
        'ANCHOR', 'LURPAK', 'FLORA', 'COUNTRY LIFE', 'UTTERLY BUTTERLY',
        'MULLER', 'DANONE', 'ACTIVIA', 'YOPLAIT', 'ONKEN',
        'PHILADELPHIA', 'DAIRYLEA', 'BABYBEL', 'CATHEDRAL CITY',
        'COWBELLE', 'ARLA', 'CRAVENDALE', 'LACTOFREE',
        'INNOCENT', 'TROPICANA', 'ROBINSONS', 'RIBENA',
        'UNCLE BEN\'S', 'UNCLE BENS', 'DOLMIO', 'LOYD GROSSMAN',
        'SHARWOOD\'S', 'SHARWOODS', 'PATAK\'S', 'PATAKS',
        'JOHN WEST', 'PRINCES', 'TUNA CHUNKS', 'SALMON FILLET',
      ];
      
      let cleanName = productName.toUpperCase();
      
      // Remove brand names that appear at the start
      for (const brand of commonBrands) {
        const brandPattern = new RegExp(`^${brand.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s+`, 'i');
        cleanName = cleanName.replace(brandPattern, '');
      }
      
      // Remove common prefixes
      const prefixesToRemove = [
        'THE ', 'A ', 'AN ',
        'FRESH ', 'FROZEN ', 'CHILLED ',
        'ORGANIC ', 'FREE RANGE ', 'BRITISH ',
        'FINEST ', 'TASTE THE DIFFERENCE ', 'EXTRA SPECIAL ',
        'SIMPLY ', 'PURELY ', 'NATURALLY '
      ];
      
      for (const prefix of prefixesToRemove) {
        const prefixPattern = new RegExp(`^${prefix}`, 'i');
        cleanName = cleanName.replace(prefixPattern, '');
      }
      
      // Clean up extra spaces and return with proper capitalization
      return cleanName
        .replace(/\s+/g, ' ')
        .trim()
        .split(' ')
        .map(word => word.charAt(0) + word.slice(1).toLowerCase())
        .join(' ');
    };

    // Apply brand removal only to selected products on mobile
    const displayName = removeBrandNames(suggestion.name);
    
    // Format name differently for mobile vs desktop
    const formattedName = isMobile 
      ? capitalizeFirstLetter(displayName) // Mobile: no price shown
      : `${capitalizeFirstLetter(displayName)} - £${numericPrice.toFixed(2)}`; // Desktop: with price
  
    // Update shopping list directly
    const newList = [...shoppingList]
    newList[index] = formattedName
    setShoppingList(newList)

    // Store selection in localStorage (keep original name for matching)
    const selectedProducts = JSON.parse(localStorage.getItem("selectedProducts") || "[]")
    selectedProducts[index] = {
      name: suggestion.name, // Keep original name for backend matching
      displayName: displayName, // Add cleaned name for display
      price: numericPrice.toFixed(2),
      category: suggestion.category,
      store: selectedSupermarket,
    }
    localStorage.setItem("selectedProducts", JSON.stringify(selectedProducts))

    // Reset states
    setShowSuggestions(false)
    setActiveSuggestionIndex(-1)
    setFocusedInputIndex(-1)

    // Re-enable the onChange handler after a short delay
    setTimeout(() => {
      setIsSelectingSuggestion(false)
    }, 300)
  }

  const handleInputFocus = (index) => {
    setFocusedInputIndex(index)
    const value = shoppingList[index]

    // Don't show suggestions if the value already contains a price (indicating it's a selected product)
    if (value.includes("£")) {
      setShowSuggestions(false)
      return
    }

    if (value.length > 1 && aldiProducts.length > 0) {
      // Use the improved search function
      const filteredSuggestions = searchProducts(aldiProducts, value, 8);

      setSuggestions(filteredSuggestions)
      setShowSuggestions(filteredSuggestions.length > 0)
    }
  }

  const handleInputBlur = () => {
    // Delay hiding suggestions to allow clicking on them
    setTimeout(() => {
      setShowSuggestions(false)
      setFocusedInputIndex(-1)
    }, 200)
  }

  const handleCompare = () => {
    const filteredList = shoppingList.filter((item) => item.trim() !== "")
    if (filteredList.length > 0) {
      // Store the shopping list and matched products in localStorage
      localStorage.setItem("shoppingList", JSON.stringify(filteredList))

      const matchedProducts = filteredList.map((item) => {
        const matchedProduct = aldiProducts.find((product) => product.name.toLowerCase().includes(item.toLowerCase()))
        return {
          searchTerm: item,
          product: matchedProduct || null,
        }
      })
      localStorage.setItem("matchedProducts", JSON.stringify(matchedProducts))

      // Navigate to the results page
      navigate("/results")
    }
  }

  const hasValidItems = shoppingList.some((item) => item.trim() !== "")

  const lastItemIsEmpty = shoppingList[shoppingList.length - 1].trim() === ""

  return (
    <div className="page-container">
      {/* Header */}
      <header className="header">
        <div className="container">
          <div className="header-content">
            <Link to="/" className="logo">
              <ShoppingCart className="logo-icon" />
              <span className="logo-text">CompareGroceryPrices</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <section className="shopping-list-section">
        <div className="container">
          <div className="shopping-content">
            <div className="progress-bar">
              <div className="progress-step completed">1</div>
              <div className="progress-line completed"></div>
              <div className="progress-step active">2</div>
              <div className="progress-line"></div>
              <div className="progress-step">3</div>
            </div>

            <h1 className="shopping-title">What's on your shopping list?</h1>
            <p className="shopping-description">
              Add the items you need to buy. We'll compare prices across all major supermarkets and show you where to
              get the best deals.
            </p>

            {selectedSupermarket && (
              <div className="current-store">
                <span>
                  Currently shopping at: <strong>{selectedSupermarket}</strong>
                </span>
              </div>
            )}

            <div className="shopping-list-container">
              <h3 className="list-title">Your Shopping List</h3>
              {/* <p className="list-subtitle">
                {isLoadingProducts ? "Loading product suggestions..." : "Start typing to see product suggestions"}
              </p> */}

              <div className="items-list">
                {shoppingList.map((item, index) => (
                  <div key={index} className="item-input-group">
                    <div className="input-wrapper">
                      <input
                        ref={(el) => (inputRefs.current[index] = el)}
                        type="text"
                        value={item}
                        onChange={(e) => updateItem(index, e.target.value)}
                        onKeyDown={(e) => handleKeyDown(e, index)}
                        onFocus={() => handleInputFocus(index)}
                        onBlur={handleInputBlur}
                        placeholder={isMobile ? `Item ${index + 1}` : `Item ${index + 1} (e.g. Milk, Bread, Eggs)`}
                        className="item-input"
                        autoComplete="off"
                        disabled={isLoadingProducts}
                      />

                      {/* X button inside the input field */}
                      {(shoppingList.length > 1 || (shoppingList.length === 1 && item.trim() !== "")) && (
                        <button 
                          onClick={() => removeItem(index)} 
                          className="remove-item-btn-inside" 
                          type="button"
                          aria-label="Remove item"
                        >
                          <X className="remove-icon" />
                        </button>
                      )}

                      {/* Suggestions Dropdown */}
                      {showSuggestions && focusedInputIndex === index && suggestions.length > 0 && (
                        <div className="suggestions-dropdown">
                          {suggestions.map((suggestion, suggestionIndex) => (
                            <div
                              key={suggestionIndex}
                              className={`suggestion-item ${suggestionIndex === activeSuggestionIndex ? "active" : ""}`}
                              onClick={(e) => selectSuggestion(suggestion, index, e)}
                            >
                              {renderSuggestion(suggestion)}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <button 
                onClick={addItem} 
                className={`add-item-btn ${lastItemIsEmpty ? "disabled" : ""}`}
                disabled={isLoadingProducts || lastItemIsEmpty}
              >
                <Plus className="add-icon" />
                Add Another Item
              </button>
            </div>

            {/* Cannot Find Product Section */}
            <div className="missing-product-section">
              <div className="missing-product-icon">
                <AlertTriangle />
              </div>
              <h3 className="missing-product-title">Cannot find a product?</h3>
              <p className="missing-product-description">
                If you can't find a specific product or brand in our database, let us know and we'll add it for future comparisons.
              </p>
              <Link 
                to="/contact?category=missing-item" 
                className="report-missing-link"
              >
                Report Missing Item
              </Link>
            </div>

            <div className="action-buttons">
              <Link to="/select-supermarket" className="back-button">
                <ArrowLeft className="button-icon" />
                Back
              </Link>

              <button
                onClick={handleCompare}
                disabled={!hasValidItems || isLoadingProducts}
                className={`compare-button ${!hasValidItems || isLoadingProducts ? "disabled" : ""}`}
              >
                Compare Prices
                <ArrowRight className="button-icon" />
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}