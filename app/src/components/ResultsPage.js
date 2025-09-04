import { useState, useEffect } from "react"
import { ShoppingCart, ArrowLeft, TrendingDown, Store, Search} from 'lucide-react'
import { Link, useNavigate } from "react-router-dom"

// Enhanced Product Matcher Class
class ProductMatcher {
  constructor() {
    this.normalizedProducts = new Map()
    this.allProducts = []
    this.priceThreshold = 5
    this.similarityThreshold = 0.4 // Lowered from 0.6 to find more matches
    this.synonyms = {
      // Common product synonyms
      'milk': ['milk', 'dairy'],
      'bread': ['bread', 'loaf', 'baguette', 'roll'],
      'cheese': ['cheese', 'cheddar', 'mozzarella', 'brie', 'gouda'],
      'yogurt': ['yogurt', 'yoghurt'],
      'biscuits': ['biscuits', 'cookies', 'crackers'],
      'crisps': ['crisps', 'chips'],
      'chicken': ['chicken', 'poultry'],
      'beef': ['beef', 'steak', 'mince'],
      'pasta': ['pasta', 'spaghetti', 'penne', 'fusilli'],
      'rice': ['rice', 'basmati', 'jasmine'],
      'oil': ['oil', 'olive', 'vegetable', 'sunflower'],
      'butter': ['butter', 'margarine', 'spread'],
      'juice': ['juice', 'drink', 'beverage'],
      'cereal': ['cereal', 'cornflakes', 'muesli', 'granola'],
      'tomato': ['tomato', 'tomatoes'],
      'potato': ['potato', 'potatoes', 'spuds'],
      'apple': ['apple', 'apples'],
      'banana': ['banana', 'bananas'],
      'onion': ['onion', 'onions'],
      'carrot': ['carrot', 'carrots'],
      'bell_pepper': ['pepper', 'peppers', 'capsicum'], // Renamed to avoid conflict
      'cucumber': ['cucumber'],
      'lettuce': ['lettuce', 'salad', 'leaves'],
      'salmon': ['salmon', 'fish'],
      'tuna': ['tuna', 'fish'],
      'ham': ['ham', 'bacon'],
      'soap': ['soap', 'wash', 'cleaner'],
      'shampoo': ['shampoo', 'hair'],
      'detergent': ['detergent', 'washing', 'liquid'],
      'toilet': ['toilet', 'tissue', 'paper'],
      'tea': ['tea', 'bags'],
      'coffee': ['coffee', 'instant', 'ground'],
      'sugar': ['sugar', 'sweetener'],
      'flour': ['flour', 'plain', 'self-raising'],
      'salt': ['salt', 'sea', 'table'],
      'black_pepper': ['pepper', 'black', 'white', 'ground'] // Renamed to avoid conflict
    }
    
    this.brandVariations = {
      // Common brand variations and generics
      'own brand': ['own brand', 'everyday', 'value', 'basic', 'essential'],
      'organic': ['organic', 'bio', 'natural'],
      'free range': ['free range', 'outdoor bred'],
      'low fat': ['low fat', 'reduced fat', 'light'],
      'whole': ['whole', 'full fat'],
      'semi skimmed': ['semi skimmed', 'semi-skimmed', '2%'],
      'skimmed': ['skimmed', 'fat free', '0%']
    }
  }

  normalizeProductName(name) {
    return name
      .toLowerCase()
      // Remove brand names and store-specific terms
      .replace(/(tesco|sainsbury's|aldi|morrisons|asda|specially selected|everyday essentials|hearty food co|nature's pick|willow farms)/gi, '')
      // Remove size/weight indicators but keep them for later matching
      .replace(/\b\d+\s*(g|kg|ml|l|cl|pack|pieces|count|x|pint|litre|gram|kilogram|millilitre)\b/g, '')
      // Remove common descriptors that don't affect product identity
      .replace(/\b(fresh|frozen|chilled|ambient|long life|uht|new|improved|extra|super|premium|deluxe|finest|taste the difference)\b/g, '')
      // Clean up punctuation and extra spaces
      .replace(/[^\w\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
  }

  extractKeywords(name) {
    const normalized = this.normalizeProductName(name)
    const words = normalized.split(' ').filter(word => word.length > 2)
    const keywords = new Set(words)
    
    // Add synonyms
    words.forEach(word => {
      Object.entries(this.synonyms).forEach(([key, synonymList]) => {
        if (synonymList.includes(word) || word.includes(key)) {
          synonymList.forEach(syn => keywords.add(syn))
        }
      })
    })
    
    return Array.from(keywords)
  }

  extractPrice(priceStr) {
    if (!priceStr || priceStr === 'N/A') return null
    
    // Handle ASDA's "actual price£X.XX" format
    let cleanPrice = priceStr.toString().replace(/actual price/i, '').trim()
    
    const match = cleanPrice.match(/£?(\d+\.?\d*)/)
    return match ? parseFloat(match[1]) : null
  }

  // Enhanced similarity calculation
  calculateSimilarity(searchTerm, productName) {
    const searchKeywords = this.extractKeywords(searchTerm)
    const productKeywords = this.extractKeywords(productName)
    
    // Exact match
    if (this.normalizeProductName(searchTerm) === this.normalizeProductName(productName)) {
      return 1.0
    }
    
    // Jaccard similarity (intersection over union)
    const searchSet = new Set(searchKeywords)
    const productSet = new Set(productKeywords)
    const intersection = new Set([...searchSet].filter(x => productSet.has(x)))
    const union = new Set([...searchSet, ...productSet])
    
    let jaccardSimilarity = intersection.size / union.size
    
    // Boost for word order preservation
    const searchWords = searchKeywords.join(' ')
    const productWords = productKeywords.join(' ')
    if (productWords.includes(searchWords) || searchWords.includes(productWords)) {
      jaccardSimilarity += 0.2
    }
    
    // Boost for partial word matches
    let partialMatches = 0
    searchKeywords.forEach(searchWord => {
      productKeywords.forEach(productWord => {
        if (searchWord.length >= 3 && productWord.length >= 3) {
          if (searchWord.includes(productWord) || productWord.includes(searchWord)) {
            partialMatches++
          }
        }
      })
    })
    
    const partialBoost = (partialMatches / Math.max(searchKeywords.length, productKeywords.length)) * 0.3
    
    return Math.min(1.0, jaccardSimilarity + partialBoost)
  }

  // Levenshtein distance for fuzzy matching
  levenshteinDistance(str1, str2) {
    const matrix = []
    
    for (let i = 0; i <= str2.length; i++) {
      matrix[i] = [i]
    }
    
    for (let j = 0; j <= str1.length; j++) {
      matrix[0][j] = j
    }
    
    for (let i = 1; i <= str2.length; i++) {
      for (let j = 1; j <= str1.length; j++) {
        if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1]
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1, // substitution
            matrix[i][j - 1] + 1,     // insertion
            matrix[i - 1][j] + 1      // deletion
          )
        }
      }
    }
    
    return matrix[str2.length][str1.length]
  }

  addProduct(name, price, store, category) {
    const product = {
      originalName: name,
      normalizedName: this.normalizeProductName(name),
      keywords: this.extractKeywords(name),
      price: this.extractPrice(price),
      store,
      category: category || ''
    }
    
    this.allProducts.push(product)
    
    // Also add to normalized map for quick lookup
    if (!this.normalizedProducts.has(product.normalizedName)) {
      this.normalizedProducts.set(product.normalizedName, [])
    }
    this.normalizedProducts.get(product.normalizedName).push(product)
  }

  loadProductsFromCSV(csvText, store) {
    const lines = csvText.trim().split('\n')
    if (lines.length < 2) return
    
    const headers = lines[0].split(',').map(h => h.replace(/"/g, '').trim())
    
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim()
      if (!line) continue

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
      values.push(current.trim())

      if (values.length >= headers.length) {
        const product = {}
        headers.forEach((header, index) => {
          product[header] = values[index]?.replace(/"/g, "").trim() || ""
        })

        // Handle both naming conventions (name/Name, price/Price, category/Category)
        const name = product.name || product.Name
        const price = product.price || product.Price
        const category = product.category || product.Category

        if (name && name.length > 2 && price) {
          this.addProduct(name, price, store, category)
        }
      }
    }
  }

  // Enhanced: Find similar products with corrected scoring
  findSimilarProducts(searchTerm) {
    const searchKeywords = this.extractKeywords(searchTerm)
    
    // Score all products
    const scoredProducts = this.allProducts
      .map(product => {
        let similarity = this.calculateSimilarity(searchTerm, product.originalName)
        
        // Additional scoring factors
        
        // Exact normalized match bonus
        if (product.normalizedName === this.normalizeProductName(searchTerm)) {
          similarity += 0.5
        }
        
        // Keyword overlap bonus
        const keywordOverlap = searchKeywords.filter(kw => 
          product.keywords.some(pk => pk.includes(kw) || kw.includes(pk))
        ).length
        similarity += (keywordOverlap / searchKeywords.length) * 0.3
        
        // Fuzzy string matching for typos
        if (similarity < 0.5 && searchTerm.length > 3) {
          const distance = this.levenshteinDistance(this.normalizeProductName(searchTerm), product.normalizedName)
          const maxLength = Math.max(searchTerm.length, product.normalizedName.length)
          const fuzzyScore = 1 - (distance / maxLength)
          if (fuzzyScore > 0.7) {
            similarity = Math.max(similarity, fuzzyScore * 0.8)
          }
        }
        
        // Category matching
        if (product.category) {
          const categoryKeywords = this.extractKeywords(product.category)
          const categoryMatch = searchKeywords.some(kw => 
            categoryKeywords.some(ck => ck.includes(kw) || kw.includes(ck))
          )
          if (categoryMatch) {
            similarity += 0.2
          }
        }
        
        return { ...product, similarity: Math.min(1.0, similarity) }
      })
      .filter(product => product.similarity >= this.similarityThreshold && product.price !== null)
      .sort((a, b) => b.similarity - a.similarity)
    
    // Group by store and find best matches
    return this.groupAndCompareProducts(scoredProducts, searchTerm)
  }

  groupAndCompareProducts(scoredProducts, searchTerm) {
    // Group products by store
    const byStore = scoredProducts.reduce((acc, product) => {
      if (!acc[product.store]) {
        acc[product.store] = []
      }
      acc[product.store].push(product)
      return acc
    }, {})

    const stores = Object.keys(byStore)
    const comparisons = []

    // Create all possible store combinations
    for (let i = 0; i < stores.length; i++) {
      for (let j = i + 1; j < stores.length; j++) {
        const store1 = stores[i]
        const store2 = stores[j]
        
        // Find best matching products between these two stores
        const store1Products = byStore[store1].slice(0, 5) // Top 5 from each store
        const store2Products = byStore[store2].slice(0, 5)
        
        store1Products.forEach(prod1 => {
          store2Products.forEach(prod2 => {
            // Calculate combined similarity score
            const combinedSimilarity = (prod1.similarity + prod2.similarity) / 2
            
            if (combinedSimilarity >= this.similarityThreshold && prod1.price && prod2.price) {
              const priceDiff = Math.abs(prod1.price - prod2.price)
              const saving = Math.max(prod1.price, prod2.price) - Math.min(prod1.price, prod2.price)
              
              comparisons.push({
                product1: {
                  name: prod1.originalName,
                  price: prod1.price,
                  store: store1,
                  similarity: prod1.similarity
                },
                product2: {
                  name: prod2.originalName,
                  price: prod2.price,
                  store: store2,
                  similarity: prod2.similarity
                },
                priceDifference: priceDiff,
                potentialSaving: saving,
                combinedSimilarity: combinedSimilarity,
                cheaperStore: prod1.price < prod2.price ? store1 : store2,
                cheaperPrice: Math.min(prod1.price, prod2.price),
                searchTerm: searchTerm
              })
            }
          })
        })
      }
    }

    // Sort by combined similarity and potential savings
    return comparisons
      .sort((a, b) => {
        // First by similarity
        if (Math.abs(b.combinedSimilarity - a.combinedSimilarity) > 0.1) {
          return b.combinedSimilarity - a.combinedSimilarity
        }
        // Then by potential savings
        return b.potentialSaving - a.potentialSaving
      })
      .slice(0, 10) // Return top 10 comparisons per item
  }

  // New method: Direct product search for single store matching
  findProductsInStore(searchTerm, targetStore, maxResults = 5) {
    const searchKeywords = this.extractKeywords(searchTerm)
    
    const storeProducts = this.allProducts
      .filter(product => product.store === targetStore)
      .map(product => {
        let similarity = this.calculateSimilarity(searchTerm, product.originalName)
        
        // Boost exact keyword matches
        const exactKeywordMatches = searchKeywords.filter(kw => 
          product.keywords.includes(kw)
        ).length
        similarity += (exactKeywordMatches / searchKeywords.length) * 0.4
        
        return { ...product, similarity }
      })
      .filter(product => product.similarity >= 0.3)
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, maxResults)
    
    return storeProducts
  }

  // New method: Find alternatives across all stores
  findBestAlternatives(searchTerm, excludeStore = null) {
    const allMatches = this.allProducts
      .filter(product => !excludeStore || product.store !== excludeStore)
      .map(product => {
        const similarity = this.calculateSimilarity(searchTerm, product.originalName)
        return { ...product, similarity }
      })
      .filter(product => product.similarity >= this.similarityThreshold && product.price !== null)
      .sort((a, b) => {
        // Sort by similarity first, then by price
        if (Math.abs(b.similarity - a.similarity) > 0.1) {
          return b.similarity - a.similarity
        }
        return a.price - b.price
      })
    
    // Group by store and take best from each
    const byStore = {}
    allMatches.forEach(product => {
      if (!byStore[product.store] || byStore[product.store].similarity < product.similarity) {
        byStore[product.store] = product
      }
    })
    
    return Object.values(byStore).slice(0, 4)
  }
}

export default function ResultsPage() {
  const [shoppingList, setShoppingList] = useState([])
  const [selectedSupermarket, setSelectedSupermarket] = useState("")
  const [comparisons, setComparisons] = useState([])
  const [totalSavings, setTotalSavings] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [bestAlternativeStore, setBestAlternativeStore] = useState("")
  const [matchedItemsCount, setMatchedItemsCount] = useState(0)
  const navigate = useNavigate()

  useEffect(() => {
    const loadDataAndCompare = async () => {
      try {
        // Get data from localStorage
        const storedList = JSON.parse(localStorage.getItem("shoppingList") || "[]")
        const storedSupermarket = localStorage.getItem("selectedSupermarket")
        const selectedProducts = JSON.parse(localStorage.getItem("selectedProducts") || "[]")
        
        if (!storedList.length || !storedSupermarket) {
          navigate("/shopping-list")
          return
        }

        setShoppingList(storedList)
        setSelectedSupermarket(storedSupermarket)

        // Initialize Enhanced ProductMatcher
        const matcher = new ProductMatcher()

        // Updated supermarkets list to include ASDA
        const supermarkets = [
          { name: "ALDI", file: "/aldi.csv" },
          { name: "Tesco", file: "/tesco.csv" },
          { name: "Sainsbury's", file: "/sainsburys.csv" },
          { name: "Morrisons", file: "/morrisons.csv" },
          { name: "ASDA", file: "/asda.csv" }
        ]

        console.log("Loading product data from all supermarkets...")

        // Load all CSV files
        for (const supermarket of supermarkets) {
          try {
            console.log(`Loading ${supermarket.name}...`)
            const response = await fetch(supermarket.file)
            if (response.ok) {
              const csvText = await response.text()
              matcher.loadProductsFromCSV(csvText, supermarket.name)
              console.log(`✓ Loaded ${supermarket.name} products`)
            } else {
              console.warn(`Failed to load ${supermarket.name}: ${response.status}`)
            }
          } catch (error) {
            console.warn(`Failed to load ${supermarket.name} data:`, error)
          }
        }

        console.log(`Total products loaded: ${matcher.allProducts.length}`)

        // Enhanced comparison logic using SELECTED products
        const allComparisons = []
        let totalPotentialSavings = 0
        const storeSavings = {}
        let matchedItems = 0

        for (let i = 0; i < storedList.length; i++) {
          const item = storedList[i]
          const selectedProduct = selectedProducts[i] // Get the specific product the user selected
          
          console.log(`\nAnalyzing item ${i + 1}: "${item}"`)
          
          // Extract just the product name (remove price if present)
          const productName = item.includes(' - £') ? item.split(' - £')[0] : item

          let currentStoreProduct = null
          let results = []

          // If user selected a specific product, use that as the base
          if (selectedProduct && selectedProduct.name && selectedProduct.price) {
            console.log(`Using selected product: ${selectedProduct.name} from ${selectedProduct.store}`)
            
            currentStoreProduct = {
              name: selectedProduct.name,
              price: parseFloat(selectedProduct.price),
              store: storedSupermarket,
              category: selectedProduct.category
            }

            // Find similar products in OTHER stores (excluding the selected supermarket)
            const otherStoreProducts = matcher.allProducts
              .filter(product => product.store !== storedSupermarket)
              .map(product => {
                const similarity = matcher.calculateSimilarity(productName, product.originalName)
                return { ...product, similarity }
              })
              .filter(product => product.similarity >= 0.3 && product.price !== null)
              .sort((a, b) => b.similarity - a.similarity)

            // Group by store and take best match from each store
            const byStore = {}
            otherStoreProducts.forEach(product => {
              if (!byStore[product.store] || byStore[product.store].similarity < product.similarity) {
                byStore[product.store] = product
              }
            })

            // Create comparisons with the selected product
            results = Object.values(byStore)
              .slice(0, 4) // Top 4 alternative stores
              .map(altProduct => ({
                product1: {
                  name: currentStoreProduct.name,
                  price: currentStoreProduct.price,
                  store: currentStoreProduct.store,
                  similarity: 1.0 // User selected this, so it's a perfect match
                },
                product2: {
                  name: altProduct.originalName,
                  price: altProduct.price,
                  store: altProduct.store,
                  similarity: altProduct.similarity
                },
                priceDifference: Math.abs(currentStoreProduct.price - altProduct.price),
                potentialSaving: Math.max(0, currentStoreProduct.price - altProduct.price),
                combinedSimilarity: (1.0 + altProduct.similarity) / 2,
                cheaperStore: currentStoreProduct.price < altProduct.price ? currentStoreProduct.store : altProduct.store,
                cheaperPrice: Math.min(currentStoreProduct.price, altProduct.price),
                searchTerm: productName
              }))
              .filter(comparison => comparison.potentialSaving >= 0) // Include all comparisons, even if no savings
              .sort((a, b) => b.potentialSaving - a.potentialSaving)

          } else {
            // Fallback: If no specific product was selected, use the old logic
            console.log(`No specific product selected for "${productName}", using search logic`)
            
            // Find the best product in the selected supermarket first
            const currentStoreMatches = matcher.findProductsInStore(productName, storedSupermarket, 1)
            
            if (currentStoreMatches.length > 0) {
              currentStoreProduct = currentStoreMatches[0]
              
              // Find alternatives in other stores
              const alternatives = matcher.findBestAlternatives(productName, storedSupermarket)
              
              results = alternatives.map(alt => ({
                product1: {
                  name: currentStoreProduct.originalName,
                  price: currentStoreProduct.price,
                  store: storedSupermarket,
                  similarity: currentStoreProduct.similarity
                },
                product2: {
                  name: alt.originalName,
                  price: alt.price,
                  store: alt.store,
                  similarity: alt.similarity
                },
                priceDifference: Math.abs(currentStoreProduct.price - alt.price),
                potentialSaving: Math.max(0, currentStoreProduct.price - alt.price),
                combinedSimilarity: (currentStoreProduct.similarity + alt.similarity) / 2,
                cheaperStore: currentStoreProduct.price < alt.price ? storedSupermarket : alt.store,
                cheaperPrice: Math.min(currentStoreProduct.price, alt.price),
                searchTerm: productName
              }))
            }
          }
          
          console.log(`Found ${results.length} comparisons for "${productName}"`)
          
          if (results.length > 0) {
            matchedItems++
            
            // Find the best savings for this item
            const bestSaving = results.reduce((best, current) => {
              return (current.potentialSaving || 0) > (best.potentialSaving || 0) ? current : best
            }, results[0])

            allComparisons.push({
              searchTerm: productName,
              originalItem: item,
              selectedProduct: currentStoreProduct, // Store the base product for display
              comparisons: results.slice(0, 5), // Show top 5 comparisons
              bestSaving: bestSaving,
              matchQuality: results[0]?.combinedSimilarity || 0
            })

            const savingsAmount = bestSaving.potentialSaving || 0
            totalPotentialSavings += savingsAmount

            // Track savings by store
            if (savingsAmount > 0 && bestSaving.cheaperStore && bestSaving.cheaperStore !== storedSupermarket) {
              if (!storeSavings[bestSaving.cheaperStore]) {
                storeSavings[bestSaving.cheaperStore] = 0
              }
              storeSavings[bestSaving.cheaperStore] += savingsAmount
            }
          } else {
            console.log(`No matches found for "${productName}"`)
            // Still add to comparisons but with no matches
            allComparisons.push({
              searchTerm: productName,
              originalItem: item,
              selectedProduct: currentStoreProduct,
              comparisons: [],
              bestSaving: null,
              matchQuality: 0
            })
          }
        }

        // Find the store with the most total savings
        const bestStore = Object.keys(storeSavings).length > 0 
          ? Object.keys(storeSavings).reduce((a, b) => 
              storeSavings[a] > storeSavings[b] ? a : b
            )
          : ""

        console.log(`\nComparison Summary:`)
        console.log(`- Selected supermarket: ${storedSupermarket}`)
        console.log(`- Items processed: ${storedList.length}`)
        console.log(`- Items matched: ${matchedItems}`)
        console.log(`- Total potential savings: £${totalPotentialSavings.toFixed(2)}`)
        console.log(`- Best alternative store: ${bestStore}`)
        console.log(`- Store savings breakdown:`, storeSavings)

        setComparisons(allComparisons)
        setTotalSavings(totalPotentialSavings)
        setBestAlternativeStore(bestStore)
        setMatchedItemsCount(matchedItems)

      } catch (error) {
        console.error("Error loading comparison data:", error)
      } finally {
        setIsLoading(false)
      }
    }

    loadDataAndCompare()
  }, [navigate])

  if (isLoading) {
    return (
      <div className="page-container">
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
        <div className="loading-container">
          <div className="loading-content">
            <h2>Comparing prices across supermarkets...</h2>
            <p>This may take a moment while we analyze your shopping list.</p>
            <div className="loading-progress">
              <div className="loading-bar"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

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

      {/* Results Content */}
      <section className="results-section">
        <div className="container">
          <div className="results-content">
            <div className="progress-bar">
              <div className="progress-step completed">1</div>
              <div className="progress-line completed"></div>
              <div className="progress-step completed">2</div>
              <div className="progress-line completed"></div>
              <div className="progress-step active">3</div>
            </div>

            <h1 className="results-title">Your Price Comparison Results</h1>
            <p className="results-description">
              We've compared your shopping list across major supermarkets to find you the best deals.
            </p>

            {/* Summary Cards */}
            <div className="summary-cards">
              <div className="summary-card savings-card">
                <div className="card-icon">
                  <TrendingDown size={24} />
                </div>
                <div className="card-content">
                  <h3>Potential Savings</h3>
                  <p className="savings-amount">£{totalSavings.toFixed(2)}</p>
                  <span className="savings-subtitle">vs {selectedSupermarket}</span>
                </div>
              </div>

              <div className="summary-card store-card">
                <div className="card-icon">
                  <Store size={24} />
                </div>
                <div className="card-content">
                  <h3>Best Alternative</h3>
                  <p className="store-name">{bestAlternativeStore || "No better option found"}</p>
                  <span className="store-subtitle">
                    {bestAlternativeStore ? "Offers the most savings" : "Current store is competitive"}
                  </span>
                </div>
              </div>

              <div className="summary-card items-card">
                <div className="card-icon">
                  <Search size={24} />
                </div>
                <div className="card-content">
                  <h3>Items Matched</h3>
                  <p className="items-count">{matchedItemsCount}</p>
                  <span className="items-subtitle">out of {shoppingList.length} items</span>
                </div>
              </div>
            </div>

            {/* Detailed Comparisons */}
            <div className="comparisons-container">
              <h2 className="comparisons-title">Item-by-Item Comparison</h2>
              
              {comparisons.map((item, index) => (
                <div key={index} className="comparison-card">
                  <div className="comparison-header">
                    <h3 className="item-name">{item.searchTerm}</h3>
                    <div className="match-info">
                      {item.matchQuality > 0 && (
                        <span className="match-quality">
                          {Math.round(item.matchQuality * 100)}% match
                        </span>
                      )}
                      {item.bestSaving?.potentialSaving > 0 && (
                        <div className="savings-badge">
                          Save £{item.bestSaving.potentialSaving.toFixed(2)}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {item.comparisons.length > 0 ? (
                    <div className="comparison-details">
                      {item.comparisons.slice(0, 3).map((comparison, compIndex) => (
                        <div key={compIndex} className="price-comparison">
                          <div className="store-comparison">
                            <div className="store-item">
                              <span className="store-name">{comparison.product1.store}</span>
                              <span className="product-name">{comparison.product1.name}</span>
                              <span className="price">£{comparison.product1.price.toFixed(2)}</span>
                            </div>
                            <div className="vs-divider">vs</div>
                            <div className="store-item">
                              <span className="store-name">{comparison.product2.store}</span>
                              <span className="product-name">{comparison.product2.name}</span>
                              <span className="price">£{comparison.product2.price.toFixed(2)}</span>
                            </div>
                          </div>
                          {comparison.potentialSaving > 0 && (
                            <div className="saving-highlight">
                              <span className="cheaper-store">{comparison.cheaperStore}</span> is cheaper by 
                              <span className="saving-amount"> £{comparison.potentialSaving.toFixed(2)}</span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="no-matches">
                      <p>No similar products found across other supermarkets.</p>
                      <span className="no-matches-subtitle">
                        Try searching with a more generic term or check the spelling.
                      </span>
                    </div>
                  )}
                </div>
              ))}
              
              {comparisons.length === 0 && (
                <div className="no-results">
                  <h3>No comparisons available</h3>
                  <p>We couldn't find matching products for your shopping list items. This might be because:</p>
                  <ul>
                    <li>The product names are too specific or contain typos</li>
                    <li>The products are not available in our database</li>
                    <li>Try using more generic terms (e.g., "milk" instead of "Organic Semi-Skimmed Milk 2L")</li>
                  </ul>
                </div>
              )}
            </div>

            {/* Enhanced Insights */}
            {totalSavings > 0 && (
              <div 
                className="insights-container" 
                data-high-savings={totalSavings > 10 ? "true" : "false"}
              >
                <h2 className="insights-title">💡 Shopping Insights</h2>
                <div className="insights-grid">
                  <div className="insight-card">
                    <h4>📅 Monthly Savings Potential</h4>
                    <p className="insight-value">£{(totalSavings * 4).toFixed(2)}</p>
                    <span className="insight-subtitle">If you shop weekly</span>
                  </div>
                  <div className="insight-card">
                    <h4>📅 Annual Savings Potential</h4>
                    <p className="insight-value">£{(totalSavings * 52).toFixed(2)}</p>
                    <span className="insight-subtitle">If you shop weekly</span>
                  </div>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="action-buttons">
              <Link to="/shopping-list" className="back-button">
                <ArrowLeft className="button-icon" />
                Edit Shopping List
              </Link>
              
              <button 
                onClick={() => {
                  // Clear localStorage and start fresh
                  localStorage.removeItem("shoppingList")
                  localStorage.removeItem("selectedSupermarket")
                  localStorage.removeItem("selectedProducts")
                  navigate("/")
                }}
                className="continue-button"
              >
                Start New Comparison
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}