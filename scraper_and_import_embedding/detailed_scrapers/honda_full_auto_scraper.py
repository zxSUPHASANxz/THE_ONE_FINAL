"""
Honda Motorcycle Full Auto Scraper with Embeddings
สกัดข้อมูลจาก https://www.thaihonda.co.th/honda/motorcycle
- ชื่อและราคาจาก div class="n_top"
- Specifications จาก div class="n_name" และ div class="value"
- สร้าง embeddings ด้วย Gemini API
- บันทึกเป็น JSON
"""
import os
import sys
import json
import time
import re
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_one.settings')
import django
django.setup()

import logging
import argparse
from typing import Optional

from the_one.logging_config import setup_logging

logger = logging.getLogger(__name__)

class HondaFullAutoScraper:
    def __init__(self):
        self.brand = "Honda"
        self.base_url = "https://www.thaihonda.co.th/honda/motorcycle"
        self.motorcycles = []
        self.driver = None
    
    def setup_driver(self, headless=False):
        """Setup Chrome WebDriver"""
        # Import heavy browser deps only when needed
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager

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
        logger.info("🔍 กำลังดึงรายการรถจาก %s", self.base_url)
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
            
            logger.info("✅ พบรถทั้งหมด %d รุ่น", len(model_urls))
            return model_urls
            
        except Exception:
            logger.exception("❌ เกิดข้อผิดพลาดในการดึงรายการรถ")
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
        
        except Exception:
            logger.exception("⚠️ ไม่สามารถดึงข้อมูลราคาได้")

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
        
        except Exception:
            logger.exception("⚠️ ไม่สามารถดึงข้อมูล specifications ได้")
        
        return specs
    
    def scrape_model_page(self, url):
        """สกัดข้อมูลจากหน้ารถแต่ละรุ่น"""
        try:
            logger.info("📄 กำลังดึงข้อมูลจาก: %s", url)
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
        except Exception:
            logger.exception("❌ เกิดข้อผิดพลาดในการดึงข้อมูลจาก %s", url)
            return None
    
    def create_embedding(self, text):
        """สร้าง embedding ด้วย Gemini API"""
        try:
            # Import and configure generative AI client only when needed
            import google.generativeai as genai

            gem_key = os.environ.get('GEMINI_API_KEY')
            if not gem_key:
                logger.warning("GEMINI_API_KEY not set; skipping embedding creation")
                return None

            genai.configure(api_key=gem_key)
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result.get('embedding')
        except Exception:
            logger.exception("⚠️ ไม่สามารถสร้าง embedding ได้")
            return None
    
    def prepare_text_for_embedding(self, motorcycle_data):
        """เตรียม text สำหรับสร้าง embedding"""
        text_parts = []
        
        # เพิ่มชื่อยี่ห้อและรุ่น
        text_parts.append(f"Brand: {motorcycle_data.get('brand', '')}")
        if 'model' in motorcycle_data:
            text_parts.append(f"Model: {motorcycle_data['model']}")
        
        # เพิ่มราคา
        if 'price' in motorcycle_data:
            text_parts.append(f"Price: {motorcycle_data['price']}")
        
        # เพิ่ม specifications
        if 'specifications' in motorcycle_data and motorcycle_data['specifications']:
            text_parts.append("Specifications:")
            for name, value in motorcycle_data['specifications'].items():
                text_parts.append(f"{name}: {value}")
        
        return "\n".join(text_parts)
    
    def scrape_all_models(self, create_embeddings=False):
        """สกัดข้อมูลจากรถทุกรุ่น"""
        # 1. ดึง URLs ของรถทั้งหมด
        model_urls = self.get_model_urls()
        
        if not model_urls:
            logger.error("❌ ไม่พบ URL ของรถ")
            return
        
        # 2. วนลูปดึงข้อมูลจากแต่ละรถ
        logger.info("🚀 เริ่มสกัดข้อมูลจาก %d รุ่น...", len(model_urls))
        if create_embeddings:
            logger.info("🤖 โหมด: สกัดข้อมูล + สร้าง embeddings")
        else:
            logger.info("⚠️ โหมด: สกัดข้อมูลอย่างเดียว (ไม่สร้าง embeddings)")

        from tqdm import tqdm

        for idx, url in enumerate(tqdm(model_urls, desc="📊 กำลังสกัดข้อมูล"), 1):
            motorcycle_data = self.scrape_model_page(url)
            
            if motorcycle_data:
                # สร้าง embedding (ถ้าเปิดใช้งาน)
                if create_embeddings:
                    text = self.prepare_text_for_embedding(motorcycle_data)
                    embedding = self.create_embedding(text)

                    if embedding:
                        motorcycle_data['embedding'] = embedding
                        motorcycle_data['embedding_dimension'] = len(embedding)
                
                self.motorcycles.append(motorcycle_data)
                logger.info("✅ [%d/%d] %s - เสร็จสิ้น", idx, len(model_urls), motorcycle_data.get('model', 'Unknown'))
            
            # Delay เพื่อไม่ให้ถูกบล็อก
            time.sleep(2)
        
        # 3. ปิด browser
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                logger.exception("Error while quitting driver")
    
    def save_to_json(self, filename='honda_motorcycles_full.json'):
        """บันทึกข้อมูลเป็น JSON file"""
        output_path = Path(__file__).parent / filename

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.motorcycles, f, ensure_ascii=False, indent=2)

            logger.info("✅ บันทึกข้อมูลสำเร็จ: %s", output_path)
            logger.info("📊 จำนวนรถทั้งหมด: %d รุ่น", len(self.motorcycles))

        except Exception:
            logger.exception("❌ ไม่สามารถบันทึกไฟล์ได้")
    
    def save_to_database(self):
        """บันทึกข้อมูลลง Django database"""
        logger.info("\n💾 กำลังบันทึกข้อมูลลงฐานข้อมูล...")
        saved_count = 0

        # Setup Django only when saving to DB
        try:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_one.settings')
            import django
            django.setup()
        except Exception:
            logger.exception("Failed to setup Django; database saving may fail")

        from chatbot.models import MotorcycleKnowledge

        for motorcycle in self.motorcycles:
            try:
                text = self.prepare_text_for_embedding(motorcycle)
                embedding = motorcycle.get('embedding')

                if not embedding:
                    logger.warning("⚠️ ข้าม %s - ไม่มี embedding", motorcycle.get('model'))
                    continue

                obj, created = MotorcycleKnowledge.objects.update_or_create(
                    source='honda_website',
                    brand=motorcycle.get('brand', 'Honda'),
                    model=motorcycle.get('model', 'Unknown'),
                    defaults={
                        'category': 'specifications',
                        'title': motorcycle.get('model', 'Unknown'),
                        'content': text,
                        'price': motorcycle.get('price', ''),
                        'specifications': json.dumps(motorcycle.get('specifications', {}), ensure_ascii=False),
                        'url': motorcycle.get('url', ''),
                        'embedding': embedding
                    }
                )

                saved_count += 1
                status = "สร้างใหม่" if created else "อัพเดท"
                logger.info("✅ %s: %s", status, motorcycle.get('model'))

            except Exception:
                logger.exception("❌ ไม่สามารถบันทึก %s ได้", motorcycle.get('model'))

        logger.info("\n✅ บันทึกข้อมูลเสร็จสิ้น: %d/%d รุ่น", saved_count, len(self.motorcycles))


def main():
    """Main function"""
    setup_logging()

    parser = argparse.ArgumentParser(description='Honda Motorcycle Full Auto Scraper')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--create-embeddings', action='store_true', help='Create embeddings using Gemini API')
    parser.add_argument('--save-db', action='store_true', help='Save results to Django database (requires embeddings)')
    args = parser.parse_args()

    logger.info("%s", "=" * 80)
    logger.info("🏍️  Honda Motorcycle Full Auto Scraper")
    logger.info("%s", "=" * 80)

    scraper = HondaFullAutoScraper()

    # 1. สกัดข้อมูล
    scraper.scrape_all_models(create_embeddings=args.create_embeddings)

    # 2. บันทึก JSON
    scraper.save_to_json()

    # 3. บันทึกลงฐานข้อมูล (เฉพาะกรณีมี embeddings)
    if args.create_embeddings and args.save_db:
        scraper.save_to_database()
    elif args.save_db and not args.create_embeddings:
        logger.warning('ข้าม: ไม่สามารถบันทึกลงฐานข้อมูลได้เนื่องจากไม่มี embeddings')

    logger.info("%s", "=" * 80)
    logger.info("✅ เสร็จสิ้นทั้งหมด!")
    logger.info("%s", "=" * 80)


if __name__ == "__main__":
    main()
