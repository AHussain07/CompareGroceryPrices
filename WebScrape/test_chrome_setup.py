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
        
        # Kill any running Chrome processes first
        try:
            subprocess.run(['pkill', '-f', 'chrome'], capture_output=True)
            subprocess.run(['pkill', '-f', 'Google Chrome'], capture_output=True)
            import time
            time.sleep(3)
            print("🧹 Killed existing Chrome processes")
        except:
            pass
        
        print("🔧 Creating Chrome driver (this may take a moment)...")
        
        # Try multiple strategies with fresh ChromeOptions each time
        strategies = [
            ("auto-detected version", {}),
            ("explicit version", {"version_main": chrome_version} if chrome_version else {}),
            ("no version specification", {"version_main": None}),
            ("force version 139", {"version_main": 139}),
            ("force version 140", {"version_main": 140})
        ]
        
        for strategy_name, kwargs in strategies:
            try:
                print(f"🔧 Attempting with {strategy_name}...")
                
                # Create fresh ChromeOptions for each attempt
                options = uc.ChromeOptions()
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-web-security')
                options.add_argument('--allow-running-insecure-content')
                options.add_argument('--disable-background-timer-throttling')
                options.add_argument('--remote-debugging-port=0')  # Use random port
                
                # Create driver with strategy-specific parameters
                driver = uc.Chrome(options=options, **kwargs)
                
                print("✅ Chrome driver created successfully")
                
                # Simple test
                print("🌐 Testing basic navigation...")
                driver.get("https://www.google.com")
                title = driver.title
                print(f"✅ Navigation successful. Page title: {title}")
                
                driver.quit()
                print(f"✅ undetected_chromedriver test completed successfully with {strategy_name}!")
                return True
                
            except Exception as e:
                print(f"⚠️  {strategy_name} failed: {e}")
                # Clean up any leftover processes before next attempt
                try:
                    subprocess.run(['pkill', '-f', 'chrome'], capture_output=True)
                    import time
                    time.sleep(1)
                except:
                    pass
                continue
        
        # If all strategies failed
        print("❌ All strategies failed")
        return False
        
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
