import os

import math

def calculate_shipping_sg(weight_kg):
    """
    Calculates Shipping Cost for Singapore (Shopee KR Logistics).
    Based on 'shipping_rates' sheet analysis.
    """
    weight_g = weight_kg * 1000
    price_sgd = 0
    
    if weight_g <= 50:
        price_sgd = 0.4
    elif weight_g <= 1000:
        # Base 0.4 for first 50g
        # Add 0.08 for every additional 10g (or part thereof)
        additional_weight = weight_g - 50
        blocks = math.ceil(additional_weight / 10)
        price_sgd = 0.4 + (blocks * 0.08)
    else:
        # Based on 1000g = 8.0, then +0.7 per 100g
        # 1010g -> 8.7
        base_price = 8.0 # Price for 1000g approx? actually table says 1000g is 8.0 (calculated 0.4 + 95*0.08 = 7.6 + 0.4 = 8.0)
        additional_weight = weight_g - 1000
        blocks = math.ceil(additional_weight / 100)
        price_sgd = 8.0 + (blocks * 0.7)
        
    return price_sgd

def calculate_shopee_price(coupang_price, weight_str):
    """
    Calculates Shopee price based on extracted formula from Excel.
    
    Formula derived:
    Selling Price (SGD) = (Total Cost KRW * Margin Multiplier) / (Exchange Rate * (1 - Fet Fees))
    
    Constants:
    - Exchange Rate: 1143 (SGD -> KRW)
    - Fees: 19.35% (Shopee Fee + Transaction Fee + Shop Voucher)
    - Margin: 30% Markup (x1.3)
    """
    
    # 1. Parse weight
    weight_kg = 0.5 # Default
    if weight_str:
        try:
            clean_w = weight_str.lower().replace(" ", "").replace("약", "")
            if "kg" in clean_w:
                weight_kg = float(clean_w.replace("kg", ""))
            elif "g" in clean_w:
                weight_kg = float(clean_w.replace("g", "")) / 1000
            elif "ml" in clean_w:
                 # Rough approximation for ml -> g (assuming water density)
                 weight_kg = float(clean_w.replace("ml", "")) / 1000
                 
        except:
            print(f"Warning: Could not parse weight '{weight_str}', using default 0.5kg")
    
    # Constants
    EXCHANGE_RATE = 1143
    FEES_RATE = 0.1935 # 13.35% + 3% + 3%
    MARGIN_MULTIPLIER = 1.3 # 30% Markup
    DISCOUNT_RATE = 0.3 # 30% Listing Discount
    
    # 2. Calculate Shipping (in SGD)
    shipping_sgd = calculate_shipping_sg(weight_kg)
    shipping_krw = shipping_sgd * EXCHANGE_RATE
    
    # 3. Total Cost
    total_cost_krw = coupang_price + shipping_krw
    
    # 4. Calculate Selling Price (SGD)
    # Target: Cost * 1.3 / (Exchange * (1-Fees))
    selling_price_sgd = (total_cost_krw * MARGIN_MULTIPLIER) / (EXCHANGE_RATE * (1 - FEES_RATE))
    
    # 5. Calculate Listing Price (Before Discount)
    listing_price_sgd = selling_price_sgd / (1 - DISCOUNT_RATE)
    
    return round(listing_price_sgd, 2)

import google.generativeai as genai
from PIL import Image

def generate_english_description(title, image_paths, use_ai=False, api_key=None, user_prompt=""):
    """
    Generates English description and title using Gemini API (Legacy SDK).
    """
    if use_ai and api_key:
        try:
            import time
            from datetime import datetime
            
            # 0. Initial Throttle
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Throttle: Waiting 10s...")
            time.sleep(10)
            
            if api_key:
                 masked_key = api_key[:5] + "*" * (len(api_key)-5)
                 print(f"   -> [DEBUG] Configuring AI with Key: {masked_key}")
            
            genai.configure(api_key=api_key)
            
            # Model Pool - DOUBLE DOWN ON 2.0 (Retry Strategy)
            model_names = [
                'gemini-2.0-flash',        # Try 1
                'gemini-2.0-flash',        # Try 2 (After wait)
                'gemini-flash-latest',     # Backup
                'gemini-2.0-flash-lite'    # Lite
            ]
            
            system_instruction = f"""
            You are a professional e-commerce copywriter for 'Seoul Attic'.
            Your goal is to write a high-converting product description following the template below exactly.

            **REQUIRED OUTPUT FORMAT:**
            💝 [EVENT] Follow our shop Now & Get a 5% Discount Coupon 💝

            🎁 Item: [Made in Korea] {{Translated Product Title}}

            🤍 Item: {{Exact Product Name}}

            🤍 Description
            {{Write a concise description. Maximum 5 lines. Focus on benefits.}}

            🔍 Highlights 
            ✅ {{Feature 1}} 
            ✅ {{Feature 2}} 
            ✅ {{Feature 3}} 
            ✅ {{Feature 4}} 
            ✅ {{Feature 5}} 
            ✅ {{Feature 6}}

            🔵 Specifications 
            📍 Material: {{Material}} 
            📍 Size: {{Size}} 
            📍 Components: {{Components}} 
            📍 Origin: Korea 🇰🇷

            🏠✨ Seoul Attic Tip 🏠✨ 
            {{Tip 1: Practical usage tip}}
            {{Tip 2: Storage or care tip}}

            😊 SeoulAttic Shop Promise 😊 
            💛 All products are shipped directly from Korea 🇰🇷 
            💛 Fast and reliable delivery 
            💛 Every order is carefully packed and video-recorded for your safety 
            💛 We sell only genuine products — please report any counterfeits immediately 
            💛 If you have any product requests, please feel free to contact us!

            Thank you for choosing SeoulAttic Market. Please don’t forget to leave a 💗 rating & review 💗

            **CRITICAL RULES:**
            1. **NO DOUBLE ASTERISKS (**)**: Do not use bold markdown syntax. Pure text only.
            2. **NO COLONS (:) IN TITLE**: The '🎁 Item' line should not have extra colons or dashes.
            3. **SHORT DESCRIPTION**: Keep '🤍 Description' under 5 lines.
            4. **ENGLISH ONLY**: Translate everything.
            5. **WEIGHT ESTIMATION**: At the very bottom, add this exact line: `[WEIGHT]: 0.5` (Replace 0.5 with your best guess in kg based on valid image/title info. Numbers only).
            """

            content_parts = [
                system_instruction, 
                f"Product Title (KR): {title}"
            ]
            
            if user_prompt:
                content_parts.append(f"\n[USER INSTRUCTION]: {user_prompt}")
            
            # OPTIMIZATION: Resize images to prevent Quota Explosion
            # Sending full-res images kills the token limit instantly on Free Tier.
            print("   -> [DEBUG] Sending 1 Optimized Image to balance Quality/Quota...")
            for img_path in image_paths[:1]:
                if os.path.exists(img_path):
                    try:
                        img = Image.open(img_path)
                        # Resize if too big (Max 1024px)
                        if img.width > 1024 or img.height > 1024:
                            img.thumbnail((1024, 1024))
                        content_parts.append(img)
                    except Exception as e:
                        print(f"Error loading image {img_path}: {e}")

            # Legacy SDK Config - TEXT MODE (Better for Gold Standard Formatting)
            generation_config = {
                "response_mime_type": "text/plain" 
            }

            # Retry Loop with PERSISTENCE (Quality First)
            max_retries = 20
            response = None
            
            for attempt in range(max_retries):
                try:
                    current_model_name = model_names[attempt % 3]
                    model = genai.GenerativeModel(
                        model_name=current_model_name,
                        generation_config=generation_config
                    )
                    
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Attempt {attempt+1}/{max_retries} using {current_model_name} (Legacy SDK)...")
                    
                    response = model.generate_content(content_parts)
                    break 
                except Exception as api_error:
                    error_str = str(api_error)
                    print(f"   -> Error: {error_str[:100]}...")
                    
                    if "429" in error_str or "quota" in error_str.lower() or "not found" in error_str.lower():
                        if "404" in error_str or "not found" in error_str.lower():
                             print(f"   -> Model {current_model_name} not found. Switching...")
                             continue

                        # SMART RETRY STRATEGY for GEMINI 2.0 (User Priority)
                        if "2.0" in current_model_name:
                            # If it's the first time 2.0 fails, Google usually wants ~20s wait.
                            # We will wait ONCE and retry 2.0 to satisfy user preference.
                            if attempt == 0:
                                print(f"   -> ⏳ Gemini 2.0 Rate Limit. Pausing 65s to GUARANTEE 2.0 quota reset...")
                                time.sleep(65)
                                continue # Retry loop will pick 2.0 again
                            else:
                                print(f"   -> ⚠️ Gemini 2.0 Failed again. Switching to Backup Model...")
                                time.sleep(5)
                        else:
                            # For 1.5 (Backup), standard backoff
                            wait_time = min(30 * (attempt + 1), 120)
                            print(f"   -> ⚠️ Quota hit. Waiting {wait_time}s to preserve QUALITY...")
                            time.sleep(wait_time)
                    else:
                        print(f"   -> API Error. Retrying in 10s...")
                        time.sleep(10)

            if not response:
                raise Exception("Failed after multiple attempts.")

            # Parse Response (Text Mode)
            text = response.text.strip()
            
            # Extract Title and Description from the Gold Standard Text
            final_title = f"[Made in Korea] {title}" # Default
            final_desc = text
            # Default weight if extraction fails
            final_weight = 0.5 

            # Attempt to extract title from "🎁 Item: ..." line
            lines = text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # 1. Title Extraction
                if "🎁 Item:" in line or "Item:" in line:
                    if "🎁" in line:
                         parts = line.split("Item:")
                         if len(parts) > 1:
                            final_title = parts[1].strip()
                            final_title = final_title.replace("**", "").replace(":", "")
                
                # 2. Weight Extraction
                if "[WEIGHT]:" in line:
                    try:
                        w_str = line.split(":")[1].replace("kg","").strip()
                        final_weight = float(w_str)
                    except:
                        pass
                    continue # Skip this line in description
                
                cleaned_lines.append(line)
                
            # Use the Cleaned Text as Description
            final_desc = "\n".join(cleaned_lines).strip()
            
            # --- Text Cleaning (Safety Net) ---
            final_desc = final_desc.replace("```json", "").replace("```", "")
            final_desc = final_desc.replace("**", "") # Enforce cleaning
            
            # Note: No hardcoded header/footer appending anymore
            full_description = final_desc

            return {
                "title": final_title,
                "description": full_description,
                "weight_kg": final_weight
            }

        except Exception as e:
            error_msg = f"⚠️ AI Generation Error: {str(e)}"
            print(error_msg)
            return {
                "title": f"[Error] {title[:20]}...",
                "description": f"Error: {e}",
                "weight_kg": 0.5
            }

def select_best_category(title, category_list, api_key):
    """
    Selects the best matching category from the list using Gemini.
    """
    if not category_list:
        return ""
        
    try:
        genai.configure(api_key=api_key)
        # Use verified stable alias
        model = genai.GenerativeModel('gemini-flash-latest')
        
        # Prepare list string
        cat_str = "\n".join(category_list)
        
        prompt = f"""
        Select the best category for this product title from the provided list.
        Product Title: {title}
        
        Category List:
        {cat_str}
        
        Return ONLY the EXACT string from the list. Nothing else.
        If unsure, pick the one containing "Others".
        """
        
        response = None
        for attempt in range(3):
            try:
                response = model.generate_content(prompt)
                break
            except Exception as e:
                print(f"   -> Category AI Error (Attempt {attempt+1}): {e}")
                time.sleep(5) # Simple backoff
        
        if not response:
             return category_list[0] if category_list else ""

        text = response.text.strip()
        
        # Validation: check if text is in list
        for cat in category_list:
            if cat in text: 
                return cat
                
        # Fallback to first or "Others"
        for cat in category_list:
            if "Others" in cat:
                return cat
        return category_list[0]
        
    except Exception as e:
        print(f"Category Selection Error: {e}")
        return category_list[0] if category_list else ""
