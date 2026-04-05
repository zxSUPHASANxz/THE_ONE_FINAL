"""
Kawasaki Thailand Motorcycle Scraper
=====================================
สกัดข้อมูลรถจักรยานยนต์ Kawasaki ทุกรุ่นจาก https://www.kawasaki.co.th/th/home#

ขั้นตอน:
1. เข้าหน้าหลัก → คลิก sub-menu แต่ละหมวด (Ninja, Z, Versys, ...)
2. ดึง URL ของรถทุกรุ่นจาก div.kw-nav-sub-menu .wrapper
3. เข้าหน้ารถแต่ละรุ่น → ดึง specs จาก div.kw-product-specification .wrapper
4. บันทึกเป็น JSON

หมายเหตุ: ไฟล์นี้ทำหน้าที่สกัดข้อมูลเท่านั้น (Scraping Only)
          การสร้าง Embedding และนำเข้า DB ใช้ import_and_embedding_to_knowbase. 

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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm


# =========================
# Configuration
# =========================

BASE_URL = "https://www.kawasaki.co.th"
HOME_URL = f"{BASE_URL}/th/home#"
OUTPUT_DIR = Path(__file__).parent.parent / "database"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# หมวดหมู่ใน sub-menu (จาก nav.kw-nav-sub)
CATEGORIES = [
    "Ninja", "Z", "Versys", "Eliminator", "Vulcan",
    "MEGURO", "W", "KLE", "KLR", "KLX", "KX",
]

# Fallback: รายการรุ่นที่รู้จัก (ใช้เมื่อ auto-discovery ล้มเหลว)
FALLBACK_MODELS = [
    # NINJA
    {"slug": "ninjah2", "name": "Ninja H2", "category": "Ninja"},
    {"slug": "ninjae1", "name": "Ninja e-1", "category": "Ninja"},
    {"slug": "ninjazx10rr", "name": "Ninja ZX-10RR", "category": "Ninja"},
    {"slug": "ninjazx10r", "name": "Ninja ZX-10R", "category": "Ninja"},
    {"slug": "ninjazx6r", "name": "Ninja ZX-6R", "category": "Ninja"},
    {"slug": "ninjazx4rse", "name": "Ninja ZX-4R SE", "category": "Ninja"},
    {"slug": "ninjazx4r", "name": "Ninja ZX-4R", "category": "Ninja"},
    {"slug": "ninja650", "name": "Ninja 650", "category": "Ninja"},
    {"slug": "ninja500se", "name": "Ninja 500 SE", "category": "Ninja"},
    # Z
    {"slug": "z1000", "name": "Z1000", "category": "Z"},
    {"slug": "z900", "name": "Z900", "category": "Z"},
    {"slug": "z900rs", "name": "Z900RS", "category": "Z"},
    {"slug": "z900rsse", "name": "Z900RS SE", "category": "Z"},
    {"slug": "z650", "name": "Z650", "category": "Z"},
    {"slug": "z500se", "name": "Z500 SE", "category": "Z"},
    # Versys
    {"slug": "versys650", "name": "Versys 650", "category": "Versys"},
    # Eliminator
    {"slug": "eliminatorse", "name": "Eliminator SE", "category": "Eliminator"},
    {"slug": "eliminator", "name": "Eliminator", "category": "Eliminator"},
    # Vulcan
    {"slug": "vulcans", "name": "Vulcan S", "category": "Vulcan"},
    # MEGURO
    {"slug": "megurok3", "name": "MEGURO K3", "category": "MEGURO"},
    {"slug": "meguros1", "name": "MEGURO S1", "category": "MEGURO"},
    # W
    {"slug": "w800", "name": "W800", "category": "W"},
    {"slug": "w230", "name": "W230", "category": "W"},
    # KLE
    {"slug": "kle500", "name": "KLE 500", "category": "KLE"},
    # KLR
    {"slug": "klr650adventure", "name": "KLR650 Adventure", "category": "KLR"},
    {"slug": "klr650", "name": "KLR650", "category": "KLR"},
    # KLX
    {"slug": "klx230sherpa", "name": "KLX230 SHERPA", "category": "KLX"},
    {"slug": "klx230r", "name": "KLX230 R", "category": "KLX"},
    {"slug": "klx230sm", "name": "KLX230 SM", "category": "KLX"},
    {"slug": "klx230se", "name": "KLX230 SE", "category": "KLX"},
    {"slug": "klx230s", "name": "KLX230 S", "category": "KLX"},
    {"slug": "klx230", "name": "KLX230", "category": "KLX"},
    {"slug": "klx140rf", "name": "KLX140R F", "category": "KLX"},
    {"slug": "klx110rl", "name": "KLX110R L", "category": "KLX"},
    # KX
    {"slug": "kx250", "name": "KX250", "category": "KX"},
]


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


def clean(text: str) -> str:
    """ทำความสะอาด text — ลบ whitespace ซ้ำ"""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


# =========================
# Step 1: Auto-discover จาก sub-menu
# =========================

def discover_models_from_submenu(driver) -> List[Dict]:
    """
    เข้าหน้าหลัก → hover/click แต่ละ category ใน sub-nav
    → ดึง link รถจาก div.kw-nav-sub-menu .wrapper
    URL pattern: /th/motorcycle/{slug}
    """
    print(f"\n🔍 กำลังค้นหารุ่นรถจาก {HOME_URL}")
    driver.get(HOME_URL)
    time.sleep(5)

    discovered = []
    seen_slugs = set()

    # --- วิธี 1: คลิก category tab ใน sub-nav แล้วอ่าน dropdown ---
    try:
        # หา nav ที่เป็น sub-menu ของ Motorcycle
        sub_nav_tabs = driver.find_elements(
            By.CSS_SELECTOR,
            "nav.kw-nav-sub a, nav.kw-nav-sub span, nav.kw-nav-sub li"
        )

        for tab in sub_nav_tabs:
            tab_text = clean(tab.text)
            if not tab_text or tab_text.upper() in ("HOME", "MOTORCYCLE", "WATERCRAFT", "4 WHEELER"):
                continue

            category = tab_text.replace(" NEW!", "").replace(" new!", "").strip()

            try:
                # Hover เพื่อเปิด dropdown
                ActionChains(driver).move_to_element(tab).perform()
                time.sleep(1)

                # หา model links จาก dropdown ที่เปิดอยู่
                model_links = driver.find_elements(
                    By.CSS_SELECTOR,
                    "div.kw-nav-sub-menu .wrapper a[href*='/th/motorcycle/']"
                )

                if not model_links:
                    # ลอง click แทน hover
                    try:
                        tab.click()
                        time.sleep(1.5)
                        model_links = driver.find_elements(
                            By.CSS_SELECTOR,
                            "div.kw-nav-sub-menu .wrapper a[href*='/th/motorcycle/']"
                        )
                    except Exception:
                        pass

                for link in model_links:
                    href = link.get_attribute("href") or ""
                    if "/th/motorcycle/" not in href:
                        continue

                    slug = href.rstrip("/").split("/")[-1]
                    if slug in seen_slugs or slug == "motorcycle":
                        continue
                    seen_slugs.add(slug)

                    # ดึงชื่อ + ราคาจากข้อความภายใน link
                    name = clean(link.text) or slug.replace("-", " ").title()
                    # ราคามักอยู่ด้านล่างชื่อรุ่น
                    price_match = re.search(r"([\d,]+)\s*บาท", name)
                    price = price_match.group(1) if price_match else ""
                    # ตัดราคาออกจากชื่อ
                    model_name = re.sub(r"\s*[\d,]+\s*บาท", "", name).strip()

                    discovered.append({
                        "slug": slug,
                        "name": model_name or slug,
                        "category": category,
                        "price": price,
                        "url": href if href.startswith("http") else f"{BASE_URL}{href}",
                    })

            except Exception as e:
                print(f"   ⚠️ ไม่สามารถเปิด tab '{tab_text}': {e}")

    except Exception as e:
        print(f"   ⚠️ Auto-discover จาก sub-nav ล้มเหลว: {e}")

    # --- วิธี 2: ถ้า วิธี 1 ได้น้อย ลอง parse HTML ตรง ---
    if len(discovered) < 5:
        print("   ℹ️ ลอง parse HTML ทั้งหน้าเพื่อหา model links...")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "/th/motorcycle/" in href:
                slug = href.rstrip("/").split("/")[-1]
                if slug in seen_slugs or slug in ("motorcycle", ""):
                    continue
                seen_slugs.add(slug)

                name = clean(a_tag.get_text()) or slug.replace("-", " ").title()
                model_name = re.sub(r"\s*[\d,]+\s*บาท", "", name).strip()

                # ลอง guess category จาก slug
                cat = guess_category(slug)
                discovered.append({
                    "slug": slug,
                    "name": model_name,
                    "category": cat,
                    "price": "",
                    "url": f"{BASE_URL}{href}" if not href.startswith("http") else href,
                })

    if discovered:
        print(f"✅ Auto-discover พบ {len(discovered)} รุ่น")
        for i, m in enumerate(discovered, 1):
            print(f"   {i}. [{m['category']}] {m['name']} ({m['slug']})")
    else:
        print("⚠️ Auto-discover ไม่พบรุ่นรถเลย — จะใช้ fallback list แทน")

    return discovered


def guess_category(slug: str) -> str:
    """เดา category จาก slug"""
    s = slug.lower()
    if "ninja" in s or "zx" in s:
        return "Ninja"
    if s.startswith("z") and not s.startswith("zx"):
        return "Z"
    if "versys" in s:
        return "Versys"
    if "eliminator" in s:
        return "Eliminator"
    if "vulcan" in s:
        return "Vulcan"
    if "meguro" in s:
        return "MEGURO"
    if s.startswith("w") and len(s) <= 5:
        return "W"
    if "kle" in s:
        return "KLE"
    if "klr" in s:
        return "KLR"
    if "klx" in s:
        return "KLX"
    if "kx" in s:
        return "KX"
    return "Other"


# =========================
# Step 2: สกัด Specifications จาก div.kw-product-specification .wrapper
# =========================

def extract_specifications(soup) -> Dict[str, Dict[str, str]]:
    """
    สกัด specs จาก div.kw-product-specification > div.wrapper
    โครงสร้าง HTML:
        <div class="kw-product kw-product-specification">
          <div class="wrapper">
            <table>
              <tr><td colspan="2"> section header (มิติรถ / สมรรถนะ / เครื่องยนต์) </td></tr>
              <tr><td>spec_name</td><td>spec_value</td></tr>
              ...
            </table>
          </div>
        </div>
    Return: { "section_name": { "key": "value", ... }, ... }
    """
    specs_by_section = {}
    flat_specs = {}  # fallback flat dict

    # --- Target 1: div.kw-product-specification .wrapper ---
    spec_section = soup.select_one("div.kw-product-specification .wrapper")

    # fallback: ลองหาแค่ div.kw-product-specification
    if not spec_section:
        spec_section = soup.select_one("div.kw-product-specification")
    if not spec_section:
        spec_section = soup.select_one("[class*='specification'] .wrapper")
    if not spec_section:
        spec_section = soup.select_one("[class*='specification']")

    if not spec_section:
        return {"specs": {}}

    # --- อ่าน tables ภายใน ---
    current_section = "ทั่วไป"

    for table in spec_section.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])

            if len(cells) == 1:
                # แถว header ที่ colspan เต็ม (เช่น มิติรถ, สมรรถนะ, เครื่องยนต์)
                header_text = clean(cells[0].get_text())
                if header_text and len(header_text) < 80:
                    current_section = header_text
                    if current_section not in specs_by_section:
                        specs_by_section[current_section] = {}
                continue

            if len(cells) >= 2:
                key = clean(cells[0].get_text())
                val = clean(cells[1].get_text())
                if key and len(key) < 100:
                    if current_section not in specs_by_section:
                        specs_by_section[current_section] = {}
                    specs_by_section[current_section][key] = val
                    flat_specs[key] = val

    # --- ถ้า table ไม่มี ลอง dl/dt/dd ---
    if not flat_specs:
        for dt in spec_section.find_all("dt"):
            dd = dt.find_next_sibling("dd")
            if dd:
                key = clean(dt.get_text())
                val = clean(dd.get_text())
                if key:
                    flat_specs[key] = val

    # --- ถ้ายังไม่มี ลอง div pairs ---
    if not flat_specs:
        rows = spec_section.find_all("div", class_=re.compile(r"(row|item|spec)"))
        for row in rows:
            children = row.find_all("div", recursive=False)
            if len(children) >= 2:
                key = clean(children[0].get_text())
                val = clean(children[1].get_text())
                if key and len(key) < 100:
                    flat_specs[key] = val

    return specs_by_section if specs_by_section else {"specs": flat_specs}


def extract_price_from_page(soup) -> Dict:
    """
    ดึงราคาจากหน้ารุ่นรถ
    โครงสร้าง HTML:
        div.kw-product-color > div.wrapper >
            div.kw-product-color-price > h3 "ราคา (บาท)"
                > ul.kw-product-color-price-num
                    > li.kw-color-0.active  → "1,690,000"
                    > li.kw-color-1         → "1,700,000"  (สีอื่น)
    """
    result = {"price": "", "price_by_color": {}}

    # --- วิธี 1: ดึงจาก ul.kw-product-color-price-num (ตรง target) ---
    price_ul = soup.select_one("ul.kw-product-color-price-num")
    if price_ul:
        # ดึงราคาของสีที่ active อยู่
        active_li = price_ul.select_one("li.active")
        if active_li:
            price_text = clean(active_li.get_text())
            match = re.search(r"([\d,]+)", price_text)
            if match:
                result["price"] = f"{match.group(1)} บาท"

        # ดึงราคาทุกสี
        for li in price_ul.find_all("li"):
            price_text = clean(li.get_text())
            match = re.search(r"([\d,]+)", price_text)
            if match:
                # ดึงชื่อสีจาก class เช่น kw-color-0, kw-color-1
                classes = li.get("class", [])
                color_idx = next((c for c in classes if c.startswith("kw-color-")), "")
                result["price_by_color"][color_idx] = f"{match.group(1)} บาท"

    # --- วิธี 2: fallback — ดึงจาก div.kw-product-color-price ---
    if not result["price"]:
        price_div = soup.select_one("div.kw-product-color-price")
        if price_div:
            text = price_div.get_text()
            match = re.search(r"([\d,]+)", text)
            if match and len(match.group(1)) >= 4:  # อย่างน้อย 4 หลัก
                result["price"] = f"{match.group(1)} บาท"

    # --- วิธี 3: fallback — ดึงจาก div.kw-product-color ทั้งก้อน ---
    if not result["price"]:
        color_section = soup.select_one("div.kw-product-color")
        if color_section:
            text = color_section.get_text()
            match = re.search(r"([\d,]+)\s*(?:บาท)?", text)
            if match and len(match.group(1)) >= 4:
                result["price"] = f"{match.group(1)} บาท"

    # --- วิธี 4: fallback สุดท้าย — หาตัวเลขราคาทั่วหน้า ---
    if not result["price"]:
        for tag in soup.find_all(string=re.compile(r"[\d,]+\s*บาท")):
            text = tag if isinstance(tag, str) else tag.get_text()
            match = re.search(r"([\d,]+)\s*บาท", text)
            if match:
                result["price"] = f"{match.group(1)} บาท"
                break

    return result


def extract_colors_from_page(soup) -> List[str]:
    """
    ดึงสีที่มีให้เลือกจาก div.kw-product-color-head / div.kw-tabs
    โครงสร้าง: li.kw-color-0, li.kw-color-1 มีชื่อสีอยู่ข้างใน
    """
    colors = []

    # ลองจาก kw-tabs ใน COLOR & PRICE section
    tab_section = soup.select_one("div.kw-product-color div.kw-tabs")
    if tab_section:
        for li in tab_section.find_all("li"):
            color_name = clean(li.get_text())
            if color_name and color_name not in colors:
                colors.append(color_name)

    # fallback: ดึงจาก color swatches
    if not colors:
        for el in soup.select("div.kw-product-color-head li, [class*='color-swatch']"):
            text = clean(el.get_text())
            if text and len(text) < 80 and text not in colors:
                colors.append(text)

    return colors


def extract_model_name(soup, fallback: str) -> str:
    """ดึงชื่อรุ่นจากหน้า"""
    # ลองจาก kw-product-cover section
    cover = soup.select_one("section.kw-product-cover, .kw-product-intro")
    if cover:
        h1 = cover.find(["h1", "h2"])
        if h1:
            text = clean(h1.get_text())
            if text and len(text) < 100:
                return text

    # ลองจาก <title>
    title_tag = soup.find("title")
    if title_tag:
        text = title_tag.get_text(strip=True)
        # ตัด " | Kawasaki..." ออก
        name_part = text.split("|")[0].split("-")[0].strip()
        if name_part and len(name_part) < 100:
            return name_part

    return fallback


# =========================
# Step 3: สกัดข้อมูลจากหน้ารถแต่ละรุ่น
# =========================

def scrape_model_page(driver, model_info: Dict) -> Dict:
    """เข้าหน้ารุ่นรถ 1 รุ่น → scroll ลง → ดึง specs จาก wrapper"""
    slug = model_info["slug"]
    url = model_info.get("url", f"{BASE_URL}/th/motorcycle/{slug}")

    print(f"   📄 [{slug}] กำลังเปิดหน้า...")
    driver.get(url)
    time.sleep(4)

    # Scroll ลงเพื่อโหลด lazy content
    for i in range(4):
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {0.25 * (i + 1)});")
        time.sleep(0.8)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # ดึงข้อมูล
    name = extract_model_name(soup, model_info.get("name", slug))
    price_info = extract_price_from_page(soup)
    price = price_info["price"] or (f"{model_info['price']} บาท" if model_info.get("price") else "")
    specifications = extract_specifications(soup)
    colors = extract_colors_from_page(soup)

    # นับ specs ทั้งหมด
    total_specs = sum(len(v) for v in specifications.values() if isinstance(v, dict))

    print(f"   ชื่อรุ่น: {name}")
    print(f"   ราคา: {price or 'ไม่พบ'}")
    print(f"   สี: {', '.join(colors) if colors else 'ไม่พบ'}")
    print(f"   Specs: {total_specs} รายการ ({len(specifications)} หมวด)")

    return {
        "brand": "Kawasaki",
        "name": name,
        "slug": slug,
        "category": model_info.get("category", guess_category(slug)),
        "url": url,
        "price": price,
        "price_by_color": price_info.get("price_by_color", {}),
        "colors": colors,
        "specifications": specifications,
        "scraped_at": datetime.now().isoformat(),
    }


# =========================
# Main
# =========================

def main():
    print("=" * 70)
    print("🏍️  Kawasaki Thailand Motorcycle Scraper")
    print(f"   Source: {HOME_URL}")
    print("=" * 70)

    driver = create_driver(headless=True)

    try:
        # 1. Auto-discover รุ่นรถจาก sub-menu
        discovered = discover_models_from_submenu(driver)

        # ถ้า auto-discover ได้น้อยกว่า 10 รุ่น → ใช้ fallback list รวม
        if len(discovered) < 10:
            print(f"\n⚠️ Auto-discover ได้แค่ {len(discovered)} รุ่น — รวม fallback list")
            seen = {m["slug"] for m in discovered}
            for fb in FALLBACK_MODELS:
                if fb["slug"] not in seen:
                    fb["url"] = f"{BASE_URL}/th/motorcycle/{fb['slug']}"
                    discovered.append(fb)
                    seen.add(fb["slug"])
            print(f"   รวมทั้งหมด: {len(discovered)} รุ่น")

        models = discovered

        # 2. สกัดข้อมูลจากแต่ละรุ่น
        results = []
        errors = []
        total = len(models)
        print(f"\n🚀 เริ่มสกัดข้อมูลจาก {total} รุ่น...\n")

        for idx, model_info in enumerate(tqdm(models, desc="📊 สกัดข้อมูล"), 1):
            try:
                data = scrape_model_page(driver, model_info)
                results.append(data)

                total_specs = sum(len(v) for v in data["specifications"].values() if isinstance(v, dict))
                print(f"   ✅ [{idx}/{total}] {data['name']} — {total_specs} specs")

            except Exception as e:
                print(f"   ❌ [{idx}/{total}] {model_info.get('name', model_info['slug'])} — Error: {e}")
                errors.append({"model": model_info.get("name", ""), "slug": model_info["slug"], "error": str(e)})

            time.sleep(random.uniform(2.0, 4.0))

    finally:
        driver.quit()

    # 3. บันทึก JSON
    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"kawasaki_all_models_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Latest file (overwrite)
    latest_file = OUTPUT_DIR / "kawasaki_all_models.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 4. สรุป
    categories = {}
    for m in results:
        cat = m.get("category", "Other")
        categories.setdefault(cat, []).append(m)

    print("\n" + "=" * 70)
    print("📊 SCRAPING SUMMARY")
    print("=" * 70)
    print(f"   ✅ สกัดสำเร็จ: {len(results)} รุ่น")
    print(f"   ❌ Error: {len(errors)} รุ่น")
    print(f"   📁 บันทึกที่: {output_file}")
    print(f"   📁 Latest: {latest_file}")
    print("\n   📂 แยกตามหมวด:")
    for cat, models in sorted(categories.items()):
        print(f"      • {cat}: {len(models)} รุ่น")
    print("=" * 70)
    print("💡 ขั้นตอนถัดไป: รัน import_and_embedding_to_knowbase.py เพื่อสร้าง embedding และนำเข้า DB")
    print("=" * 70)


if __name__ == "__main__":
    main()
