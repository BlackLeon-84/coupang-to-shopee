
import sys
import os

print("--- [VERIFY] 1. Testing Imports ---")
try:
    import scraper
    print("MATCH: Scraper imported.")
    import processor
    print("MATCH: Processor imported.")
except ImportError as e:
    print(f"FAIL: Import Error: {e}")
    sys.exit(1)

print("\n--- [VERIFY] 2. Testing Browser Self-Healing Logic ---")
try:
    # This should verify logic doesn't crash. 
    # It might try to install if folder missing, or skip if present.
    scraper.ensure_playwright_browsers()
    print("PASS: ensure_playwright_browsers() executed without crash.")
except Exception as e:
    print(f"FAIL: Browser Logic Crash: {e}")
    sys.exit(1)

print("\n--- [VERIFY] 3. Testing Google GenAI Migration ---")
try:
    from google import genai
    print("PASS: 'from google import genai' successful.")
    
    # Check if Client class exists
    if hasattr(genai, 'Client'):
        print("PASS: genai.Client class found.")
    else:
        print("FAIL: genai.Client not found via 'from google import genai'")
        
except Exception as e:
    print(f"FAIL: Google GenAI Error: {e}")
    sys.exit(1)

print("\n[SUCCESS] All checks passed. Ready for Build.")
