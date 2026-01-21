import google.generativeai as genai
import os
import time
from PIL import Image

# Use known key
api_key = 'AIzaSyA6i8VOO3H-cDaii1He6aWOpyYLl5GzsXk'
genai.configure(api_key=api_key)

def test_model(model_name, content, label):
    print(f"\n--- Testing {model_name} [{label}] ---")
    try:
        model = genai.GenerativeModel(model_name)
        start = time.time()
        response = model.generate_content(content)
        elapsed = time.time() - start
        print(f"✅ SUCCESS ({elapsed:.2f}s)")
        print(f"Response: {response.text[:50]}...")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

# 1. Text Only Test
print("=== TEST 1: Text Only ===")
test_model('gemini-2.0-flash', "Hello, are you working?", "Text Only")

# 2. Text + 1 Dummy Image (Small)
print("\n=== TEST 2: Text + 1 Small Image ===")
# Create dummy image
dummy_img = Image.new('RGB', (100, 100), color = 'red')
test_model('gemini-2.0-flash', ["Describe this image", dummy_img], "1 Small Image")

# 3. Text + 3 Dummy Images
print("\n=== TEST 3: Text + 3 Small Images ===")
test_model('gemini-2.0-flash', ["Describe these", dummy_img, dummy_img, dummy_img], "3 Small Images")

print("\n=== Diagnosis Complete ===")
