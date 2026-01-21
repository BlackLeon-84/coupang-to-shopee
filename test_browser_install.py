import os
import sys
from playwright.sync_api import sync_playwright
from playwright.__main__ import main

# 1. Setup specific test directory for browsers
base_dir = os.path.dirname(os.path.abspath(__file__))
browser_dir = os.path.join(base_dir, "test_browsers")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browser_dir

print(f"Testing browser install to: {browser_dir}")

# 2. Simulate the "Self-Repair" Install Logic
print("Running Install Command...")
try:
    # Simulating: sys.argv = ["playwright", "install", "chromium"]
    # I suspect we need "chromium-headless-shell" too
    sys.argv = ["playwright", "install", "chromium"]
    main()
except SystemExit:
    pass
except Exception as e:
    print(f"Install failed: {e}")

# 3. Verify files
print("Checking installed files:")
if os.path.exists(browser_dir):
    for root, dirs, files in os.walk(browser_dir):
         for d in dirs:
             print(f" - Dir: {d}")
else:
    print("Browser directory not created!")

# 4. Try Launch
print("Attempting Launch...")
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        print("Success! Browser launched.")
        browser.close()
except Exception as e:
    print(f"Launch Failed: {e}")
