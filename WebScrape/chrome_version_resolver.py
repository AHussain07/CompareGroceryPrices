#!/usr/bin/env python3
"""
Advanced Chrome version resolver
This script attempts to resolve Chrome version inconsistencies
"""

import subprocess
import time
import os
import sys

def kill_all_chrome():
    """Kill all Chrome processes"""
    commands = [
        ['pkill', '-f', 'chrome'],
        ['pkill', '-f', 'Google Chrome'],
        ['pkill', '-f', 'chromedriver'],
        ['killall', 'chrome'],
        ['killall', 'google-chrome']
    ]
    
    for cmd in commands:
        try:
            subprocess.run(cmd, capture_output=True, timeout=5)
        except:
            pass
    
    time.sleep(3)

def test_chrome_versions():
    """Test different ways to get Chrome version"""
    print("🔍 Testing Chrome version detection methods...")
    
    methods = [
        (['google-chrome', '--version'], "Standard version check"),
        (['google-chrome', '--no-sandbox', '--version'], "No sandbox version check"),
        (['google-chrome', '--headless', '--version'], "Headless version check"),
        (['google-chrome', '--no-sandbox', '--disable-dev-shm-usage', '--version'], "Safe mode version check"),
        (['/usr/bin/google-chrome', '--version'], "Direct binary version check")
    ]
    
    versions = {}
    
    for cmd, description in methods:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                versions[description] = version
                print(f"✅ {description}: {version}")
            else:
                print(f"❌ {description}: Failed with code {result.returncode}")
        except Exception as e:
            print(f"❌ {description}: Exception {e}")
    
    return versions

def force_chrome_refresh():
    """Force Chrome to refresh its version information"""
    print("🔄 Forcing Chrome version refresh...")
    
    # Kill all Chrome processes
    kill_all_chrome()
    
    # Start Chrome briefly to force version update
    try:
        print("Starting Chrome briefly...")
        proc = subprocess.Popen([
            'google-chrome', 
            '--headless', 
            '--no-sandbox', 
            '--disable-dev-shm-usage',
            '--remote-debugging-port=9223',
            '--user-data-dir=/tmp/chrome-version-refresh'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        time.sleep(5)
        proc.terminate()
        proc.wait(timeout=5)
        print("✅ Chrome refresh completed")
    except Exception as e:
        print(f"⚠️  Chrome refresh had issues: {e}")
    
    # Clean up
    kill_all_chrome()
    
    # Remove temp user data
    try:
        subprocess.run(['rm', '-rf', '/tmp/chrome-version-refresh'], capture_output=True)
    except:
        pass

def main():
    """Main function"""
    print("🔧 Chrome Version Resolver")
    print("=" * 40)
    
    try:
        print("Initial version test:")
        initial_versions = test_chrome_versions()
        
        # Check for inconsistencies
        unique_versions = set(initial_versions.values())
        if len(unique_versions) > 1:
            print(f"\n⚠️  Found {len(unique_versions)} different versions:")
            for version in unique_versions:
                print(f"   - {version}")
            
            print("\n🔄 Attempting to resolve inconsistency...")
            force_chrome_refresh()
            
            print("\nPost-refresh version test:")
            post_versions = test_chrome_versions()
            
            post_unique = set(post_versions.values())
            if len(post_unique) == 1:
                print(f"✅ Version consistency achieved: {list(post_unique)[0]}")
            else:
                print(f"⚠️  Still {len(post_unique)} different versions after refresh")
        else:
            print(f"✅ All methods report consistent version: {list(unique_versions)[0]}")
        
        print("\n" + "=" * 40)
        return 0
        
    except Exception as e:
        print(f"❌ Chrome version resolver error: {e}")
        print("This is not critical - continuing with scraper...")
        return 0  # Don't fail the workflow

if __name__ == "__main__":
    exit(main())
