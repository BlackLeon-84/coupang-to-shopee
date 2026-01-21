import os
import time
import re
from playwright.sync_api import sync_playwright
# try-except for stealth in case it's not installed yet, but we just installed it.
try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None

import requests

def clean_filename(name):
    """Cleans a string to be used as a valid filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name)

import shutil
from urllib.parse import unquote, urlparse

def download_image(url, save_path):
    """Downloads an image from a URL or copies if local."""
    try:
        # Check if local file
        if url.startswith("file://") or os.path.exists(url) or os.path.exists(unquote(url).replace("file:///", "")):
            local_path = url
            if url.startswith("file:///"):
                if os.name == 'nt': # Windows
                     local_path = unquote(url).replace("file:///", "")
                else:
                     local_path = unquote(url).replace("file://", "")
            
            # If path not found blindly, might be relative to the original html location? 
            # But the scraper extracts what's in DOM. 
            # If "Save As" was used, src usually becomes relative or local absolute.
            
            if os.path.exists(local_path):
                shutil.copy2(local_path, save_path)
                return True
            else:
                # Try simple request for external http links in local html
                pass

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.coupang.com/"
        }
        
        if url.startswith("//"):
            url = "https:" + url
            
        if not url.startswith("http"):
             # Could be relative path from the html file.
             # This is tricky without knowing base path of html.
             # For now, skip if not absolute http.
             return False

        response = requests.get(url, headers=headers, stream=True, timeout=10)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
    return False


import json

def extract_json_ld(page):
    """Extracts product info from JSON-LD."""
    try:
        # Evaluate script content
        json_ld = page.evaluate("""() => {
            const script = document.querySelector('script[type="application/ld+json"]');
            return script ? script.innerText : null;
        }""")
        
        if json_ld:
            data = json.loads(json_ld)
            # Handle list of JSON-LD
            if isinstance(data, list):
                for item in data:
                    if item.get('@type') == 'Product':
                        data = item
                        break
            
            if data.get('@type') == 'Product':
                print("Found JSON-LD Product data!")
                result = {
                    "title": data.get("name"),
                    "price": 0,
                    "images": data.get("image", []),
                    "weight": None, # JSON-LD might not have weight
                    "detail_text": data.get("description", "")
                }
                
                # Extract Price
                offers = data.get("offers")
                if offers:
                    if isinstance(offers, list):
                        offers = offers[0]
                    result["price"] = int(offers.get("price", 0))
                
                # Normalize images
                if isinstance(result["images"], str):
                    result["images"] = [result["images"]]
                
                return result
    except Exception as e:
        print(f"Error extracting JSON-LD: {e}")
    return None

def ensure_playwright_browsers():
    """Ensures browsers are installed in the EXE environment."""
    try:
        from playwright.__main__ import main
        import sys
        
        # Determine the base directory for EXE
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            browser_dir = os.path.join(base_dir, "browsers")
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browser_dir
        else:
            # For local dev, rely on default or existing path
            browser_dir = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")

        if browser_dir and (not os.path.exists(browser_dir) or not os.listdir(browser_dir)):
            print(f"Browser not found in {browser_dir}. Installing...")
            # Use headless-shell for smaller footprint if available, otherwise chromium
            sys.argv = ["playwright", "install", "chromium"]
            try:
                main()
            except SystemExit:
                pass
            print("Browser installation complete.")
    except Exception as e:
        print(f"Failed to auto-install browser: {e}")

def extract_opengraph(page):
    """Extracts OpenGraph metadata."""
    data = {}
    try:
        # Title
        data['title'] = page.get_attribute("meta[property='og:title']", "content")
        # Image
        img = page.get_attribute("meta[property='og:image']", "content")
        if img: data['images'] = [img]
        # Description
        data['detail_text'] = page.get_attribute("meta[property='og:description']", "content")
        # Price (Some sites use product:price:amount)
        price = page.get_attribute("meta[property='product:price:amount']", "content")
        if price: data['price'] = int(float(price))
    except:
        pass
    return data

def scrape_product(url, output_dir="output"):
    """
    Universal Scraper for Coupang, Daiso, and others.
    """
    ensure_playwright_browsers()
    
    # Create output directories
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    result = {
        "title": None,
        "price": None,
        "images": [],
        "image_urls": [], # Local paths
        "detail_text": "",
        "weight": None
    }
    
    with sync_playwright() as p:
        # Launch Browser (Headless=True usually fine, but False for debugging/antibot)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Standard viewport
            viewport={"width": 1280, "height": 720}
        )
        
        if stealth_sync:
            stealth_sync(context)
            
        page = context.new_page()
        
        try:
            print(f"visiting: {url}")
            # Domain check
            is_coupang = "coupang.com" in url
            
            if is_coupang:
                # ... Existing Coupang Logic ...
                page.set_extra_http_headers({"Referer": "https://www.coupang.com/"})
                # Cookie logic (omitted for brevity, assume handled by page.goto)
            
            # Navigate
            from urllib.parse import unquote
            
            if url.startswith("file:"):
                try:
                    # Clean path
                    local_path = unquote(url).replace("file:///", "").replace("file://", "")
                    # Windows path fix (remove leading / if present before Drive letter)
                    if os.name == 'nt' and local_path.startswith("/") and ":" in local_path:
                         local_path = local_path.lstrip("/")
                    
                    if os.path.exists(local_path):
                        print(f"Loading local file content: {local_path}")
                        with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
                            page.set_content(f.read(), wait_until="domcontentloaded")
                    else:
                        print(f"File not found at {local_path}, trying goto...")
                        page.goto(url, timeout=60000, wait_until="domcontentloaded")
                except Exception as e:
                    print(f"Local Load Error: {e}")
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
            else:
                try:
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
                except Exception as e:
                    print(f"Navigation error: {e}")
            
            page.wait_for_timeout(2000) # Wait for dynamic loading
            
            # --- STRATEGY 1: JSON-LD (Best for everyone) ---
            json_data = extract_json_ld(page)
            if json_data:
                result.update(json_data)
                print(f"Extracted JSON-LD: {result.get('title')}")
            
            # --- STRATEGY 2: OpenGraph (Universal Backup) ---
            if not result['title']:
                og_data = extract_opengraph(page)
                # Merge only missing fields
                for k, v in og_data.items():
                    if not result.get(k) and v:
                        result[k] = v
                print(f"Extracted OpenGraph: {result.get('title')}")

            # --- STRATEGY 3: CSS Selectors (Site Specific) ---
            
            if is_coupang:
                 # ... Existing Coupang Selectors (Title, Price, Images) ...
                 if not result["title"]:
                    el = page.query_selector("h2.prod-buy-header__title")
                    if el: result["title"] = el.inner_text().strip()
                 
                 if not result['price']:
                    # Try multiple selectors
                    selectors = [".total-price > strong", "span.total-price > strong", ".prod-sale-price > span.total-price > strong"]
                    for sel in selectors:
                        el = page.query_selector(sel)
                        if el:
                            txt = el.inner_text().replace(",", "").replace("원", "").strip()
                            if txt.isdigit(): 
                                result['price'] = int(txt)
                                break
            else:
                # --- GENERIC / DAISO FALLBACK ---
                if not result["title"]:
                    # Try h1
                    el = page.query_selector("h1")
                    if el: result["title"] = el.inner_text().strip()
                
                if not result["price"]:
                    # Try finding price by regex in body or specific classes
                    # Daiso usually uses .price or strong tag with won
                    try:
                        # Find any element containing '원' AND digits
                        # Safe approach: Look for common classes "price", "cost", "amount", "sale"
                        price_el = page.query_selector(".price, .cost, .amount, .sale-price")
                        if price_el:
                             txt = re.sub(r'[^0-9]', '', price_el.inner_text())
                             if txt: result['price'] = int(txt)
                        
                        # Fallback: Regex on body (Risky but effective)
                        if not result['price']:
                            body_text = page.inner_text("body")
                            # Look for "1,000원" pattern near the top? Hard.
                            # Just look for the first big number with Won?
                            pass 
                    except: pass
                
                # ALWAYS Generic Search (Don't skip just because OG found one cover image)
                if True:
                    # Try to find base URL for relative links
                    base_url = ""
                    try:
                        og_url = page.get_attribute("meta[property='og:url']", "content")
                        if og_url:
                            from urllib.parse import urlparse
                            parsed = urlparse(og_url)
                            base_url = f"{parsed.scheme}://{parsed.netloc}"
                    except: pass
                    
                    # If base_url missing but we see 'daiso' in title or html, guess.
                    if not base_url and ("daiso" in (result['title'] or "").lower() or "daisomall" in url):
                        base_url = "https://www.daisomall.co.kr"

                    # Find images in Main Page AND Iframes
                    all_frames = page.frames
                    valid_imgs = []
                    
                    for frame in all_frames:
                        try:
                            imgs = frame.query_selector_all("img")
                            for img in imgs:
                                # Check lazy load attributes first
                                src = img.get_attribute("data-original") or img.get_attribute("data-src") or img.get_attribute("src")
                                
                                if not src: continue
                                
                                # Fix Relative
                                if src.startswith("//"):
                                    src = "https:" + src
                                elif src.startswith("/"):
                                    if base_url:
                                        src = base_url + src
                                    else:
                                        continue 
                                
                                # Filter valid images
                                if "http" in src and "logo" not in src and "icon" not in src and "blank" not in src and "gif" not in src:
                                     # Deduplicate
                                     if src not in valid_imgs:
                                         valid_imgs.append(src)
                        except: 
                            continue # Frame might be detached or cross-origin
                    
                    if len(valid_imgs) < 2:
                        # BRUTE FORCE FALLBACK
                        # If DOM/Iframes failed (common in saved HTML), scan raw text.
                        print("Using Brute Force Regex for Images...")
                        html_content = page.content()
                        # Regex to find http/https urls ending in image extensions
                        regex = r'https?://[^\s"\'<>]+?\.(?:jpg|jpeg|png|gif|webp)'
                        matches = re.findall(regex, html_content)
                        
                        for m in matches:
                             if "logo" not in m and "icon" not in m and "blank" not in m:
                                 # Daiso/CDN specific filters could live here
                                 if m not in valid_imgs:
                                     valid_imgs.append(m)
                                     
                    if valid_imgs:
                         # Prioritize og:image or first big image
                         result['images'] = valid_imgs[:15] # Grab more

            # 3. Extract Weight (Still need CSS usually)
            weight_found = False
            # Check description for weight if JSON didn't have it
            if not result['weight']:
                rows = page.query_selector_all("table tr") 
                for row in rows:
                    th = row.query_selector("th")
                    td = row.query_selector("td")
                    if th and td:
                        header = th.inner_text()
                        value = td.inner_text()
                        if "중량" in header or "무게" in header or "용량" in header:
                            result["weight"] = value
                            weight_found = True
                            print(f"Found Weight Info: {header} : {value}")
                            break
            
            # 4. Images
            # We want BOTH JSON images (usually high quality gallery) AND Detail images (from body)
            image_urls = result['images'] if result['images'] else []
            
            # Scrape Gallery/Thumbnails via CSS if JSON missed them or to be safe (Coupang specific)
            if is_coupang:
                thumbnails = page.query_selector_all(".prod-image__item")
                for thumb in thumbnails:
                    img_el = thumb.query_selector("img")
                    if img_el:
                        src = img_el.get_attribute("src") or img_el.get_attribute("data-src")
                        if src:
                            # Convert thumbnail to large
                            large_src = src.replace("48x48ex", "492x492ex") 
                            if large_src.startswith("//"):
                                 large_src = "https:" + large_src
                            if large_src not in result['images']:
                                result['images'].append(large_src)

                # Content Images (Detail section) - CRITICAL for user
                print("Scrolling for detail images...")
                # Scroll slowly to trigger lazy load
                for i in range(5):
                    page.mouse.wheel(0, 1000)
                    time.sleep(0.5)
                
                try:
                    page.keyboard.press("End")
                    time.sleep(2)
                except:
                    pass
                
                detail_imgs = page.query_selector_all("#productDetail img")
                for img in detail_imgs:
                    src = img.get_attribute("src") or img.get_attribute("data-src")
                    if src:
                        if src.startswith("//"):
                            src = "https:" + src
                        if "gif" not in src and "blank" not in src:
                            if src not in result['images']:
                                result['images'].append(src)
            
            print(f"Found {len(image_urls)} images (JSON + CSS).")
            result['images'] = image_urls # Update result
            
            # Store original URLs for Excel export (Shopee needs URLs)
            result['image_urls'] = image_urls
            
            # Download Images to UNIQUE folder to prevent overwrites
            # import re # Removed to avoid UnboundLocalError
            safe_title = re.sub(r'[\\/*?:"<>|]', "", result['title'])[:30].strip()
            timestamp = int(time.time())
            product_img_dir = os.path.join(images_dir, f"{safe_title}_{timestamp}")
            os.makedirs(product_img_dir, exist_ok=True)
            
            downloaded_paths = []
            for i, img_url in enumerate(result['images']):
                ext = img_url.split('.')[-1].split('?')[0]
                if ext.lower() not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    ext = "jpg"
                
                filename = f"{i+1}.{ext}"
                save_path = os.path.join(product_img_dir, filename)
                
                if download_image(img_url, save_path):
                    downloaded_paths.append(save_path)
            
            result["images"] = downloaded_paths

        except Exception as e:
            print(f"An error occurred: {e}")
            try:
                page.screenshot(path="output/debug_exception.png")
            except:
                pass

        finally:
            browser.close()
            
    return result

# Alias for compatibility
scrape_coupang = scrape_product

if __name__ == "__main__":
    url = input("Enter Coupang URL: ")
    data = scrape_coupang(url)
    print(data)
