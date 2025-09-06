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
    
    # Kill any existing Chrome processes more thoroughly
    try:
        subprocess.run(['pkill', '-f', 'chrome'], capture_output=True)
        subprocess.run(['pkill', '-f', 'Google Chrome'], capture_output=True)
        subprocess.run(['pkill', '-f', 'chromedriver'], capture_output=True)
        time.sleep(3)
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
    
    # Create multiple patched versions for different strategies
    patches_created = []
    
    if 'version_main=139' in content:
        print(f"🔧 Patching Chrome version (detected: {chrome_version})")
        
        # Strategy 1: Use detected version
        if chrome_version:
            patched_content_1 = content.replace('version_main=139', f'version_main={chrome_version}')
            with open('tesco_patched_v1.py', 'w') as f:
                f.write(patched_content_1)
            patches_created.append(('tesco_patched_v1.py', f'explicit version {chrome_version}'))
        
        # Strategy 2: Remove version specification entirely
        patched_content_2 = content.replace('version_main=139,', '')
        patched_content_2 = patched_content_2.replace(', version_main=139', '')
        patched_content_2 = patched_content_2.replace('version_main=139', '')
        with open('tesco_patched_v2.py', 'w') as f:
            f.write(patched_content_2)
        patches_created.append(('tesco_patched_v2.py', 'no version specification'))
        
        # Strategy 3: Force version 140 (since Chrome reports 140)
        patched_content_3 = content.replace('version_main=139', 'version_main=140')
        with open('tesco_patched_v3.py', 'w') as f:
            f.write(patched_content_3)
        patches_created.append(('tesco_patched_v3.py', 'force version 140'))
        
        # Strategy 4: Use None explicitly
        patched_content_4 = content.replace('version_main=139', 'version_main=None')
        with open('tesco_patched_v4.py', 'w') as f:
            f.write(patched_content_4)
        patches_created.append(('tesco_patched_v4.py', 'explicit None version'))
        
        print(f"✅ Created {len(patches_created)} compatibility patches")
        return patches_created
    else:
        print("ℹ️  No version specification found to patch")
        return []

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
    patches = patch_tesco_script()
    
    # Try different strategies in order of preference
    strategies = []
    
    # Add patched versions if available
    for patch_file, description in patches:
        strategies.append((patch_file, f"patched version ({description})"))
    
    # Add original as fallback
    strategies.append(('tesco.py', 'original version'))
    
    print(f"� Will try {len(strategies)} strategies...")
    
    for i, (script_name, description) in enumerate(strategies, 1):
        print(f"\n🏃 Strategy {i}/{len(strategies)}: Running {description}...")
        
        try:
            # Execute the script
            result = subprocess.run([sys.executable, script_name], 
                                  capture_output=False, 
                                  text=True,
                                  timeout=5400)  # 90 minutes timeout
            
            if result.returncode == 0:
                print(f"✅ Success with {description}!")
                # Cleanup patched files on success
                for patch_file, _ in patches:
                    if os.path.exists(patch_file):
                        try:
                            os.remove(patch_file)
                            print(f"🧹 Cleaned up {patch_file}")
                        except:
                            pass
                return 0
            else:
                print(f"⚠️  {description} failed with exit code {result.returncode}")
                if i < len(strategies):
                    print("🔄 Trying next strategy...")
                    # Clean up any running Chrome processes before next attempt
                    try:
                        subprocess.run(['pkill', '-f', 'chrome'], capture_output=True)
                        time.sleep(2)
                    except:
                        pass
                    continue
                    
        except subprocess.TimeoutExpired:
            print(f"⏱️  {description} timed out after 90 minutes")
            if i < len(strategies):
                print("🔄 Trying next strategy...")
                # Kill processes and try next
                try:
                    subprocess.run(['pkill', '-f', 'chrome'], capture_output=True)
                    subprocess.run(['pkill', '-f', 'python'], capture_output=True)
                    time.sleep(3)
                except:
                    pass
                continue
        except Exception as e:
            print(f"❌ Error running {description}: {e}")
            if i < len(strategies):
                print("🔄 Trying next strategy...")
                continue
    
    print("❌ All strategies failed.")
    
    # Cleanup patched files
    for patch_file, _ in patches:
        if os.path.exists(patch_file):
            try:
                os.remove(patch_file)
                print(f"🧹 Cleaned up {patch_file}")
            except:
                pass
    
    return 1

if __name__ == "__main__":
    exit(main())
