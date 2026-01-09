"""
Honda BigBike Scraper - Version 2
ปรับปรุงให้ดึง specifications ได้จริงตาม HTML structure ของ Honda
"""

import time
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from tqdm import tqdm


class HondaBigBikeV2:
    def __init__(self):
        self.brand = "Honda"
        self.base_url = "https://www.thaihonda.co.th/hondabigbike"
        self.motorcycles = []
    
    def setup_driver(self, headless=False):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)
    
    def get_model_list(self):
        """ดึงรายชื่อรุ่นทั้งหมด"""
        print(f"\n🔍 Fetching models from {self.base_url}/motorcycle")
        driver = self.setup_driver(headless=False)
        
        try:
            driver.get(f"{self.base_url}/motorcycle")
            time.sleep(5)
            
            # Scroll เพื่อโหลดทุกรุ่น
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # หา links ที่เป็นรุ่นรถ
            models = []
            seen = set()
            
            links = soup.find_all('a', href=re.compile(r'/motorcycle/'))
            
            for link in links:
                href = link.get('href', '')
                if not href or href in seen or href == '/motorcycle' or '/motorcycle' not in href:
                    continue
                
                # สร้าง URL
                if href.startswith('/'):
                    url = f"https://www.thaihonda.co.th{href}"
                elif href.startswith('http'):
                    url = href
                else:
                    continue
                
                # ดึงชื่อรุ่น
                model_name = link.get_text(strip=True) or link.get('title', '')
                if not model_name and link.find('img', alt=True):
                    model_name = link.find('img')['alt']
                
                if model_name and len(model_name) > 2:
                    models.append({
                        'model': model_name,
                        'url': url,
                        'brand': 'Honda'
                    })
                    seen.add(href)
            
            print(f"✅ Found {len(models)} models")
            return models
        
        finally:
            driver.quit()
    
    def extract_specs_from_honda(self, driver, soup):
        """ดึง specifications ตามโครงสร้างจริงของ Honda"""
        specs = {}
        
        # หา div ที่มี class="divspec" หรือมีข้อความ "ข้อมูลผลิตภัณฑ์"
        spec_sections = soup.find_all('div', class_=re.compile(r'spec|product|detail', re.I))
        
        # หาจาก text "ข้อมูลผลิตภัณฑ์"
        spec_headers = soup.find_all(text=re.compile(r'ข้อมูลผลิตภัณฑ์|specification|spec', re.I))
        
        print(f"  Found {len(spec_sections)} spec sections")
        print(f"  Found {len(spec_headers)} spec headers")
        
        # ลองคลิกปุ่ม/tab ข้อมูลผลิตภัณฑ์
        try:
            spec_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'ข้อมูล') or contains(text(), 'spec')]")
            for btn in spec_buttons[:3]:
                try:
                    driver.execute_script("arguments[0].scrollIntoView();", btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(2)
                    print(f"  Clicked spec button")
                except:
                    pass
        except:
            pass
        
        # Refresh soup หลังคลิก
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # หาทุก div ที่มี label-value pairs แบบ Honda
        # Honda ใช้โครงสร้างแบบ: <div>label</div><div>value</div> หรือ table rows
        
        # วิธีที่ 1: หา table rows
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    label = cols[0].get_text(strip=True)
                    value = cols[1].get_text(strip=True)
                    if label and value and len(label) < 200:
                        specs[label] = value
        
        # วิธีที่ 2: หา divs ที่มี pattern label-value
        # Honda อาจใช้ flex/grid layout
        all_divs = soup.find_all('div')
        for i, div in enumerate(all_divs):
            # ถ้า div มีข้อความสั้นๆ อาจเป็น label
            text = div.get_text(strip=True)
            if text and 5 < len(text) < 100 and ':' not in text:
                # หา div ถัดไปที่อาจเป็น value
                next_div = all_divs[i+1] if i+1 < len(all_divs) else None
                if next_div:
                    value = next_div.get_text(strip=True)
                    if value and len(value) < 200 and value != text:
                        # ตรวจสอบว่าเป็น spec จริง
                        if any(kw in text.lower() for kw in ['เครื่อง', 'ปริมาตร', 'ความ', 'ระบบ', 'อัตรา', 'engine', 'cc', 'dimension']):
                            specs[text] = value
        
        # วิธีที่ 3: หา dl/dt/dd
        dls = soup.find_all('dl')
        for dl in dls:
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            for dt, dd in zip(dts, dds):
                label = dt.get_text(strip=True)
                value = dd.get_text(strip=True)
                if label and value:
                    specs[label] = value
        
        print(f"  Extracted {len(specs)} specification items")
        return specs
    
    def scrape_single_model(self, url):
        """สกัดข้อมูลรุ่นเดียว"""
        print(f"\n{'='*80}")
        print(f"🏍️  Scraping: {url}")
        print(f"{'='*80}")
        
        driver = self.setup_driver(headless=False)
        
        try:
            driver.get(url)
            time.sleep(8)
            
            # หาชื่อรุ่นจาก h1
            try:
                model_name = driver.find_element(By.TAG_NAME, 'h1').text.strip()
                print(f"📝 Model: {model_name}")
            except:
                model_name = url.split('/')[-1]
                print(f"📝 Model (from URL): {model_name}")
            
            # Scroll ทั้งหน้า
            for i in range(3):
                driver.execute_script(f"window.scrollTo(0, {(i+1) * 1000});")
                time.sleep(1)
            
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # ดึงราคา
            price = None
            price_text = None
            price_patterns = [
                r'เริ่มต้น\s*([\d,]+)\s*บาท',
                r'ราคา\s*([\d,]+)\s*บาท',
                r'([\d,]+)\s*บาท'
            ]
            page_text = soup.get_text()
            for pattern in price_patterns:
                match = re.search(pattern, page_text)
                if match:
                    price = match.group(1).replace(',', '')
                    price_text = match.group(0)
                    print(f"💰 Price: {price_text}")
                    break
            
            # ดึง specifications
            specs = self.extract_specs_from_honda(driver, soup)
            
            # ดึง features
            features = []
            feature_elems = soup.find_all(['li', 'div', 'p'], class_=re.compile(r'feature|highlight', re.I))
            for elem in feature_elems[:20]:
                text = elem.get_text(strip=True)
                if text and len(text) > 15 and text not in features:
                    features.append(text)
            
            # ดึงรูปภาพ
            images = []
            img_elems = soup.find_all('img', src=re.compile(r'\.(jpg|png|webp)', re.I))
            for img in img_elems:
                src = img.get('src', '')
                if src and 'logo' not in src.lower() and 'icon' not in src.lower():
                    if not src.startswith('http'):
                        src = f"https://www.thaihonda.co.th{src}"
                    if src.startswith('http'):
                        images.append(src)
            
            # ดึงสี
            colors = []
            color_elems = soup.find_all(['div', 'span'], class_=re.compile(r'color', re.I))
            for elem in color_elems[:10]:
                color = elem.get('title') or elem.get_text(strip=True)
                if color and len(color) < 50:
                    colors.append(color)
            
            result = {
                'brand': 'Honda',
                'model': model_name,
                'url': url,
                'category': 'BigBike',
                'price': {
                    'price': price,
                    'price_text': price_text,
                    'currency': 'THB'
                },
                'specifications': specs,
                'features': features,
                'images': images[:15],
                'colors': colors,
                'description': ''
            }
            
            print(f"\n✅ Scraped successfully!")
            print(f"  - Specifications: {len(specs)} items")
            print(f"  - Features: {len(features)} items")
            print(f"  - Images: {len(images[:15])} items")
            print(f"  - Colors: {len(colors)} items")
            
            return result
        
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        finally:
            driver.quit()
    
    def save_json(self, data, filename='honda_single_test.json'):
        filepath = f"scraper/detailed_scrapers/{filename}"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Saved to {filepath}")


    def scrape_all_models(self, limit=None):
        """สกัดทุกรุ่นอัตโนมัติ"""
        print(f"\n{'='*80}")
        print("🏍️  HONDA BIGBIKE AUTO SCRAPER")
        print(f"{'='*80}")
        
        # ดึงรายชื่อรุ่นทั้งหมด
        models = self.get_model_list()
        
        if limit:
            models = models[:limit]
            print(f"\n⚡ Scraping {limit} models (limited)")
        else:
            print(f"\n🚀 Scraping ALL {len(models)} models")
        
        results = []
        
        for i, model in enumerate(models, 1):
            print(f"\n[{i}/{len(models)}]")
            result = self.scrape_single_model(model['url'])
            
            if result:
                results.append(result)
                self.motorcycles.append(result)
            
            # Rate limiting
            if i < len(models):
                print(f"⏳ Waiting 3 seconds...")
                time.sleep(3)
        
        return results


def main():
    import sys
    
    scraper = HondaBigBikeV2()
    
    # ตรวจสอบ arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--single':
            # สกัดรุ่นเดียว
            test_url = "https://www.thaihonda.co.th/hondabigbike/motorcycle/supersport/newcbr1000rr-rfirebladesp2024"
            result = scraper.scrape_single_model(test_url)
            if result:
                scraper.save_json(result, 'honda_single_test.json')
        elif sys.argv[1] == '--test':
            # ทดสอบ 3 รุ่น
            results = scraper.scrape_all_models(limit=3)
            scraper.save_json(results, 'honda_test_3models.json')
        elif sys.argv[1] == '--all':
            # สกัดทั้งหมด
            results = scraper.scrape_all_models()
            scraper.save_json(results, 'honda_bigbike_all.json')
    else:
        # Default: ทดสอบ 5 รุ่น
        print("Usage:")
        print("  --single  : Scrape single model (test)")
        print("  --test    : Scrape 3 models")
        print("  --all     : Scrape ALL models")
        print("\nRunning default: 5 models test\n")
        
        results = scraper.scrape_all_models(limit=5)
        scraper.save_json(results, 'honda_bigbike_test.json')
        
        # แสดงสรุป
        print(f"\n{'='*80}")
        print("📊 SUMMARY:")
        print(f"{'='*80}")
        print(f"✅ Scraped {len(results)} models")
        for r in results:
            print(f"  - {r['model']}: {len(r['specifications'])} specs, ฿{r['price']['price']}")


if __name__ == '__main__':
    main()
