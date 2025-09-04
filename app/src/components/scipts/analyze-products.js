// Let's analyze the ALDI products data
const fs = require("fs")
const path = require("path")

// Read the CSV file
const csvData = fs.readFileSync(path.join(__dirname, "../public/aldi_products.csv"), "utf8")

// Parse CSV data
const lines = csvData.split("\n")
const headers = lines[0].split(",")
const products = []

for (let i = 1; i < Math.min(lines.length, 100); i++) {
  // Sample first 100 products
  const values = lines[i].split(",")
  if (values.length >= headers.length) {
    const product = {}
    headers.forEach((header, index) => {
      product[header.replace(/"/g, "")] = values[index]?.replace(/"/g, "") || ""
    })
    products.push(product)
  }
}

console.log("Sample products:")
console.log(products.slice(0, 10))

console.log("\nProduct categories:")
const categories = [...new Set(products.map((p) => p.category))]
console.log(categories)

console.log("\nCommon product names:")
const names = products.map((p) => p.name).slice(0, 20)
console.log(names)
