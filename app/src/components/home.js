import { ShoppingCart, TrendingDown, ArrowRight, MessageCircle } from "lucide-react"
import { Link } from "react-router-dom"
import "./style.css"

const tescoLogo = process.env.PUBLIC_URL + "/Tesco_logo.png"
const asdaLogo = process.env.PUBLIC_URL + "/asda.png"
const morrisonsLogo = process.env.PUBLIC_URL + "/Morrisons-logo.png"
const sainsburysLogo = process.env.PUBLIC_URL + "/Sainsbury's_Logo.svg.png"
const aldiLogo = process.env.PUBLIC_URL + "/aldi-logo.png" // Changed from "/images.png" to "/aldi-logo.png"

export default function HomePage() {
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
            <nav className="header-nav">
              <Link to="/contact" className="contact-button">
                <MessageCircle className="contact-icon" />
                Contact Us
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero">
        <div className="container">
          <div className="hero-content">
            <div className="badge">
              <TrendingDown className="badge-icon" />
              Save up to 40% on groceries
            </div>

            <h1 className="hero-title">
              Find the{" "}
              <span className="hero-highlight">
                Cheapest Place
                <svg className="hero-underline" viewBox="0 0 100 12" fill="currentColor">
                  <path d="M0 8c30-4 70-4 100 0v4H0z" />
                </svg>
              </span>
              <br />
              to Buy Your Shopping List
            </h1>

            <p className="hero-description">
              Enter your grocery list, and we'll tell you which supermarket saves you the most money. Compare prices
              across all major stores instantly.
            </p>

            {/* CTA Section */}
            <div className="cta-container">
              <Link to="/select-supermarket" className="cta-button">
                Get Started
                <ArrowRight className="cta-icon" />
              </Link>
              <p className="cta-subtext">Free to use • No signup required • Compare 5+ stores</p>
            </div>

            {/* Social Proof */}
            {/* <div className="social-proof">
              <div className="proof-item">
                <Users className="proof-icon" />
                <span className="proof-text">50,000+ families saving money</span>
              </div>
              <div className="proof-item">
                <Star className="proof-icon star-filled" />
                <span className="proof-text">4.8/5 rating</span>
              </div>
              <div className="proof-item">
                <DollarSign className="proof-icon" />
                <span className="proof-text">Average savings: $127/month</span>
              </div>
            </div> */}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="how-it-works">
        <div className="container">
          <div className="section-header">
            <h2 className="section-title">How It Works</h2>
            <p className="section-description">Save money on groceries in three simple steps</p>
          </div>

          <div className="steps-grid">
            <div className="step-card">
              <div className="step-number step-1">1</div>
              <h3 className="step-title">Enter Your List</h3>
              <p className="step-description">Type in the groceries you need or upload a photo of your shopping list</p>
            </div>

            <div className="step-card">
              <div className="step-number step-2">2</div>
              <h3 className="step-title">We Compare Prices</h3>
              <p className="step-description">Our system checks prices across all major supermarkets</p>
            </div>

            <div className="step-card">
              <div className="step-number step-3">3</div>
              <h3 className="step-title">Save Money</h3>
              <p className="step-description">Get a detailed breakdown showing where to shop for maximum savings</p>
            </div>
          </div>
        </div>
      </section>

      {/* Supermarkets Section */}
      <section id="supermarkets" className="supermarkets">
        <div className="container">
          <div className="row">
            <h1 className="section__title">
              Compare prices across <span className="text--blue">major supermarkets</span>
            </h1>
            <div className="supermarket__list">
              <div className="supermarket">
                <figure className="supermarket__img--wrapper">
                  <img
                    src={tescoLogo || "/placeholder.svg?height=100&width=100&query=Tesco logo"}
                    alt="Tesco Logo"
                    className="supermarket__img"
                  />
                </figure>
                <span className="supermarket__name">Tesco</span>
              </div>
              <div className="supermarket">
                <figure className="supermarket__img--wrapper">
                  <img
                    src={asdaLogo || "/placeholder.svg?height=100&width=100&query=ASDA logo"}
                    alt="ASDA Logo"
                    className="supermarket__img"
                  />
                </figure>
                <span className="supermarket__name">ASDA</span>
              </div>
              <div className="supermarket">
                <figure className="supermarket__img--wrapper">
                  <img
                    src={morrisonsLogo || "/placeholder.svg?height=100&width=100&query=Morrisons logo"}
                    alt="Morrisons Logo"
                    className="supermarket__img"
                  />
                </figure>
                <span className="supermarket__name">Morrisons</span>
              </div>
              <div className="supermarket">
                <figure className="supermarket__img--wrapper">
                  <img
                    src={sainsburysLogo || "/placeholder.svg?height=100&width=100&query=Sainsburys logo"}
                    alt="Sainsbury's Logo"
                    className="supermarket__img"
                  />
                </figure>
                <span className="supermarket__name">Sainsbury's</span>
              </div>
              <div className="supermarket">
                <figure className="supermarket__img--wrapper">
                  <img
                    src={aldiLogo || "/aldi-logo.png"}
                    alt="Aldi Logo"
                    className="supermarket__img"
                  />
                </figure>
                <span className="supermarket__name">Aldi</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="container">
          <div className="footer-content">
            <Link to="/" className="footer-logo">
              <ShoppingCart className="footer-logo-icon" />
              <span className="footer-logo-text">CompareGroceryPrices</span>
            </Link>
            <div className="footer-links">
              <Link to="/privacy" className="footer-link">Privacy Policy</Link>
              <Link to="/terms" className="footer-link">Terms of Service</Link>
              <Link to="/contact" className="footer-link">Contact Us</Link>
            </div>
          </div>
          <div className="footer-bottom">
            <p>&copy; 2024 CompareGroceryPrices. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
