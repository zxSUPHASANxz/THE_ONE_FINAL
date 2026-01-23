"""
BMW Motorrad Thailand Scraper
==============================
สกัดข้อมูลรถมอเตอร์ไซค์ BMW ทุกรุ่นจาก bmw-motorrad.co.th
ด้วยวิธีการ Direct URL Access (เนื่องจากหน้า Overview เป็น Dynamic JS)

รันด้วย: python bmw_scraper.py
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

BASE_URL = "https://www.bmw-motorrad.co.th"
OUTPUT_DIR = Path(__file__).parent.parent / "database"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Predefined Model List (URL patterns verified for Thailand)
BMW_MODELS = [
    # --- Sport ---
    {"name": "M 1000 RR", "url": "/th/models/sport/m1000rr.html", "category": "Sport"},
    {"name": "S 1000 RR", "url": "/th/models/sport/s1000rr.html", "category": "Sport"},
    {"name": "S 1000 XR", "url": "/th/models/sport/s1000xr.html", "category": "Sport"},
    {"name": "F 900 XR", "url": "/th/models/sport/f900xr.html", "category": "Sport"},
    {"name": "G 310 RR", "url": "/th/models/sport/g310rr.html", "category": "Sport"},

    # --- Tour ---
    {"name": "K 1600 Grand America", "url": "/th/models/tour/k1600-grand-america.html", "category": "Tour"},
    {"name": "K 1600 B", "url": "/th/models/tour/k1600b.html", "category": "Tour"},
    {"name": "K 1600 GTL", "url": "/th/models/tour/k1600gtl.html", "category": "Tour"},
    {"name": "K 1600 GT", "url": "/th/models/tour/k1600gt.html", "category": "Tour"},
    {"name": "R 1250 RT", "url": "/th/models/tour/r1250rt.html", "category": "Tour"},

    # --- Roadster ---
    {"name": "M 1000 R", "url": "/th/models/roadster/m1000r.html", "category": "Roadster"},
    {"name": "S 1000 R", "url": "/th/models/roadster/s1000r.html", "category": "Roadster"},
    {"name": "F 900 R", "url": "/th/models/roadster/f900r.html", "category": "Roadster"},
    {"name": "G 310 R", "url": "/th/models/roadster/g310r.html", "category": "Roadster"},

    # --- Heritage ---
    {"name": "R 18", "url": "/th/models/heritage/r18.html", "category": "Heritage"},
    {"name": "R 18 Classic", "url": "/th/models/heritage/r18-classic.html", "category": "Heritage"},
    {"name": "R 18 B", "url": "/th/models/heritage/r18-b.html", "category": "Heritage"},
    {"name": "R 18 Transcontinental", "url": "/th/models/heritage/r18-transcontinental.html", "category": "Heritage"},
    {"name": "R 18 Roctane", "url": "/th/models/heritage/r18-roctane.html", "category": "Heritage"},
    {"name": "R 12 nineT", "url": "/th/models/heritage/r12-ninet.html", "category": "Heritage"},
    {"name": "R 12", "url": "/th/models/heritage/r12.html", "category": "Heritage"},
    {"name": "R nineT", "url": "/th/models/heritage/rninet.html", "category": "Heritage"},

    # --- Adventure ---
    {"name": "R 1300 GS", "url": "/th/models/adventure/r1300gs.html", "category": "Adventure"},
    {"name": "R 1250 GS Adventure", "url": "/th/models/adventure/r1250gs-adventure.html", "category": "Adventure"},
    {"name": "F 900 GS", "url": "/th/models/adventure/f900gs.html", "category": "Adventure"},
    {"name": "F 900 GS Adventure", "url": "/th/models/adventure/f900gs-adventure.html", "category": "Adventure"},
    {"name": "F 800 GS", "url": "/th/models/adventure/f800gs.html", "category": "Adventure"},
    {"name": "G 310 GS", "url": "/th/models/adventure/g310gs.html", "category": "Adventure"},

    # --- Urban Mobility ---
    {"name": "CE 04", "url": "/th/models/urban-mobility/ce04.html", "category": "Urban Mobility"},
    {"name": "CE 02", "url": "/th/models/urban-mobility/ce02.html", "category": "Urban Mobility"},
    {"name": "C 400 GT", "url": "/th/models/urban-mobility/c400gt.html", "category": "Urban Mobility"},
    {"name": "C 400 X", "url": "/th/models/urban-mobility/c400x.html", "category": "Urban Mobility"},
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
    # Remove HTML space entities and normalize whitespace
    text = text.replace('\xa0', ' ').replace('&nbsp;', ' ')
    return re.sub(r"\s+", " ", text.strip())


def price_to_int(text: str) -> Optional[int]:
    if not text:
        return None
    # Extract first sequence of digits that looks like a price (e.g. 1,029,000)
    match = re.search(r'([\d,]+)', text)
    if match:
        nums = re.sub(r"[^\d]", "", match.group(1))
        return int(nums) if nums.isdigit() else None
    return None


# =========================
# Scraping Functions
# =========================

def scrape_bmw_model(driver, model_info: Dict) -> Dict:
    """Scrape singular BMW model page with retries"""
    relative_url = model_info["url"]
    full_url = f"{BASE_URL}{relative_url}" if not relative_url.startswith("http") else relative_url
    
    print(f"  📄 Fetching: {full_url}")
    from selenium.webdriver.common.by import By 
    
    # Retry logic variables
    max_retries = 3
    
    # Attempt main page load
    for attempt in range(max_retries):
        try:
            driver.get(full_url)
            time.sleep(3)
            # Scroll down to trigger lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
            time.sleep(1)
            break
        except Exception as e:
            print(f"    ⚠️ Connection error (attempt {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise e
            time.sleep(5)

    try:
        # Interaction (Try to click potential tabs/expanders)
        try:
            expand_btns = driver.find_elements(By.XPATH, "//*[contains(text(), 'Expand all') or contains(text(), 'ขยายทั้งหมด') or contains(@class, 'expander-head')]")
            for btn in expand_btns:
                 if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.5)
        except Exception as e:
             pass # Interaction errors are non-critical
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        data = {
            "brand": "BMW",
            "name": model_info["name"],
            "url": full_url,
            "category": model_info["category"],
            "price": None,
            "price_numeric": None,
            "specifications": {},
            "features": [],
            "scraped_at": datetime.now().isoformat()
        }
        
        # 1. PRICE Extraction
        price_found = False
        page_text = soup.get_text(" ", strip=True)
        price_patterns = [
            r'เริ่มต้น\s*([\d,]+)\s*บาท', 
            r'ราคา\s*([\d,]+)\s*บาท',
            r'Start from\s*([\d,]+)\s*THB'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, page_text)
            if match:
                price_val = match.group(1)
                data["price"] = f"{price_val} บาท"
                data["price_numeric"] = price_to_int(price_val)
                price_found = True
                break
        
        if not price_found:
            price_el = soup.select_one(".productstage-price, .m-price-tag, .price-label")
            if price_el:
                price_text = clean(price_el.get_text())
                nums = re.search(r'([\d,]+)', price_text)
                if nums:
                    data["price"] = f"{nums.group(1)} บาท"
                    data["price_numeric"] = price_to_int(nums.group(1))

        # 2. SPECIFICATIONS Extraction
        specs = {}
        
        # Technical Data Page URL
        if full_url.endswith(".html"):
            tech_url = full_url.replace(".html", "/technicaldata.html")
        else:
             tech_url = full_url.rstrip("/") + "/technicaldata.html"
             
        # Retry logic for Technical Data Page
        tech_page_loaded = False
        for attempt in range(max_retries):
            try:
                print(f"    📄 Fetching Tech Data (Attempt {attempt+1}): {tech_url}")
                driver.get(tech_url)
                time.sleep(3)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
                time.sleep(1)
                tech_page_loaded = True
                break
            except Exception as e:
                print(f"    ⚠️ Tech page connection error: {e}")
                time.sleep(2)
        
        if tech_page_loaded:
            tech_soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # --- IMPROVED EXTRACTION LOGIC ---
            # Using class names: .table__label and .table__value
            
            # 1. Direct key-value extraction using specific classes
            val_elements = tech_soup.select(".table__value, [class*='table__value']")
            if val_elements:
                print(f"    Found {len(val_elements)} potential spec values via class class selectors")
                for val in val_elements:
                    val_text = clean(val.get_text())
                    # Look for label in previous sibling or parent->child structure
                    parent = val.parent
                    label_el = parent.select_one(".table__label, [class*='table__label']")
                    
                    # If not in direct parent, try parent's parent (common in some grids)
                    if not label_el and parent.parent:
                        label_el = parent.parent.select_one(".table__label, [class*='table__label']")
                    
                    if label_el:
                        key = clean(label_el.get_text())
                        if key and val_text:
                            specs[key] = val_text

            # 2. Fallback: Table elements (if any exist)
            tables = tech_soup.find_all("table")
            for table in tables:
                for row in table.find_all("tr"):
                    cols = row.find_all(["th", "td"])
                    if len(cols) >= 2:
                        k, v = clean(cols[0].get_text()), clean(cols[1].get_text())
                        if k and v:
                            specs[k.rstrip(" :")] = v

            # 3. Fallback: module table sections (older logic, just in case)
            if not specs:
                module_tables = tech_soup.select(".module.table .row")
                for row in module_tables:
                    col_divs = row.select("div[class*='col-']")
                    if len(col_divs) >= 2:
                         k, v = clean(col_divs[0].get_text()), clean(col_divs[1].get_text())
                         if k and v:
                             specs[k.rstrip(" :")] = v
        
        else:
            print("    ❌ Failed to load Tech Data page after retries")

        data["specifications"] = specs
        
        # 3. FEATURES Extraction (Simple heuristic from Tech Soup or skipped if not critical)
        # Note: Features are often on the Overview page which we navigated away from. 
        # For now, we accept we might miss features unless we navigate back or scrape them first.
        # User emphasized "ALL Technical Data", so Specs are priority.
        
        print(f"    found price: {data['price']}")
        print(f"    found specs: {len(data['specifications'])} items")
        
        return data

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {
            "brand": "BMW",
            "name": model_info["name"],
            "url": full_url,
            "category": model_info["category"],
            "error": str(e),
            "scraped_at": datetime.now().isoformat()
        }


def run():
    """Main scraping function"""
    print("=" * 60)
    print("🏎️ BMW Motorrad Thailand Scraper")
    print("=" * 60)
    
    driver = create_driver()
    results = []
    errors = []
    
    try:
        total = len(BMW_MODELS)
        print(f"🔍 Scraping {total} BMW models")
        
        for idx, model_info in enumerate(BMW_MODELS, 1):
            try:
                current_time = datetime.now().strftime("%H:%M:%S")
                progress = (idx / total) * 100
                print(f"\n[{idx}/{total} - {progress:.1f}%] {model_info['name']} (Time: {current_time})")
                data = scrape_bmw_model(driver, model_info)
                results.append(data)
                
                price_disp = data.get('price') or 'N/A'
                spec_count = len(data.get("specifications", {}))
                feat_count = len(data.get("features", []))
                
                print(f"  ✅ Done - Price: {price_disp}, Specs: {spec_count}, Features: {feat_count}")
                
                # Random delay
                time.sleep(random.uniform(2.0, 4.0))
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                errors.append({"model": model_info["name"], "error": str(e)})
                
    finally:
        driver.quit()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Main JSON file
    output_file = OUTPUT_DIR / f"bmw_all_models_{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "source": "bmw-motorrad.co.th",
                "scraped_at": datetime.now().isoformat(),
                "total_count": len(results),
                "error_count": len(errors)
            },
            "motorcycles": results
        }, f, ensure_ascii=False, indent=2)
    
    # Latest file
    latest_file = OUTPUT_DIR / "bmw_all_models_latest.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "source": "bmw-motorrad.co.th",
                "scraped_at": datetime.now().isoformat(),
                "total_count": len(results),
                "error_count": len(errors)
            },
            "motorcycles": results
        }, f, ensure_ascii=False, indent=2)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SCRAPING SUMMARY")
    print("=" * 60)
    print(f"✅ Total scraped: {len(results)}")
    print(f"❌ Errors: {len(errors)}")
    print(f"📁 Saved to: {output_file}")
    print(f"📁 Latest: {latest_file}")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    run()
