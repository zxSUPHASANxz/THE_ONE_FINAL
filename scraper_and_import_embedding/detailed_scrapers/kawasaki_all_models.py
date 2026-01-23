"""
Kawasaki Thailand Motorcycle Scraper
=====================================
สกัดข้อมูลรถจักรยานยนต์ Kawasaki ทุกรุ่นจาก kawasaki.co.th

รันด้วย: python kawasaki_all_models.py
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


# =========================
# Configuration
# =========================

BASE_URL = "https://www.kawasaki.co.th"
OUTPUT_DIR = Path(__file__).parent.parent / "database"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Kawasaki models จาก compare page
KAWASAKI_MODELS = [
    # NINJA Series
    {"slug": "ninjah2", "name": "Ninja H2", "price": "1,620,000", "category": "Ninja"},
    {"slug": "ninjae1", "name": "Ninja e-1", "price": "276,000", "category": "Ninja"},
    {"slug": "ninjazx10rr", "name": "Ninja ZX-10RR", "price": "1,223,000", "category": "Ninja"},
    {"slug": "ninjazx10r", "name": "Ninja ZX-10R", "price": "859,000", "category": "Ninja"},
    {"slug": "ninjazx6r", "name": "Ninja ZX-6R", "price": "399,000", "category": "Ninja"},
    {"slug": "ninjazx4rse", "name": "Ninja ZX-4R SE", "price": "320,000", "category": "Ninja"},
    {"slug": "ninjazx4r", "name": "Ninja ZX-4R", "price": "299,000", "category": "Ninja"},
    {"slug": "ninja650", "name": "Ninja 650", "price": "318,900", "category": "Ninja"},
    {"slug": "ninja500se", "name": "Ninja 500 SE", "price": "219,800", "category": "Ninja"},
    
    # Z Series
    {"slug": "z1000", "name": "Z1000", "price": "620,700", "category": "Z"},
    {"slug": "z900", "name": "Z900", "price": "349,000", "category": "Z"},
    {"slug": "z900-2023", "name": "Z900 (2023)", "price": "413,100", "category": "Z"},
    {"slug": "z900rs", "name": "Z900RS", "price": "409,000", "category": "Z"},
    {"slug": "z900rsse", "name": "Z900RS SE", "price": "449,000", "category": "Z"},
    {"slug": "z650", "name": "Z650", "price": "292,200", "category": "Z"},
    {"slug": "z500se", "name": "Z500 SE", "price": "219,800", "category": "Z"},
    
    # Versys
    {"slug": "versys650", "name": "Versys 650", "price": "259,000", "category": "Versys"},
    
    # Eliminator
    {"slug": "eliminatorse", "name": "Eliminator SE", "price": "215,000", "category": "Eliminator"},
    {"slug": "eliminator", "name": "Eliminator", "price": "199,000", "category": "Eliminator"},
    
    # Vulcan
    {"slug": "vulcans", "name": "Vulcan S", "price": "259,000", "category": "Vulcan"},
    
    # MEGURO
    {"slug": "megurok3", "name": "MEGURO K3", "price": "379,000", "category": "MEGURO"},
    {"slug": "meguros1", "name": "MEGURO S1", "price": "147,900", "category": "MEGURO"},
    
    # W Series
    {"slug": "w800", "name": "W800", "price": "325,000", "category": "W"},
    {"slug": "w230", "name": "W230", "price": "119,900", "category": "W"},
    
    # KLR
    {"slug": "klr650adventure", "name": "KLR650 Adventure", "price": "295,000", "category": "KLR"},
    {"slug": "klr650", "name": "KLR650", "price": "269,000", "category": "KLR"},
    
    # KLX Series
    {"slug": "klx230sherpa", "name": "KLX230 SHERPA", "price": "169,000", "category": "KLX"},
    {"slug": "klx230r", "name": "KLX230 R", "price": "175,000", "category": "KLX"},
    {"slug": "klx230sm", "name": "KLX230 SM", "price": "129,000", "category": "KLX"},
    {"slug": "klx230se", "name": "KLX230 SE", "price": "114,400", "category": "KLX"},
    {"slug": "klx230s", "name": "KLX230 S", "price": "110,000", "category": "KLX"},
    {"slug": "klx230", "name": "KLX230", "price": "99,500", "category": "KLX"},
    {"slug": "klx140rf", "name": "KLX140R F", "price": "125,000", "category": "KLX"},
    {"slug": "klx110rl", "name": "KLX110R L", "price": "89,000", "category": "KLX"},
    
    # KX (Motocross)
    {"slug": "kx250", "name": "KX250", "price": "325,000", "category": "KX"},
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

def scrape_model_detail(driver, model_info: Dict) -> Dict:
    """Scrape model detail page"""
    slug = model_info["slug"]
    url = f"{BASE_URL}/th/motorcycle/{slug}"
    
    print(f"  � Fetching: {url}")
    
    try:
        driver.get(url)
        time.sleep(4)
        
        # Scroll to load all content
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        data = {
            "brand": "Kawasaki",
            "name": model_info["name"],
            "url": url,
            "category": model_info["category"],
            "price": f"{model_info['price']} บาท",
            "price_numeric": price_to_int(model_info["price"]),
            "specifications": {},
            "scraped_at": datetime.now().isoformat()
        }
        
        # Try to get actual price from page
        price_el = soup.select_one(".kw-product-price, .price, [class*='price']")
        if price_el:
            price_text = clean(price_el.get_text())
            if price_text:
                match = re.search(r'([\d,]+)', price_text)
                if match:
                    data["price"] = f"{match.group(1)} บาท"
                    data["price_numeric"] = price_to_int(match.group(1))
        
        # Extract specifications - Kawasaki uses kw-product-specification class
        specifications = {}
        
        # Method 1: Look for specification section
        spec_section = soup.select_one(".kw-product-specification, .kw-product, [class*='specification']")
        
        if spec_section:
            # Find all tables
            for table in spec_section.select("table"):
                for row in table.select("tr"):
                    cols = row.select("td, th")
                    if len(cols) >= 2:
                        key = clean(cols[0].get_text())
                        value = clean(cols[1].get_text())
                        if key and value and len(key) < 100:
                            specifications[key] = value
        
        # Method 2: Look for spec rows with specific patterns
        if len(specifications) < 5:
            # Look for elements containing spec data
            for elem in soup.select("div[class*='spec'], div[class*='detail'], section"):
                rows = elem.select("tr, .row")
                for row in rows:
                    cols = row.select("td, div, span")
                    if len(cols) >= 2:
                        key = clean(cols[0].get_text())
                        value = clean(cols[1].get_text())
                        if key and value and 2 < len(key) < 80 and len(value) < 150:
                            if key not in specifications:
                                specifications[key] = value
        
        # Method 3: Parse text blocks
        if len(specifications) < 3:
            page_text = soup.get_text()
            # Look for common spec patterns
            spec_patterns = [
                (r'เครื่องยนต์[:\s]*(.+?)(?:\n|$)', 'เครื่องยนต์'),
                (r'ความกว้าง[:\s]*([\d,]+\s*mm)', 'ความกว้าง'),
                (r'ความยาว[:\s]*([\d,]+\s*mm)', 'ความยาว'),
                (r'ความสูง[:\s]*([\d,]+\s*mm)', 'ความสูง'),
                (r'น้ำหนัก[:\s]*([\d,]+\s*kg)', 'น้ำหนัก'),
            ]
            for pattern, label in spec_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match and label not in specifications:
                    specifications[label] = match.group(1).strip()
        
        data["specifications"] = specifications

        # Extract Features / Description
        features = []
        # Target specific sections for description text
        feature_sections = soup.select(".kw-product-intro .wrapper, .kw-product-feature .wrapper")
        
        for section in feature_sections:
            # Extract text from paragraphs and headers
            for elem in section.select("p, h1, h2, h3, h4, h5, div"):
                text = clean(elem.get_text())
                # Filter out short or irrelevant text
                if text and len(text) > 10 and "SPECIFICATIONS" not in text and "ACCESSORIES" not in text:
                    if text not in features:
                        features.append(text)
        
        data["features"] = features
        
        return data
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {
            "brand": "Kawasaki",
            "name": model_info["name"],
            "url": url,
            "category": model_info["category"],
            "price": f"{model_info['price']} บาท",
            "price_numeric": price_to_int(model_info["price"]),
            "specifications": {},
            "error": str(e),
            "scraped_at": datetime.now().isoformat()
        }


def main():
    """Main scraping function"""
    print("=" * 60)
    print("🏍️ Kawasaki Thailand Motorcycle Scraper")
    print("=" * 60)
    
    driver = create_driver()
    results = []
    errors = []
    
    try:
        total = len(KAWASAKI_MODELS)
        print(f"🔍 Scraping {total} Kawasaki models")
        
        for idx, model_info in enumerate(KAWASAKI_MODELS, 1):
            try:
                print(f"\n[{idx}/{total}] {model_info['name']}")
                data = scrape_model_detail(driver, model_info)
                results.append(data)
                
                spec_count = len(data.get("specifications", {}))
                print(f"  ✅ Done - Price: {data.get('price', 'N/A')}, Specs: {spec_count}")
                
                # Random delay to avoid blocking
                time.sleep(random.uniform(2.0, 4.0))
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                errors.append({"model": model_info["name"], "error": str(e)})
                
    finally:
        driver.quit()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Main JSON file
    output_file = OUTPUT_DIR / f"kawasaki_all_models_{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "source": "kawasaki.co.th",
                "scraped_at": datetime.now().isoformat(),
                "total_count": len(results),
                "error_count": len(errors)
            },
            "motorcycles": results
        }, f, ensure_ascii=False, indent=2)
    
    # Latest file
    latest_file = OUTPUT_DIR / "kawasaki_all_models_latest.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "source": "kawasaki.co.th",
                "scraped_at": datetime.now().isoformat(),
                "total_count": len(results),
                "error_count": len(errors)
            },
            "motorcycles": results
        }, f, ensure_ascii=False, indent=2)
    
    # By category
    categories = {}
    for m in results:
        cat = m.get("category", "Other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(m)
    
    for cat, models in categories.items():
        cat_file = OUTPUT_DIR / f"kawasaki_{cat.lower()}_{timestamp}.json"
        with open(cat_file, "w", encoding="utf-8") as f:
            json.dump(models, f, ensure_ascii=False, indent=2)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SCRAPING SUMMARY")
    print("=" * 60)
    print(f"✅ Total scraped: {len(results)}")
    print(f"❌ Errors: {len(errors)}")
    print(f"📁 Saved to: {output_file}")
    print(f"📁 Latest: {latest_file}")
    print("\n📂 By Category:")
    for cat, models in sorted(categories.items()):
        print(f"   • {cat}: {len(models)} models")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    main()
