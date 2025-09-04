// Utility function to parse CSV data
export const parseCSV = (csvText) => {
    const lines = csvText.trim().split("\n")
    const headers = lines[0].split(",").map((header) => header.replace(/"/g, "").trim())
    const products = []
  
    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(",")
      if (values.length >= headers.length) {
        const product = {}
        headers.forEach((header, index) => {
          product[header] = values[index]?.replace(/"/g, "").trim() || ""
        })
        products.push(product)
      }
    }
  
    return products
  }
  
  // Function to extract unique product names and clean them
  export const extractProductNames = (products) => {
    const productNames = products
      .map((product) => product.name)
      .filter((name) => name && name.length > 0)
      .map((name) => {
        // Clean up product names - remove extra descriptors, sizes, etc.
        return name
          .replace(/\d+g|\d+ml|\d+kg|\d+l/gi, "") // Remove weights/volumes
          .replace(/pack of \d+/gi, "") // Remove pack sizes
          .replace(/\s+/g, " ") // Replace multiple spaces with single space
          .trim()
      })
      .filter((name) => name.length > 2) // Filter out very short names
  
    // Remove duplicates and sort
    return [...new Set(productNames)].sort()
  }
  
  // Function to load and parse ALDI products
  export const loadAldiProducts = async () => {
    try {
      const response = await fetch("/aldi_products.csv")
      const csvText = await response.text()
      const products = parseCSV(csvText)
      const productNames = extractProductNames(products)
  
      console.log(`Loaded ${productNames.length} unique products from ALDI`)
      return { products, productNames }
    } catch (error) {
      console.error("Error loading ALDI products:", error)
      // Fallback to basic suggestions if CSV fails to load
      return {
        products: [],
        productNames: [
          "Milk",
          "Bread",
          "Eggs",
          "Butter",
          "Cheese",
          "Chicken Breast",
          "Bananas",
          "Apples",
          "Potatoes",
          "Onions",
          "Tomatoes",
          "Rice",
          "Pasta",
          "Yogurt",
          "Bacon",
          "Salmon",
          "Carrots",
          "Broccoli",
        ],
      }
    }
  }
  