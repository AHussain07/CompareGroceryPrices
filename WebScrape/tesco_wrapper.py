#!/usr/bin/env python3
"""
Wrapper script for tesco.py to handle Chrome version compatibility
This script prepares the environment and runs the original tesco.py
"""

import os
import sys
import subprocess
import time

def setup_chrome_environment():
    """Setup Chrome environment variables and cleanup"""
    print("🔧 Setting up Chrome environment...")
    
    # Clear any existing Chrome/ChromeDriver cache
    import shutil
    cache_dirs = [
        os.path.expanduser("~/.local/share/undetected_chromedriver"),
        os.path.expanduser("~/.cache/undetected_chromedriver"),
        "/tmp/undetected_chromedriver"
    ]
    
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            try:
                shutil.rmtree(cache_dir)
                print(f"✅ Cleared cache: {cache_dir}")
            except Exception as e:
                print(f"⚠️  Could not clear {cache_dir}: {e}")
    
    # Set environment variables
    os.environ['CHROME_BIN'] = '/usr/bin/google-chrome'
    os.environ['UNDETECTED_CHROMEDRIVER_FORCE_DOWNLOAD'] = '1'
    
    # Kill any existing Chrome processes
    try:
        subprocess.run(['pkill', '-f', 'chrome'], capture_output=True)
        time.sleep(2)
        print("✅ Killed existing Chrome processes")
    except:
        pass

def detect_chrome_version():
    """Detect installed Chrome version"""
    try:
        result = subprocess.run(['google-chrome', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            import re
            version_match = re.search(r'(\d+)', result.stdout)
            if version_match:
                return int(version_match.group(1))
    except Exception as e:
        print(f"⚠️  Could not detect Chrome version: {e}")
    return None

def patch_tesco_script():
    """Temporarily patch tesco.py to handle version compatibility"""
    print("🔧 Applying temporary compatibility patch...")
    
    chrome_version = detect_chrome_version()
    
    # Read the original tesco.py
    with open('tesco.py', 'r') as f:
        content = f.read()
    
    # Create a patched version that doesn't specify version_main
    if 'version_main=139' in content:
        print(f"🔧 Patching Chrome version (detected: {chrome_version})")
        
        if chrome_version:
            # Use detected version
            patched_content = content.replace('version_main=139', f'version_main={chrome_version}')
        else:
            # Remove version specification entirely
            patched_content = content.replace('version_main=139,', '')
            patched_content = patched_content.replace(', version_main=139', '')
            patched_content = patched_content.replace('version_main=139', '')
        
        # Write patched version
        with open('tesco_patched.py', 'w') as f:
            f.write(patched_content)
        
        print("✅ Created compatibility-patched version: tesco_patched.py")
        return True
    else:
        print("ℹ️  No version specification found to patch")
        return False

def main():
    """Main wrapper function"""
    print("🚀 Tesco Scraper Wrapper - Chrome Compatibility Handler")
    print("=" * 60)
    
    # Setup environment
    setup_chrome_environment()
    
    # Detect Chrome version
    chrome_version = detect_chrome_version()
    if chrome_version:
        print(f"🔍 Detected Chrome version: {chrome_version}")
    
    # Try to patch the script for compatibility
    patched = patch_tesco_script()
    
    # Run the appropriate version
    if patched:
        print("🏃 Running patched version...")
        script_name = 'tesco_patched.py'
    else:
        print("🏃 Running original version...")
        script_name = 'tesco.py'
    
    try:
        # Execute the script
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=False, 
                              text=True)
        return result.returncode
    except Exception as e:
        print(f"❌ Error running script: {e}")
        return 1
    finally:
        # Cleanup patched file
        if patched and os.path.exists('tesco_patched.py'):
            os.remove('tesco_patched.py')
            print("🧹 Cleaned up patched file")

if __name__ == "__main__":
    exit(main())
