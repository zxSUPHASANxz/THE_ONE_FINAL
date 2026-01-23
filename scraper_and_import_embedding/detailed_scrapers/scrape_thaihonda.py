import time
import re
import random
import json
from typing import Dict, List
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup


START_URL = "https://www.thaihonda.co.th/honda/motorcycle"


# ---------- Utils ----------
def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def extract_price(text: str):
    m = re.search(r"(\d{1,3}(?:,\d{3})+)\s*(THB|บาท)?", text)
    return f"{m.group(1)} บาท" if m else None


# ---------- Selenium Setup ----------
def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


# ---------- Step 1: Collect model URLs ----------
def collect_model_links(driver) -> List[str]:
    driver.get(START_URL)

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.TAG_NAME, "a"))
    )

    # scroll เพื่อให้โหลดครบ
    for _ in range(6):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.6)

    soup = BeautifulSoup(driver.page_source, "lxml")

    links = set()
    for a in soup.select("a[href*='/honda/motorcycle/']"):
        href = a.get("href")
        if href and not href.endswith("/motorcycle"):
            if href.startswith("/"):
                href = "https://www.thaihonda.co.th" + href
            links.add(href.split("#")[0])

    return sorted(links)


# ---------- Step 2: Parse model detail ----------
def parse_model_page(html: str, url: str) -> Dict:
    soup = BeautifulSoup(html, "lxml")

    # ชื่อรุ่น
    name = "UNKNOWN"
    for sel in ["h1", ".n_title", ".pd_title"]:
        node = soup.select_one(sel)
        if node:
            name = clean(node.get_text())
            break

    # ราคา
    price = None
    for node in soup.select("[class*='price'], .n_price"):
        p = extract_price(node.get_text())
        if p:
            price = p
            break

    # Specifications
    specs = {}

    spec_root = soup.select_one(".n_pd_spec")
    if spec_root:
        # ตาราง
        for row in spec_root.select("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) >= 2:
                k = clean(cols[0].get_text())
                v = clean(cols[1].get_text())
                specs[k] = v

        # fallback แบบ text
        if not specs:
            lines = [clean(x) for x in spec_root.stripped_strings]
            for i in range(0, len(lines) - 1, 2):
                specs.setdefault(lines[i], lines[i + 1])

    return {
        "url": url,
        "name": name,
        "price": price,
        "specs": specs
    }


# ---------- Step 3: Scrape all ----------
def scrape_all():
    driver = create_driver()

    try:
        model_links = collect_model_links(driver)
        print(f"พบรุ่นทั้งหมด: {len(model_links)}")

        results = []

        for i, url in enumerate(model_links, 1):
            print(f"[{i}/{len(model_links)}] {url}")
            driver.get(url)

            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(random.uniform(1.2, 2.0))

                data = parse_model_page(driver.page_source, url)
                results.append(data)

            except Exception as e:
                print(f"❌ Error page: {url} -> {e}")

        return results

    finally:
        driver.quit()


# ---------- Export ----------
def export(results: List[Dict]):
    # JSON (เหมาะกับ RAG)
    with open("thaihonda_models.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # CSV
    spec_keys = sorted({k for r in results for k in r["specs"].keys()})

    rows = []
    for r in results:
        row = {
            "name": r["name"],
            "price": r["price"],
            "url": r["url"]
        }
        for k in spec_keys:
            row[f"specs.{k}"] = r["specs"].get(k)
        rows.append(row)

    pd.DataFrame(rows).to_csv(
        "thaihonda_models.csv",
        index=False,
        encoding="utf-8-sig"
    )


# ---------- Run ----------
if __name__ == "__main__":
    data = scrape_all()
    export(data)
    print("✅ Scraping completed")
