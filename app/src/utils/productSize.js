// Size / quantity parsing so we compare like-for-like across stores.
//
// The matcher used to strip sizes out of product names, which made "Cola 2L"
// and "Cola 1L" look identical and then compared their raw prices — so a bigger
// bottle would wrongly show as "cheaper". These helpers extract the size, group
// it into a unit family (weight / volume / count), and expose a price-per-unit
// so comparisons are done on equal quantities.

// Base units per family: weight -> grams, volume -> millilitres, count -> each.
const CL_TO_ML = 10
const L_TO_ML = 1000
const PINT_TO_ML = 568 // UK pint
const KG_TO_G = 1000

// Order matters: try the most specific patterns (multipacks) first.
const MULTIPACK = /(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(kg|g|l|ltr|litre|litres|ml|cl)\b/i
const WEIGHT = /(\d+(?:\.\d+)?)\s*(kg|g)\b/i
const VOLUME = /(\d+(?:\.\d+)?)\s*(l|ltr|litre|litres|ml|cl|pints?|pt)\b/i
const COUNT =
  /(\d+)\s*(pack|pk|pieces?|count|ct|rolls?|sheets?|bags?|capsules?|tablets?|tabs?|wipes|sachets?|cans?|eggs)\b/i
const TRAILING_X = /[x×]\s*(\d+)\b/i // e.g. "Eggs x6"

function weightToGrams(value, unit) {
  return unit.toLowerCase() === "kg" ? value * KG_TO_G : value
}

function volumeToMl(value, unit) {
  const u = unit.toLowerCase()
  if (u === "ml") return value
  if (u === "cl") return value * CL_TO_ML
  if (u.startsWith("pint") || u === "pt") return value * PINT_TO_ML
  return value * L_TO_ML // l / ltr / litre(s)
}

// Parse a size out of a product name.
// Returns { family, magnitude, display } in base units, or null if none found.
export function parseSize(name) {
  if (!name) return null
  const text = String(name)

  let m = text.match(MULTIPACK)
  if (m) {
    const count = parseFloat(m[1])
    const each = parseFloat(m[2])
    const unit = m[3]
    const isVolume = /^(l|ltr|litre|litres|ml|cl)$/i.test(unit)
    const family = isVolume ? "volume" : "weight"
    const perUnit = isVolume ? volumeToMl(each, unit) : weightToGrams(each, unit)
    return {
      family,
      magnitude: count * perUnit,
      display: `${count} x ${each}${unit.toLowerCase()}`,
    }
  }

  m = text.match(WEIGHT)
  if (m) {
    const value = parseFloat(m[1])
    return {
      family: "weight",
      magnitude: weightToGrams(value, m[2]),
      display: `${m[1]}${m[2].toLowerCase()}`,
    }
  }

  m = text.match(VOLUME)
  if (m) {
    const value = parseFloat(m[1])
    return {
      family: "volume",
      magnitude: volumeToMl(value, m[2]),
      display: `${m[1]}${m[2].toLowerCase()}`,
    }
  }

  m = text.match(COUNT) || text.match(TRAILING_X)
  if (m) {
    const count = parseFloat(m[1])
    if (count > 0) {
      return { family: "count", magnitude: count, display: `${count} pack` }
    }
  }

  return null
}

export function sizesComparable(a, b) {
  return !!a && !!b && a.family === b.family && a.magnitude > 0 && b.magnitude > 0
}

// Price per base unit (per gram / per ml / per item).
export function unitPrice(price, size) {
  if (price == null || !size || !size.magnitude) return null
  return price / size.magnitude
}

// Human-friendly per-unit price, e.g. "£1.20/L", "£0.45/100g", "£0.33 each".
export function formatUnitPrice(price, size) {
  const up = unitPrice(price, size)
  if (up == null) return null
  if (size.family === "volume") return `£${(up * L_TO_ML).toFixed(2)}/L`
  if (size.family === "weight") return `£${(up * 100).toFixed(2)}/100g`
  return `£${up.toFixed(2)} each`
}
