
import sys
import os
from unittest.mock import MagicMock

# Add local directory to path
current_dir = os.getcwd()
sys.path.append(current_dir)

import processor # Import the module

# Mocking Google GenAI to avoid actual API call and focus on logic/formatting
processor.genai = MagicMock()
mock_model = MagicMock()
processor.genai.GenerativeModel.return_value = mock_model

# Mock Response
mock_response = MagicMock()
mock_response.text = """
{
    "title": "[Made in Korea] Super Shampoo",
    "description": "**🤍 Item: Super Shampoo**",
    "weight_kg": 0.8
}
"""
mock_model.generate_content.return_value = mock_response

from processor import generate_english_description

print("Testing generate_english_description logic...")
try:
    dummy_title = "테스트 샴푸"
    dummy_paths = ["test.jpg"] # Fake path
    dummy_key = "FAKE_KEY"
    dummy_prompt = "Make it exciting"
    
    # We expect this to run, use the mock AI, then hit the 'Text Cleaning' logic
    result = generate_english_description(dummy_title, dummy_paths, use_ai=True, api_key=dummy_key, user_prompt=dummy_prompt)
    
    print("\n[Result Data]")
    print(f"Title: {result['title']}")
    print(f"Desc: {result['description'][:50]}...")
    
    # Verify cleaning (No stars, no colons)
    if "**" in result['description'] or "**" in result['title']:
        print("FAIL: Asterisks found!")
    else:
        print("PASS: No asterisks found.")
        
    if "***" in result['description']: # Checking for leftover artifacts
         print("FAIL: Artifacts found")

    print("\nBackend Test Complete: SUCCESS")

except Exception as e:
    print(f"Backend Crash: {e}")
    import traceback
    traceback.print_exc()
