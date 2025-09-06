#!/usr/bin/env python3
"""
Test script to verify Chrome and undetected_chromedriver setup
This can be run independently to troubleshoot Chrome/ChromeDriver issues
"""

import sys
import os
import subprocess

def test_chrome_installation():
    """Test if Chrome is properly installed"""
    print("🔍 Testing Chrome installation...")
    
    try:
        # Test Chrome binary
        result = subprocess.run(['google-chrome', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Chrome found: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Chrome test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Chrome not found or not working: {e}")
        return False

def test_undetected_chromedriver():
    """Test undetected_chromedriver setup"""
    print("🔍 Testing undetected_chromedriver...")
    
    try:
        import undetected_chromedriver as uc
        print("✅ undetected_chromedriver imported successfully")
        
        # Create driver with minimal options
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        
        print("🔧 Creating Chrome driver (this may take a moment)...")
        
        # Let undetected_chromedriver auto-detect the version
        driver = uc.Chrome(options=options)
        print("✅ Chrome driver created successfully")
        
        # Simple test
        print("🌐 Testing basic navigation...")
        driver.get("https://www.google.com")
        title = driver.title
        print(f"✅ Navigation successful. Page title: {title}")
        
        driver.quit()
        print("✅ undetected_chromedriver test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ undetected_chromedriver test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🧪 Chrome and ChromeDriver Setup Test")
    print("=" * 50)
    
    # Environment info
    print(f"Python version: {sys.version}")
    print(f"Operating system: {os.name}")
    print(f"Current directory: {os.getcwd()}")
    
    if 'DISPLAY' in os.environ:
        print(f"Display: {os.environ['DISPLAY']}")
    
    print("=" * 50)
    
    # Run tests
    chrome_ok = test_chrome_installation()
    driver_ok = test_undetected_chromedriver()
    
    print("=" * 50)
    
    if chrome_ok and driver_ok:
        print("🎉 All tests passed! Setup is ready for scraping.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit(main())
