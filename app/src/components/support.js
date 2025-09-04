import { useState, useEffect } from "react"
import { ShoppingCart, ArrowLeft, Send, MessageSquare, Bug, Lightbulb, CheckCircle, AlertCircle } from 'lucide-react'
import { Link, useLocation, useNavigate } from "react-router-dom"
import emailjs from '@emailjs/browser'
import './style.css'

export default function ContactPage() {
  const location = useLocation()
  const navigate = useNavigate()
  
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    category: '',
    subject: '',
    message: '',
    honeypot: '' // Add honeypot field for bot detection
  })
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errors, setErrors] = useState({})
  const [submitError, setSubmitError] = useState('')
  const [isMobile, setIsMobile] = useState(false)

  // Determine return path based on URL params
  const urlParams = new URLSearchParams(location.search)
  const category = urlParams.get('category')
  const returnPath = category === 'missing-item' ? '/shopping-list' : '/'

  // Check for pre-selected category from URL params
  useEffect(() => {
    if (category === 'missing-item') {
      setFormData(prev => ({
        ...prev,
        category: 'missing-item',
        subject: 'Missing Product Report',
        message: 'Hi, I was unable to find the following product(s) in your database:\n\nProduct name: \nBrand: \nStore where I usually buy it: \n\nAdditional details: '
      }))
    }
  }, [category])

  // Email validation function
  const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  // Rate limiting function
  const checkRateLimit = () => {
    const now = Date.now()
    const COOLDOWN_PERIOD = (process.env.REACT_APP_COOLDOWN_PERIOD || 5) * 60 * 1000 // Default 5 minutes
    const MAX_SUBMISSIONS_PER_HOUR = parseInt(process.env.REACT_APP_MAX_SUBMISSIONS_PER_HOUR) || 3
    
    // Get rate limiting data from localStorage
    const rateLimitData = JSON.parse(localStorage.getItem('emailRateLimit') || '{}')
    const lastSubmission = rateLimitData.lastSubmission || 0
    const hourlyCount = rateLimitData.hourlyCount || 0
    const hourStart = rateLimitData.hourStart || now
    
    // Check if it's been less than 5 minutes since last submission
    if (now - lastSubmission < COOLDOWN_PERIOD) {
      const remainingTime = Math.ceil((COOLDOWN_PERIOD - (now - lastSubmission)) / 1000 / 60)
      return {
        allowed: false,
        message: `Please wait ${remainingTime} minutes before sending another message.`
      }
    }
    
    // Check hourly limit (reset counter if it's been more than an hour)
    const isNewHour = now - hourStart > 60 * 60 * 1000
    const currentHourlyCount = isNewHour ? 0 : hourlyCount
    
    if (currentHourlyCount >= MAX_SUBMISSIONS_PER_HOUR) {
      return {
        allowed: false,
        message: `You've reached the maximum of ${MAX_SUBMISSIONS_PER_HOUR} messages per hour. Please try again later.`
      }
    }
    
    // Update rate limiting data
    localStorage.setItem('emailRateLimit', JSON.stringify({
      lastSubmission: now,
      hourlyCount: currentHourlyCount + 1,
      hourStart: isNewHour ? now : hourStart
    }))
    
    return { allowed: true }
  }

  // Daily limit function
  const checkDailyLimit = () => {
    const today = new Date().toDateString()
    const dailyData = JSON.parse(localStorage.getItem('dailyEmailUsage') || '{}')
    
    if (dailyData.date !== today) {
      // Reset daily count for new day
      dailyData.date = today
      dailyData.count = 0
    }
    
    const DAILY_LIMIT = parseInt(process.env.REACT_APP_DAILY_LIMIT) || 10 // Set reasonable daily limit per user
    
    if (dailyData.count >= DAILY_LIMIT) {
      return {
        allowed: false,
        message: 'Daily message limit reached. Please try again tomorrow.'
      }
    }
    
    // Increment count
    dailyData.count += 1
    localStorage.setItem('dailyEmailUsage', JSON.stringify(dailyData))
    
    return { allowed: true }
  }

  // Spam detection function
  const detectSpamContent = (formData) => {
    // Common spam indicators
    const spamKeywords = [
      'viagra', 'casino', 'lottery', 'winner', 'congratulations',
      'click here', 'free money', 'act now', 'limited time',
      'make money fast', 'work from home', 'bitcoin', 'crypto',
      'investment opportunity', 'guaranteed', 'no risk', 'urgent',
      'million dollars', 'inheritance', 'prince', 'bank transfer'
    ]
    
    const suspiciousPatterns = [
      /(.)\1{5,}/g, // Repeated characters (aaaaa)
      /https?:\/\/[^\s]+/gi, // Multiple URLs
      /@[^\s]+\.[^\s]+/g, // Multiple email addresses
      /\$\d+/g, // Dollar amounts
      /\d{10,}/g // Long numbers (phone numbers, etc.)
    ]
    
    const text = `${formData.name} ${formData.email} ${formData.subject} ${formData.message}`.toLowerCase()
    
    // Check for spam keywords
    const foundSpamWords = spamKeywords.filter(keyword => text.includes(keyword))
    if (foundSpamWords.length > 0) {
      return {
        isSpam: true,
        reason: `Suspicious content detected: ${foundSpamWords.join(', ')}`
      }
    }
    
    // Check for suspicious patterns
    for (const pattern of suspiciousPatterns) {
      const matches = text.match(pattern)
      if (matches && matches.length > 2) {
        return {
          isSpam: true,
          reason: 'Suspicious content patterns detected'
        }
      }
    }
    
    // Check for very short or very long messages
    if (formData.message.trim().length < 10) {
      return {
        isSpam: true,
        reason: 'Message too short'
      }
    }
    
    if (formData.message.length > 2000) {
      return {
        isSpam: true,
        reason: 'Message too long'
      }
    }

    // Check for excessive URLs
    const urlMatches = text.match(/https?:\/\/[^\s]+/gi)
    if (urlMatches && urlMatches.length > 1) {
      return {
        isSpam: true,
        reason: 'Too many URLs detected'
      }
    }
    
    return { isSpam: false }
  }

  // Enhanced form validation with real-time checking
  const validateForm = () => {
    const newErrors = {}

    // Name validation
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required'
    } else if (formData.name.trim().length < 2) {
      newErrors.name = 'Name must be at least 2 characters'
    } else if (formData.name.trim().length > 50) {
      newErrors.name = 'Name must be less than 50 characters'
    } else if (!/^[a-zA-Z\s'-]+$/.test(formData.name.trim())) {
      newErrors.name = 'Name can only contain letters, spaces, hyphens, and apostrophes'
    }

    // Email validation
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required'
    } else if (!validateEmail(formData.email)) {
      newErrors.email = 'Please enter a valid email address'
    }

    // Category validation
    if (!formData.category) {
      newErrors.category = 'Please select a category'
    }

    // Subject validation - allow empty but check max length
    if (formData.subject.trim().length > 100) {
      newErrors.subject = 'Subject must be less than 100 characters'
    }

    // Message validation
    if (!formData.message.trim()) {
      newErrors.message = 'Message is required'
    } else if (formData.message.trim().length < 10) {
      newErrors.message = 'Message must be at least 10 characters'
    } else if (formData.message.length > 1000) {
      newErrors.message = 'Message must be less than 1000 characters'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // Real-time validation when fields change
  const validateField = (fieldName, value) => {
    const fieldErrors = { ...errors }

    switch (fieldName) {
      case 'name':
        if (!value.trim()) {
          fieldErrors.name = 'Name is required'
        } else if (value.trim().length < 2) {
          fieldErrors.name = 'Name must be at least 2 characters'
        } else if (value.trim().length > 50) {
          fieldErrors.name = 'Name must be less than 50 characters'
        } else if (!/^[a-zA-Z\s'-]+$/.test(value.trim())) {
          fieldErrors.name = 'Name can only contain letters, spaces, hyphens, and apostrophes'
        } else {
          delete fieldErrors.name
        }
        break

      case 'email':
        if (!value.trim()) {
          fieldErrors.email = 'Email is required'
        } else if (!validateEmail(value)) {
          fieldErrors.email = 'Please enter a valid email address'
        } else {
          delete fieldErrors.email
        }
        break

      case 'category':
        if (!value) {
          fieldErrors.category = 'Please select a category'
        } else {
          delete fieldErrors.category
        }
        break

      case 'subject':
        // Only check maximum length, allow empty
        if (value.trim().length > 100) {
          fieldErrors.subject = 'Subject must be less than 100 characters'
        } else {
          delete fieldErrors.subject
        }
        break

      case 'message':
        if (!value.trim()) {
          fieldErrors.message = 'Message is required'
        } else if (value.trim().length < 10) {
          fieldErrors.message = 'Message must be at least 10 characters'
        } else if (value.length > 1000) {
          fieldErrors.message = 'Message must be less than 1000 characters'
        } else {
          delete fieldErrors.message
        }
        break

      case 'honeypot':
        // Don't show any validation for honeypot
        break

      default:
        break
    }

    setErrors(fieldErrors)
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))

    // Always validate the current field being changed (except honeypot)
    if (name !== 'honeypot') {
      validateField(name, value)
    }

    // Clear submit error when user makes changes
    if (submitError) {
      setSubmitError('')
    }
  }

  const sendEmail = async (formData) => {
    try {
      // Log submission attempt for monitoring
      console.log('Email submission:', {
        timestamp: new Date().toISOString(),
        category: formData.category,
        messageLength: formData.message.length,
        userAgent: navigator.userAgent.substring(0, 100) // Truncate for privacy
      })

      // EmailJS configuration - using environment variables
      const serviceID = process.env.REACT_APP_EMAILJS_SERVICE_ID
      const templateID = process.env.REACT_APP_EMAILJS_TEMPLATE_ID
      const publicKey = process.env.REACT_APP_EMAILJS_PUBLIC_KEY
      const supportEmail = process.env.REACT_APP_SUPPORT_EMAIL

      // Validate that environment variables are loaded
      if (!serviceID || !templateID || !publicKey) {
        throw new Error('EmailJS configuration is missing. Please check environment variables.')
      }

      const templateParams = {
        from_name: formData.name,
        from_email: formData.email,
        to_email: supportEmail,
        category: formData.category,
        subject: formData.subject,
        message: formData.message,
        timestamp: new Date().toLocaleString(),
        reply_to: formData.email
      }

      const response = await emailjs.send(
        serviceID,
        templateID,
        templateParams,
        publicKey
      )

      if (response.status === 200) {
        return { success: true }
      } else {
        throw new Error('EmailJS failed to send')
      }
    } catch (error) {
      console.error('Email sending failed:', error)
      return { success: false, error: error.message }
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitError('')

    // Check honeypot (if filled, it's likely a bot)
    if (formData.honeypot) {
      console.log('Bot detected via honeypot')
      return // Silently fail for bots
    }

    // Check rate limiting
    const rateCheck = checkRateLimit()
    if (!rateCheck.allowed) {
      setSubmitError(rateCheck.message)
      return
    }

    // Check daily limit
    const dailyCheck = checkDailyLimit()
    if (!dailyCheck.allowed) {
      setSubmitError(dailyCheck.message)
      return
    }

    // Check for spam content
    const spamCheck = detectSpamContent(formData)
    if (spamCheck.isSpam) {
      setSubmitError('Your message was flagged as spam. Please review your content and try again.')
      console.log('Spam detected:', spamCheck.reason)
      return
    }

    // Validate form - this will update errors state
    const isValid = validateForm()

    // If form is not valid, don't proceed
    if (!isValid) {
      setSubmitError('Please fix the errors above before submitting.')
      return
    }

    // Additional check to ensure required fields are filled (removed subject)
    if (!formData.name.trim() || !formData.email.trim() || !formData.category || 
        !formData.message.trim()) {
      setSubmitError('Please fill out all required fields.')
      return
    }

    setIsSubmitting(true)
    
    try {
      const result = await sendEmail(formData)
      
      if (result.success) {
        setIsSubmitted(true)
        // Reset form and redirect after successful submission
        setTimeout(() => {
          navigate(returnPath)
        }, 3000)
      } else {
        setSubmitError('Failed to send message. Please try again or contact us directly at comparegrocerypricesuk@gmail.com')
      }
    } catch (error) {
      setSubmitError('An unexpected error occurred. Please try again later.')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Update the isFormValid function to properly check validation without relying on the errors object
  const isFormValid = () => {
    // Check each field individually without relying on errors state
    const nameValid = formData.name.trim().length >= 2 && 
                     formData.name.trim().length <= 50 && 
                     /^[a-zA-Z\s'-]+$/.test(formData.name.trim())
    
    const emailValid = formData.email.trim() && validateEmail(formData.email)
    
    const categoryValid = formData.category && formData.category.trim() !== ''
    
    // Subject can be empty, just check max length
    const subjectValid = formData.subject.trim().length <= 100
    
    const messageValid = formData.message.trim().length >= 10 && 
                        formData.message.length <= 1000

    return nameValid && emailValid && categoryValid && subjectValid && messageValid
  }

  // Check if the screen size is mobile
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

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

      {/* Contact Section */}
      <section className="contact-section">
        <div className="container">
          <div className="contact-content">
            <h1 className="contact-title">Get in Touch</h1>
            <p className="contact-description">
              Help us improve CompareGroceryPrices! Report bugs, suggest new features, or let us know about missing items.
            </p>

            {/* Contact Categories */}
            <div className="contact-categories">
              <div className="category-card">
                <div className="category-icon bug-icon">
                  <Bug size={24} />
                </div>
                <h3 className="category-title">Report a Bug</h3>
                <p className="category-description">Found something not working? Let us know so we can fix it.</p>
              </div>
              
              <div className="category-card">
                <div className="category-icon suggestion-icon">
                  <Lightbulb size={24} />
                </div>
                <h3 className="category-title">Suggest Improvement</h3>
                <p className="category-description">Have ideas to make our service better? We'd love to hear them.</p>
              </div>
              
              <div className="category-card">
                <div className="category-icon missing-icon">
                  <MessageSquare size={24} />
                </div>
                <h3 className="category-title">Missing Items</h3>
                <p className="category-description">Can't find a product? Report missing items from our database.</p>
              </div>
            </div>

            {/* Contact Form */}
            <div className="contact-form-container">
              {!isSubmitted ? (
                <form onSubmit={handleSubmit} className="contact-form" noValidate>
                  <h2 className="form-title">Send us a Message</h2>
                  
                  {submitError && (
                    <div className="error-banner">
                      <AlertCircle size={20} />
                      <span>{submitError}</span>
                    </div>
                  )}
                  
                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="name" className="form-label">Full Name *</label>
                      <input
                        type="text"
                        id="name"
                        name="name"
                        value={formData.name}
                        onChange={handleInputChange}
                        className={`form-input ${errors.name ? 'error' : ''}`}
                        placeholder="Enter your full name"
                        required
                        maxLength={50}
                      />
                      {errors.name && <span className="error-message">{errors.name}</span>}
                    </div>
                    
                    <div className="form-group">
                      <label htmlFor="email" className="form-label">Email Address *</label>
                      <input
                        type="email"
                        id="email"
                        name="email"
                        value={formData.email}
                        onChange={handleInputChange}
                        className={`form-input ${errors.email ? 'error' : ''}`}
                        placeholder="Enter your email address"
                        required
                      />
                      {errors.email && <span className="error-message">{errors.email}</span>}
                    </div>
                  </div>

                  <div className="form-group">
                    <label htmlFor="category" className="form-label">Category *</label>
                    <select
                      id="category"
                      name="category"
                      value={formData.category}
                      onChange={handleInputChange}
                      className={`form-select ${errors.category ? 'error' : ''}`}
                      required
                    >
                      <option value="">Select a category</option>
                      <option value="bug">🐛 Bug Report</option>
                      <option value="feature">💡 Feature Request</option>
                      <option value="missing-item">🛒 Missing Item</option>
                      <option value="general">💬 General Inquiry</option>
                      <option value="data-accuracy">📊 Data Accuracy</option>
                    </select>
                    {errors.category && <span className="error-message">{errors.category}</span>}
                  </div>

                  <div className="form-group">
                    <label htmlFor="subject" className="form-label">Subject</label>
                    <input
                      type="text"
                      id="subject"
                      name="subject"
                      value={formData.subject}
                      onChange={handleInputChange}
                      className={`form-input ${errors.subject ? 'error' : ''}`}
                      placeholder={isMobile ? "" : "Brief description of your message"}
                      maxLength={100}
                    />
                    {errors.subject && <span className="error-message">{errors.subject}</span>}
                  </div>

                  <div className="form-group">
                    <label htmlFor="message" className="form-label">Message *</label>
                    <textarea
                      id="message"
                      name="message"
                      value={formData.message}
                      onChange={handleInputChange}
                      className={`form-textarea ${errors.message ? 'error' : ''}`}
                      placeholder={isMobile ? "" : "Please provide detailed information about your request..."}
                      rows="6"
                      required
                      maxLength={1000}
                    ></textarea>
                    <div className="character-count">
                      <span className={formData.message.length > 1000 ? 'over-limit' : ''}>
                        {formData.message.length}/1000 characters
                      </span>
                    </div>
                    {errors.message && <span className="error-message">{errors.message}</span>}
                  </div>

                  {/* Honeypot field - hidden from users but visible to bots */}
                  <div style={{ display: 'none' }}>
                    <label htmlFor="website">Website (leave blank):</label>
                    <input
                      type="text"
                      id="website"
                      name="honeypot"
                      value={formData.honeypot}
                      onChange={handleInputChange}
                      tabIndex="-1"
                      autoComplete="off"
                    />
                  </div>

                  <div className="form-actions">
                    <Link to={returnPath} className="back-button">
                      <ArrowLeft className="button-icon" />
                      {returnPath === '/shopping-list' ? 'Back to Shopping List' : 'Back to Home'}
                    </Link>
                    
                    <button 
                      type="submit" 
                      className={`submit-button ${!isFormValid() || isSubmitting ? 'disabled' : ''}`}
                      disabled={!isFormValid() || isSubmitting}
                      style={{ pointerEvents: isSubmitting ? 'none' : 'auto' }}
                    >
                      {isSubmitting ? (
                        <>
                          <div className="spinner"></div>
                          Sending...
                        </>
                      ) : (
                        <>
                          <Send className="button-icon" />
                          Send Message
                        </>
                      )}
                    </button>
                  </div>
                </form>
              ) : (
                <div className="success-message">
                  <div className="success-icon">
                    <CheckCircle size={48} />
                  </div>
                  <h2 className="success-title">Message Sent Successfully!</h2>
                  <p className="success-description">
                    Thank you for your feedback! We've received your message and will get back to you at <strong>{formData.email}</strong> within 24-48 hours.
                    {returnPath === '/shopping-list' && (
                      <><br/><br/>You'll be redirected back to your shopping list in a moment to continue adding items.</>
                    )}
                  </p>
                  <div className="success-actions">
                    <Link to={returnPath} className="continue-button">
                      {returnPath === '/shopping-list' ? 'Continue Shopping List' : 'Return to Home'}
                    </Link>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <div className="footer">
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
            © 2025 CompareGroceryPrices. All rights reserved.
          </div>
        </div>
      </div>
    </div>
  )
}