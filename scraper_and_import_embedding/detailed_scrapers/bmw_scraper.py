"""
BMW Motorrad Thailand Scraper
==============================
สกัดข้อมูลรถมอเตอร์ไซค์ BMW ทุกรุ่นจาก bmw-motorrad.co.th

ขั้นตอน:
1. เข้าหน้า modeloverview.html → ดึง URL ของรถทุกรุ่น
2. เข้าหน้ารถแต่ละรุ่น → ดึงชื่อ + ราคาจาก productstage
3. เข้าหน้า technicaldata.html → ดึง specs จาก section.module.table
4. บันทึกเป็น JSON ใน database/

หมายเหตุ: ไฟล์นี้ทำหน้าที่สกัดข้อมูลเท่านั้น (Scraping Only)
          การสร้าง Embedding และนำเข้า DB ใช้ import_and_embedding_to_knowbase.py

รันด้วย: python bmw_scraper.py
"""
import json
import re
import time
import random
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# =========================
# Configuration
# =========================

BASE_URL = "https://www.bmw-motorrad.co.th"
OVERVIEW_URL = f"{BASE_URL}/th/models/modeloverview.html"
OUTPUT_DIR = Path(__file__).parent.parent / "database"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# หมวดรถที่ต้องการ scrape (ใช้กรอง URL จากหน้า Overview)
VALID_CATEGORIES = {"sport", "tour", "roadster", "heritage", "adventure", "urban-mobility"}


# =========================
# Selenium Setup
# =========================

def create_driver():
    """สร้าง Chrome WebDriver แบบ headless"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )


def clean(text):
    """ลบ &nbsp; และ whitespace ซ้ำออกจากข้อความ"""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ").strip())


# =========================
# Step 1: ดึง URL รถทุกรุ่นจากหน้า Overview
# =========================

def get_model_urls(driver):
    """
    เปิดหน้า modeloverview.html → scroll โหลดรถทั้งหมด
    → ดึง link ที่ match /th/models/{category}/{slug}.html
    """
    print(f"\n🔍 กำลังดึงรายการรถจาก {OVERVIEW_URL}")
    driver.get(OVERVIEW_URL)
    time.sleep(5)

    # Scroll ลงทีละส่วนเพื่อ trigger lazy loading ให้โหลดรถทุกหมวด
    for i in range(6):
        driver.execute_script(
            f"window.scrollTo(0, document.body.scrollHeight * {0.17 * (i + 1)});"
        )
        time.sleep(1.5)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    models = []
    seen_slugs = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]

        # Match URL pattern: /th/models/sport/s1000rr.html
        match = re.match(r"/th/models/([\w-]+)/([\w-]+)\.html$", href)
        if not match:
            continue

        category, slug = match.group(1), match.group(2)

        # กรองเฉพาะ URL ที่เป็นหน้ารุ่นรถจริง + ไม่ซ้ำ
        if category not in VALID_CATEGORIES or slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        models.append({
            "slug": slug,
            "category": category.replace("-", " ").title(),
            "url": f"{BASE_URL}{href}",
        })

    print(f"✅ พบรถทั้งหมด {len(models)} รุ่น")
    for i, m in enumerate(models, 1):
        print(f"   {i}. [{m['category']}] {m['slug']}")

    return models


# =========================
# Step 2: Scrape รถ 1 รุ่น (ชื่อ + ราคา + specs)
# =========================

def scrape_model(driver, model):
    """
    เข้าหน้ารถ 1 รุ่น:
    1. ดึงชื่อรุ่น + ราคาจากหน้า model page (productstage)
    2. เปิดหน้า technicaldata.html → ดึง specs จาก section.module.table
    """
    url = model["url"]

    # --- หน้ารุ่นรถ: ดึงชื่อและราคา ---
    print(f"   📄 เปิดหน้ารุ่นรถ...")
    driver.get(url)
    time.sleep(3)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
    time.sleep(1)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # ดึงชื่อรุ่น จาก span.productName
    name = model["slug"].replace("-", " ").title()
    name_el = soup.select_one("span.productName")
    if name_el:
        candidate = clean(name_el.get_text())
        if candidate and len(candidate) < 80:
            name = candidate

    # ดึงราคา เช่น "เริ่มต้น 1,029,000 บาท*"
    price = None
    price_numeric = None

    # วิธี 1: จาก p.pricing หรือ productstage__info
    price_el = soup.select_one("p.pricing, .productstage__info")
    if price_el:
        price_match = re.search(r"([\d,]+)\s*บาท", price_el.get_text())
        if price_match:
            price = f"{price_match.group(1)} บาท"
            price_numeric = int(price_match.group(1).replace(",", ""))

    # วิธี 2: fallback regex จากข้อความทั้งหน้า
    if not price:
        page_text = soup.get_text(" ", strip=True)
        price_match = re.search(r"เริ่มต้น\s*([\d,]+)\s*บาท", page_text)
        if price_match:
            price = f"{price_match.group(1)} บาท"
            price_numeric = int(price_match.group(1).replace(",", ""))

    # --- หน้า Technical Data: ดึง specs ---
    tech_url = url.replace(".html", "/technicaldata.html")
    print(f"   📄 เปิดหน้า Technical Data...")
    driver.get(tech_url)
    time.sleep(3)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
    time.sleep(1)

    tech_soup = BeautifulSoup(driver.page_source, "html.parser")

    # ดึง specs จาก <section class="module table"> > table > tr > td
    specs = {}
    for section in tech_soup.select("section.module.table"):
        for row in section.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                key = clean(cells[0].get_text())
                val = clean(cells[1].get_text())
                if key and val:
                    specs[key] = val

    print(f"   ✅ {name} — ราคา: {price or 'N/A'}, Specs: {len(specs)}")

    return {
        "brand": "BMW",
        "name": name,
        "slug": model["slug"],
        "category": model["category"],
        "url": url,
        "price": price,
        "price_numeric": price_numeric,
        "specifications": specs,
        "scraped_at": datetime.now().isoformat(),
    }


# =========================
# Main
# =========================

def run():
    """รัน scraper: ดึง URL จาก overview → scrape ทีละรุ่น → บันทึก JSON"""
    print("=" * 60)
    print("🏍️  BMW Motorrad Thailand Scraper")
    print("=" * 60)

    driver = create_driver()
    results = []
    errors = []

    try:
        # 1. ดึง URL ทุกรุ่นจากหน้า Overview
        models = get_model_urls(driver)
        if not models:
            print("❌ ไม่พบรุ่นรถ — ตรวจสอบหน้า Overview")
            return []

        total = len(models)
        print(f"\n🚀 เริ่มสกัดข้อมูลจาก {total} รุ่น...\n")

        # 2. สกัดข้อมูลทีละรุ่น
        for idx, model in enumerate(models, 1):
            try:
                progress = (idx / total) * 100
                print(f"\n[{idx}/{total} — {progress:.0f}%] {model['slug']}")
                data = scrape_model(driver, model)
                results.append(data)
                time.sleep(random.uniform(2.0, 4.0))
            except Exception as e:
                print(f"   ❌ Error: {e}")
                errors.append({"slug": model["slug"], "error": str(e)})

    finally:
        driver.quit()

    # 3. บันทึก JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"bmw_all_models_{timestamp}.json"
    latest_file = OUTPUT_DIR / "bmw_all_models.json"

    payload = {
        "metadata": {
            "source": "bmw-motorrad.co.th",
            "scraped_at": datetime.now().isoformat(),
            "total_count": len(results),
            "error_count": len(errors),
        },
        "motorcycles": results,
    }

    for path in (output_file, latest_file):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    # 4. สรุป
    print("\n" + "=" * 60)
    print("📊 SCRAPING SUMMARY")
    print("=" * 60)
    print(f"✅ สกัดสำเร็จ: {len(results)} รุ่น")
    print(f"❌ Error: {len(errors)} รุ่น")
    print(f"📁 บันทึกที่: {output_file}")
    print(f"📁 Latest: {latest_file}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    run()
