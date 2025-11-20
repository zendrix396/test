import requests
import json
from bs4 import BeautifulSoup

def scrape():
    base_url = "https://kiayaaccessories.com/products.json"
    scraped_data = []
    page = 1
    
    print("Scraping Kiaya Accessories...")
    while True:
        try:
            response = requests.get(f"{base_url}?page={page}", timeout=10)
            response.raise_for_status()
            products = response.json().get("products", [])

            if not products:
                break

            for product in products:
                price = product.get("variants")[0].get("price") if product.get("variants") else None
                description = BeautifulSoup(product.get("body_html", ""), "html.parser").get_text(separator='\n').strip()
                
                scraped_data.append({
                    "name": product.get("title"),
                    "description": description,
                    "price": price,
                    "image_urls": [img.get("src") for img in product.get("images", [])],
                    "tags": product.get("tags", []),
                    "source_site": "kiayaaccessories",
                    "source_url": f"https://kiayaaccessories.com/products/{product.get('handle')}"
                })
            
            print(f"  - Scraped page {page}...")
            page += 1
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"  - Error on page {page}: {e}. Stopping.")
            break
    
    return scraped_data
