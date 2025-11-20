import requests
from bs4 import BeautifulSoup
import re

def clean_price(price_string):
    if not price_string: return None
    cleaned = re.sub(r'[^\d.]', '', price_string)
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None

def scrape_product_info(url, session):
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    name_tag = soup.find('h1', class_='product_title')
    if not name_tag: return None

    price_tag = soup.find('p', class_='price')
    price = None
    if price_tag:
        sale_price_tag = price_tag.find('ins')
        price = clean_price(sale_price_tag.text if sale_price_tag else price_tag.text.split('MRP')[0].strip())

    description = ""
    desc_container = soup.find('div', id='tab-description')
    if desc_container:
        desc_ul = desc_container.find('ul')
        if desc_ul:
            description = "\n".join([item.text.strip() for item in desc_ul.find_all('li')])

    tags = []
    for script in soup.find_all('script'):
        if script.string and 'pysWooProductData' in script.string:
            tags_match = re.search(r'"tags":\s*"(.*?)"', script.string)
            if tags_match:
                tags = [tag.strip() for tag in tags_match.group(1).split(',') if tag.strip()]
                break
    
    return {
        "name": name_tag.text.strip(),
        "description": description,
        "price": price,
        "image_urls": [fig['data-src'] for fig in soup.select('div.woocommerce-product-gallery figure[data-src]')],
        "tags": tags,
        "source_site": "comicsense",
        "source_url": url
    }

def scrape():
    sitemap_url = "https://www.comicsense.store/wp-sitemap-posts-product-1.xml"
    scraped_data = []
    
    print("Scraping Comicsense...")
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    try:
        response = session.get(sitemap_url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  - Could not fetch sitemap: {e}")
        return []

    sitemap_soup = BeautifulSoup(response.content, 'xml')
    product_urls = [loc.text for loc in sitemap_soup.find_all('loc')]
    
    for i, url in enumerate(product_urls):
        print(f"  - Scraping URL {i+1}/{len(product_urls)}: {url[:50]}...")
        product_info = scrape_product_info(url, session)
        if product_info:
            scraped_data.append(product_info)
    
    return scraped_data
