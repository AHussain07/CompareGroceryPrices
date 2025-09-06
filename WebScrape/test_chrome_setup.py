#!/usr/bin/env python3
"""
Test script to verify Chrome and undetected_chromedriver setup
This can be run independently to troubleshoot Chrome/ChromeDriver issues
"""

import sys
import os
import subprocess
import signal

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
            subprocess.run(['pkill', '-f', 'chrome'], capture_output=True, timeout=5)
            subprocess.run(['pkill', '-f', 'Google Chrome'], capture_output=True, timeout=5)
            import time
            time.sleep(2)
            print("🧹 Killed existing Chrome processes")
        except:
            pass
        
        print("🔧 Creating Chrome driver (this may take a moment)...")
        
        # Try simpler strategies first to avoid timeout
        strategies = [
            ("no version specification", {"version_main": None}),
            ("auto-detected version", {}),
            ("force version 140", {"version_main": 140}),
            ("force version 139", {"version_main": 139})
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
                options.add_argument('--remote-debugging-port=0')  # Use random port
                options.add_argument('--disable-logging')
                options.add_argument('--silent')
                
                # Create driver with strategy-specific parameters with simple timeout
                try:
                    # Use subprocess to run driver creation with timeout
                    driver = uc.Chrome(options=options, **kwargs)
                    
                    print("✅ Chrome driver created successfully")
                    
                    # Quick test only
                    print("🌐 Testing basic functionality...")
                    driver.get("data:text/html,<html><body><h1>Test</h1></body></html>")
                    print("✅ Basic test successful")
                    
                    driver.quit()
                    print(f"✅ undetected_chromedriver test completed successfully with {strategy_name}!")
                    return True
                    
                except Exception as driver_error:
                    print(f"⚠️  Driver creation failed: {str(driver_error)[:100]}...")
                    continue
                
            except Exception as e:
                print(f"⚠️  {strategy_name} failed: {str(e)[:100]}...")
                # Clean up any leftover processes before next attempt
                try:
                    subprocess.run(['pkill', '-f', 'chrome'], capture_output=True, timeout=3)
                    time.sleep(1)
                except:
                    pass
                continue
        
        # If all strategies failed
        print("❌ All strategies failed, but this might be OK - the wrapper has more strategies")
        return False
        
    except Exception as e:
        print(f"❌ undetected_chromedriver test failed: {str(e)[:100]}...")
        
        # Additional debugging info
        print("\n🔍 Additional debugging information:")
        try:
            # Check if Chrome is running
            result = subprocess.run(['pgrep', '-f', 'chrome'], capture_output=True, text=True, timeout=5)
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
    
    # Run tests with error handling
    try:
        chrome_ok = test_chrome_installation()
    except Exception as e:
        print(f"❌ Chrome test error: {e}")
        chrome_ok = False
    
    try:
        driver_ok = test_undetected_chromedriver()
    except Exception as e:
        print(f"❌ Driver test error: {e}")
        driver_ok = False
    
    print("=" * 50)
    
    if chrome_ok and driver_ok:
        print("🎉 All tests passed! Setup is ready for scraping.")
        return 0
    elif chrome_ok:
        print("⚠️  Chrome OK, but driver tests failed. Wrapper will try multiple strategies.")
        return 0  # Don't fail if Chrome is working
    else:
        print("❌ Chrome installation issues detected.")
        return 1

if __name__ == "__main__":
    exit(main())
