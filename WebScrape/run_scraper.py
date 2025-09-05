#!/usr/bin/env python3
import sys
import subprocess
import os
from datetime import datetime

def run_scraper(script_name, timeout_minutes=30):
    """Run a scraper script with timeout and error handling"""
    print(f"🚀 Starting {script_name}...")
    start_time = datetime.now()
    
    try:
        # Run the scraper
        result = subprocess.run(
            [sys.executable, script_name],
            timeout=timeout_minutes * 60,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        if result.returncode == 0:
            print(f"✅ {script_name} completed successfully in {duration}")
            if result.stdout:
                print("Output:", result.stdout[-500:])  # Last 500 chars
        else:
            print(f"❌ {script_name} failed with return code {result.returncode}")
            if result.stderr:
                print("Error:", result.stderr[-500:])
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {script_name} timed out after {timeout_minutes} minutes")
        return False
    except Exception as e:
        print(f"💥 {script_name} crashed: {e}")
        return False

if __name__ == "__main__":
    scrapers = [
        ("aldi.py", 30),
        ("tesco.py", 30), 
        ("sainsburys.py", 40),
        ("morrisons.py", 30),
        ("asda.py", 45)
    ]
    
    results = {}
    for script, timeout in scrapers:
        results[script] = run_scraper(script, timeout)
    
    print("\n" + "="*50)
    print("📊 SCRAPING SUMMARY:")
    for script, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"{script}: {status}")
    print("="*50)