from scraper import scrape_product
import os

# Create absolute path for User's Daiso HTML
# Use raw string for Korean characters and backslashes
file_path = os.path.abspath(r"상품 폴더/3/본셉 비타씨 동결 건조 더블샷 앰플 키트 - 다이소몰.html")
url = f"file:///{file_path}"

print(f"Testing URL: {url}")
data = scrape_product(url)

print("\n--- RESULTS ---")
print(f"Title: {data['title']}")
print(f"Price: {data['price']}")
print(f"Images Found: {len(data['images'])}")
for img in data['images']:
    print(f" - {img}")
