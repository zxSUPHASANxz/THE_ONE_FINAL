"""
Yamaha BigBike Thailand Scraper
================================
สกัดข้อมูลรถบิ๊กไบค์ Yamaha ทุกรุ่นจาก yamaha-motor.co.th/bigbike

รันด้วย: python yamaha_bigbike_scraper.py
"""
import json
import re
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from the_one.logging_config import setup_logging


# =========================
# Configuration
# =========================

BASE_URL = "https://www.yamaha-motor.co.th"
OUTPUT_DIR = Path(__file__).parent.parent / "database"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# BigBike models จากหน้า model page
BIGBIKE_MODELS = [
    {"slug": "tenere-700-2025", "name": "Ténéré 700 2025", "price": "459,000"},
    {"slug": "r9", "name": "R9", "price": "495,000"},
    {"slug": "mt07-2020", "name": "MT07 2025", "price": "299,000"},
    {"slug": "mt07y-amt2025", "name": "MT07Y-AMT2025", "price": "305,000"},
    {"slug": "new-tmax-560-2025", "name": "TMAX 560", "price": "539,000"},
    {"slug": "new-tmax-tech-max-2025", "name": "TMAX TECH MAX", "price": "569,000"},
    {"slug": "r1m-2022", "name": "R1M", "price": "1,199,000"},
    {"slug": "r1", "name": "R1", "price": "899,000"},
    {"slug": "r7-2025", "name": "R7 2025", "price": "339,000"},
    {"slug": "2024-r7", "name": "R7 2024", "price": "339,000"},
    {"slug": "tracer-9gt-plus", "name": "TRACER 9GT+", "price": "619,000"},
    {"slug": "tracer-9gt", "name": "TRACER 9GT", "price": "569,000"},
    {"slug": "tenere-700-tft", "name": "Ténéré 700 TFT", "price": "479,000"},
    {"slug": "xsr900", "name": "XSR900", "price": "479,000"},
    {"slug": "mt-09-y-amt", "name": "MT-09 Y-AMT", "price": "519,000"},
    {"slug": "xsr700", "name": "XSR700", "price": "349,000"},
    {"slug": "2024-mt-09-sp", "name": "MT-09 SP", "price": "489,000"},
    {"slug": "2024-mt-09", "name": "MT-09", "price": "447,000"},
    {"slug": "mt07", "name": "MT-07", "price": "305,000"},
    {"slug": "sr400-2025", "name": "SR400 2025", "price": "298,000"},
    {"slug": "sr400-2023", "name": "SR400 2023", "price": "295,000"},
]


# =========================
# Selenium Setup
# =========================

def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


def clean(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def price_to_int(text: str) -> Optional[int]:
    if not text:
        return None
    nums = re.sub(r"[^\d]", "", text)
    return int(nums) if nums.isdigit() else None


# =========================
# Scraping Functions
# =========================

def scrape_bigbike_spec(driver, model_info: Dict) -> Dict:
    """Scrape specification page for a BigBike model"""
    slug = model_info["slug"]
    spec_url = f"{BASE_URL}/bigbike/{slug}/specification"
    overview_url = f"{BASE_URL}/bigbike/{slug}/overview"
    
    logger.info("  📄 Fetching: %s", spec_url)
    
    try:
        driver.get(spec_url)
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        data = {
            "brand": "Yamaha",
            "name": model_info["name"],
            "url": overview_url,
            "spec_url": spec_url,
            "category": "BigBike",
            "price": f"{model_info['price']} บาท",
            "price_numeric": price_to_int(model_info["price"]),
            "specifications": {},
            "scraped_at": datetime.now().isoformat()
        }
        
        # Try to get actual price from page if available
        price_el = soup.select_one(".price_center, .price, [class*='price']")
        if price_el:
            price_text = clean(price_el.get_text())
            if price_text:
                # Extract number from price
                match = re.search(r'([\d,]+)', price_text)
                if match:
                    data["price"] = f"{match.group(1)} บาท"
                    data["price_numeric"] = price_to_int(match.group(1))
        
        # Extract specifications from accordion panels
        specifications = {}
        
        for panel in soup.select(".panel.panel-default, .panel-group .panel"):
            # Get section title
            heading = panel.select_one(".panel-heading, .panel-title")
            section_title = clean(heading.get_text()) if heading else "General"
            
            # Get spec data from table
            section_specs = {}
            for row in panel.select("tr"):
                cols = row.find_all("td")
                if len(cols) >= 2:
                    key = clean(cols[0].get_text())
                    value = clean(cols[1].get_text())
                    if key and value and len(key) < 100:
                        section_specs[key] = value
            
            if section_specs:
                specifications[section_title] = section_specs
        
        # Flatten specifications for easier use
        flat_specs = {}
        for section, specs in specifications.items():
            for key, value in specs.items():
                flat_specs[key] = value
        
        data["specifications"] = flat_specs
        data["specifications_grouped"] = specifications
        
        return data
        
        except Exception as e:
            logger.exception("  ❌ Error: %s", e)
        return {
            "brand": "Yamaha",
            "name": model_info["name"],
            "url": overview_url,
            "category": "BigBike",
            "price": f"{model_info['price']} บาท",
            "price_numeric": price_to_int(model_info["price"]),
            "specifications": {},
            "error": str(e),
            "scraped_at": datetime.now().isoformat()
        }


def run():
    """Main scraping function"""
    logger.info("=" * 60)
    logger.info("🏍️ Yamaha BigBike Thailand Scraper")
    logger.info("=" * 60)
    
    driver = create_driver()
    results = []
    errors = []
    
    try:
        total = len(BIGBIKE_MODELS)
        logger.info("🔍 Scraping %d BigBike models", total)
        
        for idx, model_info in enumerate(BIGBIKE_MODELS, 1):
            try:
                logger.info("\n[%d/%d] %s", idx, total, model_info['name'])
                data = scrape_bigbike_spec(driver, model_info)
                results.append(data)
                
                spec_count = len(data.get("specifications", {}))
                logger.info("  ✅ Done - Price: %s, Specs: %d", data.get('price', 'N/A'), spec_count)
                
                # Random delay to avoid blocking
                time.sleep(random.uniform(2.0, 4.0))
                
            except Exception as e:
                logger.exception("  ❌ Error: %s", e)
                errors.append({"model": model_info["name"], "error": str(e)})
                errors.append({"model": model_info["name"], "error": str(e)})
                
    finally:
        driver.quit()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Main JSON file
    output_file = OUTPUT_DIR / f"yamaha_bigbike_{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "source": "yamaha-motor.co.th/bigbike",
                "scraped_at": datetime.now().isoformat(),
                "total_count": len(results),
                "error_count": len(errors)
            },
            "motorcycles": results
        }, f, ensure_ascii=False, indent=2)
    
    # Latest file
    latest_file = OUTPUT_DIR / "yamaha_bigbike_latest.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "source": "yamaha-motor.co.th/bigbike",
                "scraped_at": datetime.now().isoformat(),
                "total_count": len(results),
                "error_count": len(errors)
            },
            "motorcycles": results
        }, f, ensure_ascii=False, indent=2)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 SCRAPING SUMMARY")
    logger.info("=" * 60)
    logger.info("✅ Total scraped: %d", len(results))
    logger.info("❌ Errors: %d", len(errors))
    logger.info("📁 Saved to: %s", output_file)
    logger.info("📁 Latest: %s", latest_file)
    logger.info("=" * 60)
    
    return results


if __name__ == "__main__":
    setup_logging()
    run()
