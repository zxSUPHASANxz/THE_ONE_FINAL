"""
Honda Motorcycle Scraper - Auto scrape all models with specifications
Scrapes from https://www.thaihonda.co.th/honda/motorcycle
"""
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_one.settings')
import django
django.setup()

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import google.generativeai as genai
import logging
from the_one.logging_config import setup_logging

logger = logging.getLogger(__name__)

from chatbot.models import MotorcycleKnowledge

# Gemini API configuration (from environment)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.critical("GEMINI_API_KEY not set. Add it to your .env or environment variables.")
    sys.exit(1)
genai.configure(api_key=GEMINI_API_KEY)

def setup_driver(headless=False):
    """Setup Chrome WebDriver"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def generate_embedding(text):
    """Generate embedding using Gemini API"""
    try:
        model = 'models/text-embedding-004'
        result = genai.embed_content(
            model=model,
            content=text,
            task_type="retrieval_document"
        )
        return result.get('embedding')
    except Exception:
        logger.exception("Error generating embedding")
        return None

def get_all_motorcycle_links(driver):
    """Get all motorcycle detail page links from main page"""
    logger.info("🔍 Fetching all motorcycle links...")
    base_url = "https://www.thaihonda.co.th/honda/motorcycle"
    
    # Categories to explore
    categories = [
        'automatic', 'sport', 'onoff', 'bobber', 'scrambler', 
        'neo-sport-cafe', 'family', 'helmet', 'accessories', 'h2c'
    ]
    
    all_links = set()  # Use set to avoid duplicates
    category_names = set(categories)  # For faster lookup
    
    for category in categories:
        category_url = f"{base_url}/{category}"
        logger.info("  🔍 Exploring category: %s", category)
        
        try:
            driver.get(category_url)
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find all product links
            links = soup.find_all('a', href=True)
            count = 0
            
            for link in links:
                href = link.get('href', '')
                
                # Check if it's a motorcycle link
                if '/honda/motorcycle/' in href:
                    # Count slashes to determine depth
                    slash_count = href.count('/')
                    
                    # Product pages have exactly 5 slashes (e.g., /honda/motorcycle/automatic/adv350-2025)
                    if slash_count == 5:
                        full_url = href if href.startswith('http') else f"https://www.thaihonda.co.th{href}"
                        
                        # Extract the last part (model slug)
                        parts = href.strip('/').split('/')
                        if len(parts) >= 4:
                            model_slug = parts[-1]
                            
                            # Exclude if the model slug is actually a category name
                            if model_slug not in category_names:
                                all_links.add(full_url)
                                count += 1
            
            logger.info("     Found %d models in %s", count, category)
        
        except Exception:
            logger.exception("  ⚠️ Error exploring %s", category)
    
    all_links = list(all_links)
    logger.info("✅ Found %d unique motorcycle models", len(all_links))
    return all_links

def scrape_motorcycle_detail(driver, url):
    """Scrape detailed information from a motorcycle page"""
    logger.info("\n📄 Scraping: %s", url)
    
    try:
        driver.get(url)
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Extract model name - try multiple selectors
        model_name = "Unknown"
        
        # Try to find model name from various locations
        for selector in ['h1', 'h2', '.n_name', '.model-name', 'title']:
            elem = soup.find(selector)
            if elem:
                text = elem.get_text(strip=True)
                if text and text != "Unknown" and len(text) > 3:
                    model_name = text.split('|')[0].strip()
                    break
        
        # Extract price - look for THB
        price = "N/A"
        price_patterns = [
            soup.find('div', class_='n_price'),
            soup.find(string=lambda text: 'THB' in str(text) if text else False),
            soup.find('div', class_='price'),
            soup.find('span', class_='price')
        ]
        
        for pattern in price_patterns:
            if pattern:
                price_text = pattern.get_text(strip=True) if hasattr(pattern, 'get_text') else str(pattern).strip()
                if 'THB' in price_text or '฿' in price_text or 'บาท' in price_text:
                    price = price_text
                    break
        
        # Extract specifications from ul.n_sp_data
        specifications = {}
        
        # Try to find specifications list
        sp_data = soup.find('ul', class_='n_sp_data')
        
        if sp_data:
            items = sp_data.find_all('li')
            logger.info("   Found %d specification items", len(items))
            
            for item in items:
                name_elem = item.find('div', class_='n_name')
                value_elem = item.find('div', class_='n_value')
                
                if name_elem and value_elem:
                    name = name_elem.get_text(strip=True)
                    value = value_elem.get_text(strip=True)
                    if name and value:
                        specifications[name] = value
        else:
            logger.warning("   ⚠️ No specification list found")
        
        # Get colors
        colors = []
        color_elements = soup.find_all('div', class_='n_color_item') or soup.find_all('li', class_='color')
        for color_elem in color_elements:
            color_text = color_elem.get_text(strip=True)
            if color_text and color_text not in colors:
                colors.append(color_text)
        
        # If still no data, skip this URL
        if model_name == "Unknown" and not specifications:
            logger.warning("   ⚠️ No valid data found, skipping...")
            return None
        
        bike_data = {
            'brand': 'Honda',
            'model': model_name,
            'url': url,
            'price': price,
            'specifications': specifications,
            'colors': colors,
            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        logger.info("✅ Scraped: %s", model_name)
        logger.info("   Price: %s", price)
        logger.info("   Specs: %d items", len(specifications))
        logger.info("   Colors: %d options", len(colors))
        
        return bike_data
        
    except Exception:
        logger.exception("❌ Error scraping %s", url)
        return None

def save_to_database(bike_data):
    """Save motorcycle data to database with embedding"""
    try:
        # Create text for embedding
        specs_text = "\n".join([f"{k}: {v}" for k, v in bike_data['specifications'].items()])
        colors_text = ", ".join(bike_data['colors']) if bike_data['colors'] else "ไม่ระบุสี"
        
        full_text = f"""รุ่น: {bike_data['model']}
ยี่ห้อ: {bike_data['brand']}
ราคา: {bike_data['price']}
สี: {colors_text}

ข้อมูลจำเพาะ:
{specs_text}

URL: {bike_data['url']}"""
        
        # Generate embedding
        logger.info("   🔄 Generating embedding...")
        embedding = generate_embedding(full_text)
        
        if not embedding:
            logger.warning("   ⚠️ Could not generate embedding, skipping database save")
            return None
        
        # Save to database
        motorcycle = MotorcycleKnowledge.objects.create(
            brand=bike_data['brand'],
            model=bike_data['model'],
            source_url=bike_data['url'],
            symptom=f"ข้อมูล {bike_data['model']}\nราคา: {bike_data['price']}\nสี: {colors_text}",
            solution=specs_text,
            scraped_data=bike_data['specifications'],
            embedding=embedding
        )
        
        logger.info("   ✅ Saved to database (ID: %s)", motorcycle.id)
        
        # Return data with embedding for JSON export
        bike_data_with_embedding = bike_data.copy()
        bike_data_with_embedding['embedding'] = embedding
        bike_data_with_embedding['database_id'] = motorcycle.id
        
        return bike_data_with_embedding
        
    except Exception:
        logger.exception("   ❌ Error saving to database")
        return None

def save_to_json(motorcycles_raw, motorcycles_with_embeddings):
    """Save scraped data to JSON files"""
    output_dir = Path(__file__).parent
    
    # Save raw data
    raw_file = output_dir / 'honda_motorcycles.json'
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(motorcycles_raw, f, ensure_ascii=False, indent=2)
    logger.info("\n✅ Saved raw data: %s (%d motorcycles)", raw_file, len(motorcycles_raw))
    
    # Save data with embeddings
    embedded_file = output_dir / 'honda_motorcycles_with_embeddings.json'
    with open(embedded_file, 'w', encoding='utf-8') as f:
        json.dump(motorcycles_with_embeddings, f, ensure_ascii=False, indent=2)
    logger.info("✅ Saved data with embeddings: %s (%d motorcycles)", embedded_file, len(motorcycles_with_embeddings))

def main():
    logger.info("=" * 60)
    logger.info("Honda Motorcycle Auto Scraper")
    logger.info("=" * 60)
    
    driver = setup_driver(headless=False)
    
    try:
        # Get all motorcycle links
        links = get_all_motorcycle_links(driver)
        
        if not links:
            logger.error("❌ No motorcycle links found!")
            return
        
        motorcycles_raw = []
        motorcycles_with_embeddings = []
        
        # Scrape each motorcycle
        for i, link in enumerate(links, 1):
            logger.info("\n[%d/%d] Processing: %s", i, len(links), link)
            
            bike_data = scrape_motorcycle_detail(driver, link)
            
            if bike_data:
                motorcycles_raw.append(bike_data)
                
                # Save to database and get embedding
                bike_with_embedding = save_to_database(bike_data)
                if bike_with_embedding:
                    motorcycles_with_embeddings.append(bike_with_embedding)
            
            # Small delay between requests
            time.sleep(1)
        
        # Save all data to JSON
        save_to_json(motorcycles_raw, motorcycles_with_embeddings)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ SCRAPING COMPLETED!")
        logger.info("📊 Total motorcycles scraped: %d", len(motorcycles_raw))
        logger.info("💾 Saved to database: %d", len(motorcycles_with_embeddings))
        logger.info("📁 JSON files created: 2 files")
        logger.info("=" * 60)
        
    finally:
        driver.quit()
        logger.info("\n🔒 Browser closed")

if __name__ == "__main__":
    setup_logging()
    main()
