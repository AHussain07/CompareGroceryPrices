"use client"

import { ShoppingCart, ArrowRight, ArrowLeft } from "lucide-react"
import { Link } from "react-router-dom"
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import "./style.css"

export default function SelectSupermarketPage() {
  const [selectedSupermarket, setSelectedSupermarket] = useState("")
  const navigate = useNavigate()

  const supermarkets = [
    "Aldi",
    "Asda",
    "Morrisons",
    "Sainsbury's",
    "Tesco",
  ]

  const handleContinue = () => {
    if (selectedSupermarket) {
      // Store supermarket name in correct case
      localStorage.setItem("selectedSupermarket", selectedSupermarket.toUpperCase())
      navigate("/shopping-list")
    }
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

      {/* Main Content */}
      <section className="select-supermarket-section">
        <div className="container">
          <div className="select-content">
            <div className="progress-bar">
              <div className="progress-step active">1</div>
              <div className="progress-line"></div>
              <div className="progress-step">2</div>
              <div className="progress-line"></div>
              <div className="progress-step">3</div>
            </div>

            <h1 className="select-title">Where do you currently shop for groceries?</h1>
            <p className="select-description">
              Select your primary supermarket so we can show you how much you could save by switching.
            </p>

            <div className="supermarket-selection">
              <select
                value={selectedSupermarket}
                onChange={(e) => setSelectedSupermarket(e.target.value)}
                className="supermarket-dropdown"
              >
                <option value="">Choose your supermarket...</option>
                {supermarkets.map((market) => (
                  <option key={market} value={market}>
                    {market}
                  </option>
                ))}
              </select>
            </div>

            <div className="action-buttons">
              <Link to="/" className="back-button">
                <ArrowLeft className="button-icon" />
                Back to Home
              </Link>

              <button
                onClick={handleContinue}
                disabled={!selectedSupermarket}
                className={`continue-button ${!selectedSupermarket ? "disabled" : ""}`}
              >
                Continue
                <ArrowRight className="button-icon" />
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
