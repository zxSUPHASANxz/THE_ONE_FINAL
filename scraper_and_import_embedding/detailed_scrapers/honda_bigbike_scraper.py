"""
Honda BigBike Thailand Scraper
===============================
สกัดข้อมูลรถบิ๊กไบค์ Honda ทุกรุ่นจาก https://www.thaihonda.co.th/hondabigbike/motorcycle
- เข้าหน้าหลักเพื่อดึง URL ของรถทุกรุ่น
- เข้าหน้ารถแต่ละรุ่น กดปุ่ม "+" เพื่อขยาย accordion
- สกัด Specifications จาก div class="spec"
- บันทึกเป็น JSON

หมายเหตุ: ไฟล์นี้ทำหน้าที่สกัดข้อมูลเท่านั้น (Scraping Only)
          การสร้าง Embedding และนำเข้า DB ใช้ import_and_embedding_to_knowbase.py

รันด้วย: python honda_bigbike_scraper.py
"""
import json
import time
import re
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    NoSuchElementException,
)
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from tqdm import tqdm


# =========================
# Configuration
# =========================

BASE_URL = "https://www.thaihonda.co.th"
BIGBIKE_URL = f"{BASE_URL}/hondabigbike/motorcycle"
OUTPUT_DIR = Path(__file__).parent.parent / "database"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# Selenium Setup
# =========================

def create_driver(headless=True):
    """สร้าง Chrome WebDriver"""
    options = Options()
    if headless:
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


def dismiss_cookie_banner(driver):
    """ปิด cookie consent banner (ถ้ามี)"""
    try:
        accept_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        accept_btn.click()
        time.sleep(1)
    except TimeoutException:
        pass  # ไม่มี banner หรือ ปิดไปแล้ว


# =========================
# Step 1: ดึง URL รถทุกรุ่นจากหน้าหลัก
# =========================

def get_model_urls(driver):
    """
    เข้าหน้า /hondabigbike/motorcycle แล้วดึง link ของรถแต่ละรุ่น
    URL pattern: /hondabigbike/motorcycle/{category}/{model-slug}
    """
    print(f"\n🔍 กำลังดึงรายการรถจาก {BIGBIKE_URL}")
    driver.get(BIGBIKE_URL)
    time.sleep(5)

    dismiss_cookie_banner(driver)

    # Scroll ลงทีละนิดเพื่อ trigger lazy-load (ถ้ามี)
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    soup = BeautifulSoup(driver.page_source, "html.parser")

    model_urls = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        # ต้องมี /hondabigbike/motorcycle/ + category + model (อย่างน้อย 4 segments)
        if "/hondabigbike/motorcycle/" in href and href != "/hondabigbike/motorcycle":
            parts = href.rstrip("/").split("/")
            # /hondabigbike/motorcycle/sport/cbr1000rr-r => อย่างน้อย 4 ส่วนหลัง domain
            if len(parts) >= 4:
                full_url = f"{BASE_URL}{href}" if not href.startswith("http") else href
                if full_url not in model_urls:
                    model_urls.append(full_url)

    print(f"✅ พบรถทั้งหมด {len(model_urls)} รุ่น")
    for i, url in enumerate(model_urls, 1):
        print(f"   {i}. {url.split('/')[-1]}")
    return model_urls


# =========================
# Step 2: กดปุ่ม "+" ขยาย accordion ทั้งหมด
# =========================

def expand_all_accordions(driver):
    """
    ค้นหาปุ่ม "+" (accordion toggle) ภายใน div.spec แล้วกดขยายทั้งหมด
    จากภาพ: accordion header มีไอคอน +/- สำหรับขยาย/ย่อ section
    """
    expanded_count = 0

    try:
        # รอให้ section spec โหลด
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.spec"))
        )
    except TimeoutException:
        print("   ⚠️ ไม่พบ div.spec ในหน้านี้")
        return expanded_count

    # -- ลองหลายวิธีกด accordion --

    # วิธี 1: กดปุ่ม/icon ที่เป็น accordion toggle ใน div.spec
    toggle_selectors = [
        "div.spec .accordion .icon",
        "div.spec .accordion-toggle",
        "div.spec .accordion-header",
        "div.spec [data-toggle='collapse']",
        "div.spec .collapse-trigger",
        "div.spec .btn-accordion",
        "div.spec .plus-icon",
        "div.spec h3",
        "div.spec .panel-heading",
    ]

    for selector in toggle_selectors:
        toggles = driver.find_elements(By.CSS_SELECTOR, selector)
        if toggles:
            for toggle in toggles:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle)
                    time.sleep(0.3)
                    toggle.click()
                    expanded_count += 1
                    time.sleep(0.5)
                except (ElementClickInterceptedException, Exception):
                    try:
                        driver.execute_script("arguments[0].click();", toggle)
                        expanded_count += 1
                        time.sleep(0.5)
                    except Exception:
                        pass
            if expanded_count > 0:
                break

    # วิธี 2: ถ้ายังไม่พบ toggle ให้ลองหา element ที่มี text "+" แล้วกด
    if expanded_count == 0:
        try:
            plus_elements = driver.find_elements(
                By.XPATH,
                "//div[contains(@class,'spec')]//span[text()='+'] | "
                "//div[contains(@class,'spec')]//i[text()='+'] | "
                "//div[contains(@class,'spec')]//button[text()='+'] | "
                "//div[contains(@class,'spec')]//div[text()='+']"
            )
            for el in plus_elements:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    time.sleep(0.3)
                    el.click()
                    expanded_count += 1
                    time.sleep(0.5)
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", el)
                        expanded_count += 1
                    except Exception:
                        pass
        except Exception:
            pass

    # วิธี 3: Force-expand ด้วย JS
    if expanded_count == 0:
        driver.execute_script("""
            document.querySelectorAll('div.spec .accordion-content, div.spec .panel-body, div.spec .collapse').forEach(el => {
                el.style.display = 'block';
                el.style.height = 'auto';
                el.style.overflow = 'visible';
                el.classList.add('in', 'show', 'active');
            });
        """)
        expanded_count = -1

    # วิธี 4: Fallback สุดท้าย
    driver.execute_script("""
        document.querySelectorAll('div.spec [style*="display: none"], div.spec [style*="display:none"]').forEach(el => {
            el.style.display = 'block';
        });
        document.querySelectorAll('div.spec .collapsed').forEach(el => {
            el.classList.remove('collapsed');
        });
    """)

    if expanded_count > 0:
        print(f"   ✅ กด expand accordion {expanded_count} section(s)")
    elif expanded_count == -1:
        print("   ✅ Force-expand accordion ด้วย JavaScript")
    else:
        print("   ℹ️ ไม่พบ accordion toggle (อาจเปิดอยู่แล้ว)")

    time.sleep(1)
    return expanded_count


# =========================
# Step 3: สกัดข้อมูลจาก div.spec
# =========================

def extract_model_name_and_price(soup):
    """ดึงชื่อรุ่นและราคาจากหน้ารถ"""
    name = ""
    price_text = ""

    for selector in [
        ("h1", {}),
        ("h2", {"class": "title"}),
        ("div", {"class": "product-name"}),
        ("div", {"class": re.compile(r"model[-_]?name", re.I)}),
    ]:
        tag = soup.find(selector[0], selector[1]) if selector[1] else soup.find(selector[0])
        if tag:
            text = tag.get_text(strip=True)
            if text and len(text) < 150:
                name = text
                break

    for tag in soup.find_all(string=re.compile(r"(start|เริ่มต้น|ราคา|THB|บาท)")):
        text = tag if isinstance(tag, str) else tag.get_text(strip=True)
        match = re.search(r"([\d,]+)\s*(THB|บาท)", text)
        if match:
            price_text = text.strip()
            break

    if not name:
        title_tag = soup.find("title")
        if title_tag:
            name = title_tag.get_text(strip=True).split("|")[0].strip()

    return name, price_text


def extract_specs_from_div(soup):
    """
    สกัด Specifications จาก div class="spec"
    โครงสร้าง HTML (จาก DevTools):
        div.spec > div.container > h2.title "ข้อมูลผลิตภัณฑ์"
                                 > div.accordion
                                    > section header (สมรรถนะของเครื่องยนต์ etc.)
                                    > table rows → spec_name | spec_value
    """
    all_specs = {}

    spec_div = soup.find("div", class_="spec")
    if not spec_div:
        return all_specs

    current_section = "ทั่วไป"

    # --- ลองอ่านจาก table rows ก่อน ---
    tables = spec_div.find_all("table")
    for table in tables:
        prev = table.find_previous_sibling(["h3", "h4", "div"])
        if prev:
            header_text = prev.get_text(strip=True)
            if header_text and len(header_text) < 100:
                current_section = header_text

        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                val = cells[1].get_text(strip=True)
                if key and val:
                    all_specs[key] = val

    # --- ถ้า table ไม่มี ลองอ่านจาก div pairs ---
    if not all_specs:
        for name_div in spec_div.find_all("div", class_="n_name"):
            value_div = name_div.find_next_sibling("div", class_="value")
            if not value_div:
                parent = name_div.parent
                value_div = parent.find("div", class_="value") if parent else None
            if value_div:
                key = name_div.get_text(strip=True)
                val = value_div.get_text(strip=True)
                if key and val:
                    all_specs[key] = val

    # --- ลองอ่านจาก dl/dt/dd ---
    if not all_specs:
        for dt in spec_div.find_all("dt"):
            dd = dt.find_next_sibling("dd")
            if dd:
                key = dt.get_text(strip=True)
                val = dd.get_text(strip=True)
                if key and val:
                    all_specs[key] = val

    # --- Fallback: อ่านทุก text pair ที่ดูเป็น key-value ---
    if not all_specs:
        rows = spec_div.find_all("div", class_=re.compile(r"(row|item|spec-row|n_desc)"))
        for row in rows:
            children = row.find_all("div", recursive=False)
            if len(children) >= 2:
                key = children[0].get_text(strip=True)
                val = children[1].get_text(strip=True)
                if key and len(key) < 100:
                    all_specs[key] = val

    return all_specs


def extract_colors(soup):
    """ดึงสีที่มีให้เลือก"""
    colors = []
    for el in soup.find_all(["div", "span", "li"], class_=re.compile(r"color", re.I)):
        text = el.get_text(strip=True)
        if text and len(text) < 80:
            colors.append(text)
    return list(dict.fromkeys(colors))


# =========================
# Step 4: สกัดข้อมูลจากหน้ารถแต่ละรุ่น
# =========================

def scrape_model_page(driver, url):
    """เข้าหน้ารถ 1 รุ่น → กดขยาย accordion → ดึง specs"""
    slug = url.rstrip("/").split("/")[-1]
    category = url.rstrip("/").split("/")[-2] if len(url.split("/")) >= 5 else ""

    print(f"\n📄 [{slug}] กำลังเปิดหน้า...")
    driver.get(url)
    time.sleep(4)

    dismiss_cookie_banner(driver)

    # Scroll ลงไปให้ถึง section spec
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
    time.sleep(2)

    # กดขยาย accordion ทั้งหมด
    expand_all_accordions(driver)

    # ดึง page source หลังจากขยายแล้ว
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # ดึงข้อมูล
    model_name, price_text = extract_model_name_and_price(soup)
    specs = extract_specs_from_div(soup)

    if not model_name:
        model_name = slug.replace("-", " ").title()

    print(f"   ชื่อรุ่น: {model_name}")
    print(f"   ราคา: {price_text or 'ไม่พบ'}")
    print(f"   Specs: {len(specs)} รายการ")

    return {
        "brand": "Honda",
        "model": model_name,
        "slug": slug,
        "category": category,
        "url": url,
        "price": price_text,
        "specifications": specs,
        "colors": extract_colors(soup),
        "scraped_at": datetime.now().isoformat(),
    }


# =========================
# Main
# =========================

def main():
    print("=" * 70)
    print("🏍️  Honda BigBike Thailand Scraper")
    print(f"   Source: {BIGBIKE_URL}")
    print("=" * 70)

    driver = create_driver(headless=True)

    try:
        # 1. ดึงรายการ URL ของรถทุกรุ่น
        model_urls = get_model_urls(driver)

        if not model_urls:
            print("❌ ไม่พบ URL ของรถ — ลองรัน headless=False เพื่อดู browser")
            return

        # 2. วนสกัดข้อมูลแต่ละรุ่น
        results = []
        for idx, url in enumerate(tqdm(model_urls, desc="📊 สกัดข้อมูล"), 1):
            try:
                data = scrape_model_page(driver, url)
                results.append(data)
                print(f"   ✅ [{idx}/{len(model_urls)}] {data['model']} — เสร็จ")
            except Exception as e:
                print(f"   ❌ [{idx}/{len(model_urls)}] {url.split('/')[-1]} — Error: {e}")

            time.sleep(2)

        # 3. บันทึก JSON
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"honda_bigbike_detailed_{timestamp}.json"
        output_path = OUTPUT_DIR / filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 70)
        print(f"✅ สกัดข้อมูลเสร็จสิ้น!")
        print(f"   จำนวนรุ่น: {len(results)}/{len(model_urls)}")
        print(f"   บันทึกที่: {output_path}")
        print(f"💡 ขั้นตอนถัดไป: รัน import_and_embedding_to_knowbase.py เพื่อสร้าง embedding และนำเข้า DB")
        print("=" * 70)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
