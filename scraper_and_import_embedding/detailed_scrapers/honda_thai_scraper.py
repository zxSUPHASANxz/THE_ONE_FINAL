"""
Honda Motorcycle Full Auto Scraper
สกัดข้อมูลจาก https://www.thaihonda.co.th/honda/motorcycle
- ชื่อและราคาจาก div class="n_top"
- Specifications จาก div class="n_name" และ div class="value"
- บันทึกเป็น JSON

หมายเหตุ: ไฟล์นี้ทำหน้าที่สกัดข้อมูลเท่านั้น (Scraping Only)
          การสร้าง Embedding และนำเข้า DB ใช้ import_and_embedding_to_knowbase.py
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
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from tqdm import tqdm

class HondaFullAutoScraper:
    def __init__(self):
        self.brand = "Honda"
        self.base_url = "https://www.thaihonda.co.th/honda/motorcycle"
        self.motorcycles = []
        self.driver = None
    
    def setup_driver(self, headless=False):
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
        return webdriver.Chrome(service=service, options=chrome_options)
    
    def get_model_urls(self):
        """ดึง URL ของรถทุกรุ่นจากหน้าหลัก"""
        print(f"\n🔍 กำลังดึงรายการรถจาก {self.base_url}")
        self.driver = self.setup_driver(headless=False)
        
        try:
            self.driver.get(self.base_url)
            time.sleep(5)
            
            # Scroll เพื่อโหลดรถทั้งหมด
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # ดึง link ของรถแต่ละรุ่น
            model_urls = []
            
            # ค้นหา links ในหน้า products/motorcycles
            # จากรูปภาพเห็นว่ารถอยู่ใน section ต่างๆ เช่น "เกียร์อัตโนมัติ", "โปรดักส์ใหม่", etc.
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                # ดึงเฉพาะ link ที่เป็นหน้ารถ เช่น /honda/motorcycle/sport/new-cbr250rr-2023
                if '/honda/motorcycle/' in href and href != '/honda/motorcycle':
                    full_url = f"https://www.thaihonda.co.th{href}" if not href.startswith('http') else href
                    if full_url not in model_urls:
                        model_urls.append(full_url)
            
            print(f"✅ พบรถทั้งหมด {len(model_urls)} รุ่น")
            return model_urls
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการดึงรายการรถ: {e}")
            return []
    
    def extract_price_from_n_top(self, soup):
        """ดึงชื่อและราคาจาก top section (เช่น 'CBR250RR SP | start 269,000 THB')"""
        price_info = {}
        
        try:
            # วิธีที่ 1: หาจาก h1, h2, h3 ที่มีราคา
            headers = soup.find_all(['h1', 'h2', 'h3', 'div'], class_=re.compile(r'(title|top|price|model)', re.I))
            
            for header in headers:
                text = header.get_text(strip=True)
                
                # ถ้าพบ pattern "ชื่อรุ่น | start xxx THB" หรือ "ชื่อรุ่น | เริ่มต้น xxx บาท"
                if '|' in text and ('start' in text.lower() or 'เริ่มต้น' in text or 'THB' in text or 'บาท' in text):
                    parts = text.split('|')
                    if len(parts) >= 2:
                        # ส่วนแรกเป็นชื่อรุ่น
                        price_info['model'] = parts[0].strip()
                        
                        # ส่วนที่สองมีราคา
                        price_part = parts[1].strip()
                        price_match = re.search(r'([\d,]+)', price_part)
                        if price_match:
                            price_num = price_match.group(1).replace(',', '')
                            price_info['price'] = {
                                'price': price_num,
                                'price_text': price_part,
                                'currency': 'THB'
                            }
                    break
            
            # วิธีที่ 2: หาแยก - ชื่อจาก h1/h2/h3, ราคาจาก div/span
            if not price_info.get('model'):
                title_tags = soup.find_all(['h1', 'h2', 'h3'], limit=3)
                for tag in title_tags:
                    text = tag.get_text(strip=True)
                    # ถ้ามีความยาวพอสมควรและไม่มีราคา
                    if 5 < len(text) < 100 and not re.search(r'\d{3,}', text):
                        price_info['model'] = text
                        break
            
            if not price_info.get('price'):
                # หาราคา
                price_tags = soup.find_all(text=re.compile(r'(start|เริ่มต้น|THB|฿|บาท).*\d'))
                for tag in price_tags:
                    text = tag if isinstance(tag, str) else tag.get_text(strip=True)
                    price_match = re.search(r'([\d,]+)\s*(THB|฿|บาท)', text)
                    if price_match:
                        price_num = price_match.group(1).replace(',', '')
                        price_info['price'] = {
                            'price': price_num,
                            'price_text': text.strip(),
                            'currency': 'THB'
                        }
                        break
        
        except Exception as e:
            print(f"⚠️ ไม่สามารถดึงข้อมูลราคาได้: {e}")
        
        return price_info
    
    def extract_specifications(self, soup):
        """ดึง Specifications จาก table/div structure"""
        specs = {}
        
        try:
            # วิธีที่ 1: ดึงจาก table rows (จากรูปตัวอย่าง)
            # หา table ที่มี specifications
            spec_tables = soup.find_all('table') + soup.find_all('div', class_='n_container')
            
            for table in spec_tables:
                rows = table.find_all('tr') if table.name == 'table' else table.find_all('div', class_='n_desc')
                
                for row in rows:
                    # หา cell ซ้าย (ชื่อฟิลด์) และขวา (ค่า)
                    if row.name == 'tr':
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            name = cells[0].get_text(strip=True)
                            value = cells[1].get_text(strip=True)
                            if name and value:
                                specs[name] = value
                    else:
                        # div structure
                        name_div = row.find('div', class_='n_name')
                        value_div = row.find('div', class_='value')
                        
                        if name_div and value_div:
                            name = name_div.get_text(strip=True)
                            value = value_div.get_text(strip=True)
                            if name and value:
                                specs[name] = value
            
            # วิธีที่ 2: ถ้ายังไม่พบ ลองหาจาก dl/dt/dd
            if not specs:
                dts = soup.find_all('dt')
                dds = soup.find_all('dd')
                
                for dt, dd in zip(dts, dds):
                    name = dt.get_text(strip=True)
                    value = dd.get_text(strip=True)
                    if name and value:
                        specs[name] = value
            
            # วิธีที่ 3: ลองหาจาก div pairs ที่อยู่ติดกัน
            if not specs:
                all_divs = soup.find_all('div')
                for i in range(len(all_divs) - 1):
                    div1 = all_divs[i]
                    div2 = all_divs[i + 1]
                    
                    # ถ้า div แรกมี class ที่บอกว่าเป็น label/name
                    if 'label' in div1.get('class', []) or 'name' in div1.get('class', []):
                        if 'value' in div2.get('class', []) or 'data' in div2.get('class', []):
                            name = div1.get_text(strip=True)
                            value = div2.get_text(strip=True)
                            if name and value and len(name) < 100:  # ไม่ยาวเกินไป
                                specs[name] = value
        
        except Exception as e:
            print(f"⚠️ ไม่สามารถดึงข้อมูล specifications ได้: {e}")
        
        return specs
    
    def scrape_model_page(self, url):
        """สกัดข้อมูลจากหน้ารถแต่ละรุ่น"""
        try:
            print(f"\n📄 กำลังดึงข้อมูลจาก: {url}")
            self.driver.get(url)
            time.sleep(5)
            
            # Scroll ลงไปเพื่อโหลด specifications
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 1. ดึงชื่อและราคาจาก n_top
            price_info = self.extract_price_from_n_top(soup)
            
            # 2. ดึง specifications
            specs = self.extract_specifications(soup)
            
            # 3. Extract model slug from URL
            model_slug = url.split('/')[-1]
            
            # 4. ดึง features (ถ้ามี)
            features = []
            feature_sections = soup.find_all('div', class_='feature') or soup.find_all('div', class_='highlight')
            for section in feature_sections:
                feature_text = section.get_text(strip=True)
                if feature_text:
                    features.append(feature_text)
            
            # 5. ดึงรูปภาพ (ถ้ามี)
            images = []
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src', '')
                if src and ('motorcycle' in src or 'honda' in src):
                    images.append(src)
            
            # 6. ดึงสีที่มี (ถ้ามี)
            colors = []
            color_divs = soup.find_all('div', class_='color') or soup.find_all('div', class_='n_color')
            for color_div in color_divs:
                color_text = color_div.get_text(strip=True)
                if color_text:
                    colors.append(color_text)
            
            # 7. รวมข้อมูลในรูปแบบเดียวกับ honda_bigbike_all.json
            motorcycle_data = {
                'brand': self.brand,
                'model': model_slug,
                'url': url,
                'category': 'Motorcycle',
                'scraped_at': datetime.now().isoformat(),
                **price_info,
                'specifications': specs,
                'features': features if features else [],
                'images': images if images else [],
                'colors': colors if colors else [],
                'description': ''
            }
            
            return motorcycle_data
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการดึงข้อมูลจาก {url}: {e}")
            return None
    
    def scrape_all_models(self):
        """สกัดข้อมูลจากรถทุกรุ่น"""
        # 1. ดึง URLs ของรถทั้งหมด
        model_urls = self.get_model_urls()
        
        if not model_urls:
            print("❌ ไม่พบ URL ของรถ")
            return
        
        # 2. วนลูปดึงข้อมูลจากแต่ละรถ
        print(f"\n🚀 เริ่มสกัดข้อมูลจาก {len(model_urls)} รุ่น...")
        
        for idx, url in enumerate(tqdm(model_urls, desc="📊 กำลังสกัดข้อมูล"), 1):
            motorcycle_data = self.scrape_model_page(url)
            
            if motorcycle_data:
                self.motorcycles.append(motorcycle_data)
                print(f"✅ [{idx}/{len(model_urls)}] {motorcycle_data.get('model', 'Unknown')} - เสร็จสิ้น")
            
            # Delay เพื่อไม่ให้ถูกบล็อก
            time.sleep(2)
        
        # 3. ปิด browser
        if self.driver:
            self.driver.quit()
    
    def save_to_json(self, filename='honda_motorcycles_full.json'):
        """บันทึกข้อมูลเป็น JSON file"""
        output_path = Path(__file__).parent.parent / "database" / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.motorcycles, f, ensure_ascii=False, indent=2)
            
            print(f"\n✅ บันทึกข้อมูลสำเร็จ: {output_path}")
            print(f"📊 จำนวนรถทั้งหมด: {len(self.motorcycles)} รุ่น")
            
        except Exception as e:
            print(f"❌ ไม่สามารถบันทึกไฟล์ได้: {e}")


def main():
    """Main function"""
    print("=" * 80)
    print("🏍️  Honda Motorcycle Full Auto Scraper")
    print("=" * 80)
    
    scraper = HondaFullAutoScraper()
    
    # 1. สกัดข้อมูล
    scraper.scrape_all_models()
    
    # 2. บันทึก JSON
    scraper.save_to_json()
    
    print("\n" + "=" * 80)
    print("✅ สกัดข้อมูลเสร็จสิ้น!")
    print("💡 ขั้นตอนถัดไป: รัน import_and_embedding_to_knowbase.py เพื่อสร้าง embedding และนำเข้า DB")
    print("=" * 80)


if __name__ == "__main__":
    main()
