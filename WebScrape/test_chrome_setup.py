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
        
        # Get Chrome version for compatibility check
        chrome_version = None
        try:
            result = subprocess.run(['google-chrome', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                import re
                version_match = re.search(r'(\d+)', result.stdout)
                if version_match:
                    chrome_version = int(version_match.group(1))
                    print(f"🔍 Detected Chrome major version: {chrome_version}")
        except Exception as e:
            print(f"⚠️  Could not detect Chrome version: {e}")
        
        # Create driver with minimal options and version handling
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-background-timer-throttling')
        
        print("🔧 Creating Chrome driver (this may take a moment)...")
        
        # Try with auto-detected version first
        try:
            print("🔧 Attempting with auto-detected version...")
            driver = uc.Chrome(options=options)
        except Exception as e1:
            print(f"⚠️  Auto-detection failed: {e1}")
            
            # Try with explicit version if we detected it
            if chrome_version:
                try:
                    print(f"🔧 Attempting with explicit version {chrome_version}...")
                    driver = uc.Chrome(version_main=chrome_version, options=options)
                except Exception as e2:
                    print(f"⚠️  Explicit version failed: {e2}")
                    
                    # Try without version specification
                    print("🔧 Attempting without version specification...")
                    driver = uc.Chrome(version_main=None, options=options)
            else:
                # Re-raise the original exception if we can't try alternatives
                raise e1
        
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
        
        # Additional debugging info
        print("\n🔍 Additional debugging information:")
        try:
            # Check if Chrome is running
            result = subprocess.run(['pgrep', '-f', 'chrome'], capture_output=True, text=True)
            if result.stdout.strip():
                print(f"⚠️  Found running Chrome processes: {result.stdout.strip()}")
            else:
                print("ℹ️  No Chrome processes found running")
        except:
            pass
            
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
