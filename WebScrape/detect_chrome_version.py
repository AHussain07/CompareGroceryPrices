#!/usr/bin/env python3
"""
Chrome version detection utility
This script detects the installed Chrome version and provides compatibility info
"""

import subprocess
import re
import sys

def get_chrome_version():
    """Get the installed Chrome version"""
    try:
        result = subprocess.run(['google-chrome', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_text = result.stdout.strip()
            # Extract version number (e.g., "Google Chrome 131.0.6778.85" -> "131.0.6778.85")
            version_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', version_text)
            if version_match:
                full_version = version_match.group(1)
                major_version = full_version.split('.')[0]
                return full_version, major_version, version_text
            else:
                return None, None, version_text
        else:
            return None, None, f"Error: {result.stderr}"
    except Exception as e:
        return None, None, f"Exception: {e}"

def main():
    """Detect Chrome version and provide compatibility info"""
    print("🔍 Chrome Version Detection")
    print("=" * 40)
    
    full_version, major_version, raw_output = get_chrome_version()
    
    print(f"Raw output: {raw_output}")
    
    if full_version and major_version:
        print(f"✅ Chrome version detected: {full_version}")
        print(f"✅ Major version: {major_version}")
        
        # Provide guidance based on version
        try:
            major_int = int(major_version)
            if major_int >= 130:
                print("✅ Chrome version is recent and should work well with undetected_chromedriver")
                print("💡 Recommendation: Let undetected_chromedriver auto-detect the version")
                print("   (Do not specify version_main parameter)")
            elif major_int >= 120:
                print("⚠️  Chrome version is moderately recent")
                print(f"💡 Recommendation: Try version_main={major_version}")
            else:
                print("⚠️  Chrome version is quite old")
                print("💡 Recommendation: Consider updating Chrome or use version_main=None")
                
        except ValueError:
            print("❌ Could not parse major version as integer")
            
    else:
        print("❌ Could not detect Chrome version")
        print("💡 This might indicate Chrome is not properly installed")
        
    print("=" * 40)
    return 0

if __name__ == "__main__":
    exit(main())
