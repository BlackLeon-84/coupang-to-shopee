import google.generativeai as genai
import os

# Use the key from previous context
os.environ["GEMINI_API_KEY"] = 'AIzaSyA6i8VOO3H-cDaii1He6aWOpyYLl5GzsXk'
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("No API KEY found.")
else:
    genai.configure(api_key=api_key)
    print("Listing available models (Legacy SDK)...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")
