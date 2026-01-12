"""
Yamaha Thailand Motorcycle Scraper
===================================
สกัดข้อมูลรถจักรยานยนต์ Yamaha ทุกรุ่นจาก yamaha-motor.co.th
- ชื่อรุ่น
- ราคา
- Specifications

รันด้วย: python yamaha_scraper.py
"""
import time
import json
import re
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# =====================
# Configuration
# =====================

BASE_URL = "https://www.yamaha-motor.co.th"
OUTPUT_DIR = Path(__file__).parent.parent / "database"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Known model slugs และ URL paths
YAMAHA_MODELS = [
    # 2026
    {"slug": "nmax-2026", "name": "NMAX [2026]"},
    # 2025
    {"slug": "all-new-aerox-2025", "name": "ALL NEW AEROX [2025]"},
    {"slug": "pg-1-2025", "name": "PG-1 [2025]"},
    {"slug": "grand-filano-hybrid-2025", "name": "GRAND FILANO HYBRID [2025]"},
    {"slug": "finn-2025", "name": "FINN [2025]"},
    {"slug": "r15-2025", "name": "R15 / R15M [2025]"},
    {"slug": "exciter-155-2025", "name": "EXCITER 155 [2025]"},
    {"slug": "r3-2025", "name": "R3 [2025]"},
    {"slug": "fazzio-2025", "name": "FAZZIO [2025]"},
    {"slug": "all-new-nmax-2025", "name": "ALL NEW NMAX [2025]"},
    {"slug": "xmax-2025", "name": "XMAX [2025]"},
    # 2024
    {"slug": "xsr155-2024", "name": "XSR155 [2024]"},
    {"slug": "mt-03-2024", "name": "MT-03 [2024]"},
    {"slug": "fazzio-x-fila", "name": "FAZZIO X FILA [LIMITED EDITION]"},
    {"slug": "fino-final-edition-2024", "name": "FINO FINAL EDITION [2024]"},
    {"slug": "mt-15-2024", "name": "MT-15 [2024]"},
    {"slug": "xmax-tech-max-2024", "name": "XMAX TECH MAX [2024]"},
    # 2023
    {"slug": "gt125-2023", "name": "GT125 [2023]"},
    {"slug": "qbix-2023", "name": "QBIX [2023]"},
    # 2022
    {"slug": "wr155r-2022", "name": "WR155R [2022]"},
]


# =====================
# Selenium Setup
# =====================

def init_driver():
    """Initialize Chrome WebDriver with headless mode"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text.strip())


def parse_price(text: str) -> tuple[Optional[str], Optional[int]]:
    """Extract price from text"""
    if not text:
        return None, None
    
    # Find price pattern like "98,500 - 113,500 บาท" or "85,900 บาท"
    match = re.search(r'([\d,]+(?:\s*-\s*[\d,]+)?)\s*(?:บาท|THB)?', text)
    if match:
        price_text = f"{match.group(1)} บาท"
        # Get the first number for numeric value
        nums = re.findall(r'\d+', match.group(1).replace(',', ''))
        price_numeric = int(nums[0]) if nums else None
        return price_text, price_numeric
    return None, None


# =====================
# Scraping Functions
# =====================

def scrape_model_overview(driver, model_info: Dict) -> Optional[Dict]:
    """Scrape overview page for a model"""
    slug = model_info["slug"]
    overview_url = f"{BASE_URL}/commuter/{slug}/overview"
    spec_url = f"{BASE_URL}/commuter/{slug}/specification"
    
    print(f"  📄 Fetching: {overview_url}")
    
    try:
        driver.get(overview_url)
        time.sleep(2)  # Wait for page load
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        data = {
            "brand": "Yamaha",
            "name": model_info["name"],
            "url": overview_url,
            "spec_url": spec_url,
            "category": "มอเตอร์ไซค์",
            "scraped_at": datetime.now().isoformat()
        }
        
        # Extract price from overview page
        price_element = soup.select_one(".price_center, .price, [class*='price']")
        if price_element:
            price_text = clean_text(price_element.get_text())
            data["price"], data["price_numeric"] = parse_price(price_text)
        
        # Try to get specs from specification page
        print(f"  � Fetching specs: {spec_url}")
        driver.get(spec_url)
        time.sleep(2)
        
        spec_soup = BeautifulSoup(driver.page_source, "html.parser")
        data["specifications"] = extract_specifications(spec_soup)
        
        return data
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def extract_specifications(soup: BeautifulSoup) -> Dict[str, str]:
    """Extract specifications from the specification page"""
    specs = {}
    
    # Method 1: Look for accordion panels (Yamaha uses panel-group)
    panels = soup.select(".panel-group .panel, .accordion, [class*='spec']")
    
    for panel in panels:
        # Get section title
        header = panel.select_one(".panel-heading, .panel-title, h3, h4")
        section_title = clean_text(header.get_text()) if header else ""
        
        # Get table or list content
        tables = panel.select("table")
        for table in tables:
            for row in table.select("tr"):
                cols = row.select("td, th")
                if len(cols) >= 2:
                    key = clean_text(cols[0].get_text())
                    value = clean_text(cols[1].get_text())
                    if key and value and len(key) < 100:
                        # Add section context if available
                        if section_title and section_title not in key:
                            full_key = f"{key}"
                        else:
                            full_key = key
                        specs[full_key] = value
    
    # Method 2: Look for div-based key-value pairs
    if len(specs) < 3:
        spec_containers = soup.select(".detail, .spec-detail, [class*='detail']")
        for container in spec_containers:
            rows = container.select(".row, div > div")
            for row in rows:
                text = clean_text(row.get_text())
                # Try to split by common separators
                if ':' in text:
                    parts = text.split(':', 1)
                    if len(parts) == 2:
                        key, value = parts
                        if key and value and len(key) < 80:
                            specs[clean_text(key)] = clean_text(value)
    
    # Method 3: Parse accordion text blocks
    if len(specs) < 3:
        body_sections = soup.select(".panel-body, .accordion-body")
        for body in body_sections:
            lines = [clean_text(x) for x in body.stripped_strings]
            # Pair consecutive lines as key-value
            for i in range(0, len(lines) - 1, 2):
                key = lines[i]
                value = lines[i + 1] if i + 1 < len(lines) else ""
                if key and value and len(key) < 80 and len(value) < 200:
                    specs[key] = value
    
    return specs


def scrape_all_yamaha():
    """Main scraping function"""
    print("=" * 60)
    print("🏍️ Yamaha Thailand Motorcycle Scraper")
    print("=" * 60)
    
    driver = init_driver()
    all_models = []
    errors = []
    
    try:
        total = len(YAMAHA_MODELS)
        
        for idx, model_info in enumerate(YAMAHA_MODELS, 1):
            print(f"\n[{idx}/{total}] {model_info['name']}")
            
            try:
                model_data = scrape_model_overview(driver, model_info)
                if model_data:
                    all_models.append(model_data)
                    print(f"  ✅ Done - Price: {model_data.get('price', 'N/A')}, Specs: {len(model_data.get('specifications', {}))}")
                
                # Random delay to avoid blocking
                time.sleep(random.uniform(1.5, 3.0))
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                errors.append({"model": model_info["name"], "error": str(e)})
                
    finally:
        driver.quit()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Main JSON file
    output_file = OUTPUT_DIR / f"yamaha_all_models_{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "source": "yamaha-motor.co.th",
                "scraped_at": datetime.now().isoformat(),
                "total_count": len(all_models),
                "error_count": len(errors)
            },
            "motorcycles": all_models
        }, f, ensure_ascii=False, indent=2)
    
    # Latest file (always same name for easy access)
    latest_file = OUTPUT_DIR / "yamaha_all_models_latest.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "source": "yamaha-motor.co.th",
                "scraped_at": datetime.now().isoformat(),
                "total_count": len(all_models),
                "error_count": len(errors)
            },
            "motorcycles": all_models
        }, f, ensure_ascii=False, indent=2)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SCRAPING SUMMARY")
    print("=" * 60)
    print(f"✅ Total scraped: {len(all_models)}")
    print(f"❌ Errors: {len(errors)}")
    print(f"📁 Saved to: {output_file}")
    print(f"📁 Latest: {latest_file}")
    print("=" * 60)
    
    return all_models


if __name__ == "__main__":
    scrape_all_yamaha()
