#!/usr/bin/env python3
"""
Pantip Motorcycle Scraper - Auto Search & Extract
สกัดข้อมูลจาก Pantip เกี่ยวกับมอเตอร์ไซด์ 150cc+ และบิ๊กไบค์
รองรับการค้นหาอัตโนมัติและสกัดเนื้อหาครบถ้วน
"""

import json
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def create_chrome_driver():
    """สร้าง Chrome WebDriver พร้อมการตั้งค่า"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver


def clean_text(text):
    """ทำความสะอาดข้อความ"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def search_pantip(driver, keywords, max_retries=3):
    """ค้นหากระทู้ใน Pantip ตามคำค้น"""
    logger.info("🔍 %s", keywords)
    
    search_url = f"https://pantip.com/search?q={keywords}"
    
    # Retry logic with exponential backoff
    for attempt in range(max_retries):
        try:
            driver.get(search_url)
            time.sleep(1.5)  # ลดจาก 3 เป็น 1.5
            break
        except Exception as e:
            error_msg = str(e).lower()
            # ถ้าเป็น session error ให้ raise เพื่อสร้าง driver ใหม่
            if 'session' in error_msg or 'invalid' in error_msg or 'disconnected' in error_msg:
                logger.error("❌ Session error: %s", str(e)[:200])
                raise Exception(f"RECREATE_DRIVER_NEEDED: {e}")

            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning("Retry %d...", attempt + 1)
                time.sleep(wait_time)
            else:
                raise e
    
    # Scroll เพื่อโหลดเนื้อหา - ลดจาก 3 เป็น 2 รอบ
    for _ in range(2):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)  # ลดจาก 2 เป็น 1
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # หากระทู้จากผลการค้นหา
    thread_links = []
    
    # วิธีที่ 1: หาจาก div.post-item
    posts = soup.find_all('div', class_='post-item')
    for post in posts:
        link = post.find('a', href=True)
        if link and '/topic/' in link.get('href'):
            full_url = f"https://pantip.com{link.get('href')}" if link.get('href').startswith('/') else link.get('href')
            if full_url not in thread_links:
                thread_links.append(full_url)
    
    # วิธีที่ 2: หาจาก a tag ที่มี /topic/
    if len(thread_links) == 0:
        links = soup.find_all('a', href=re.compile(r'/topic/\d+'))
        for link in links:
            full_url = f"https://pantip.com{link.get('href')}" if link.get('href').startswith('/') else link.get('href')
            # ตัดพารามิเตอร์ออก
            full_url = full_url.split('?')[0]
            if full_url not in thread_links:
                thread_links.append(full_url)
    
    logger.info("✅ พบ %d กระทู้", len(thread_links))
    return thread_links


def scrape_thread_content(driver, url, max_retries=2):
    """สกัดเนื้อหาจากกระทู้ Pantip"""
    for attempt in range(max_retries):
        try:
            logger.info("  🌐 เปิดกระทู้: %s", url)
            driver.get(url)
            
            # รอให้โหลดเนื้อหาด้วย WebDriverWait - เพิ่มเวลารอ
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "article"))
                )
            except:
                pass
            
            # รอเพิ่มสำหรับ lazy loading
            time.sleep(5)
            
            # Scroll หลายรอบเพื่อให้โหลด comments ทั้งหมด
            last_height = driver.execute_script("return document.body.scrollHeight")
            for i in range(5):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Scroll กลับขึ้นไปด้านบน
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            thread_data = {
                'url': url,
                'title': '',
                'author': '',
                'date': '',
                'views': 0,
                'comments_count': 0,
                'tags': [],
                'content': '',
                'comments': []
            }
            
            # Title - ใช้หลายวิธี
            title_tag = soup.find('h1', class_='display-post-title')
            if not title_tag:
                title_tag = soup.find('h1', class_=re.compile(r'title'))
            if not title_tag:
                title_tag = soup.find('h1')
            if title_tag:
                thread_data['title'] = clean_text(title_tag.get_text())
            
            # Author - หลายวิธี
            author_tag = soup.find('a', class_='owner')
            if not author_tag:
                author_tag = soup.find('div', class_='display-post-name')
            if not author_tag:
                author_tag = soup.find('a', class_=re.compile(r'author'))
            if author_tag:
                thread_data['author'] = clean_text(author_tag.get_text())
            
            # Date
            date_tag = soup.find('abbr', class_='timeago')
            if not date_tag:
                date_tag = soup.find('time')
            if date_tag:
                thread_data['date'] = date_tag.get('title', '') or date_tag.get('datetime', '')
            
            # Views
            views_tag = soup.find('span', class_='view-count')
            if views_tag:
                views_text = clean_text(views_tag.get_text())
                views_match = re.search(r'([\d,]+)', views_text)
                if views_match:
                    thread_data['views'] = int(views_match.group(1).replace(',', ''))
            
            # Comments count
            comment_count_tag = soup.find('span', class_='comments-count')
            if comment_count_tag:
                count_text = clean_text(comment_count_tag.get_text())
                count_match = re.search(r'(\d+)', count_text)
                if count_match:
                    thread_data['comments_count'] = int(count_match.group(1))
            
            # Tags
            tag_links = soup.find_all('a', class_='tag-item')
            if not tag_links:
                tag_links = soup.find_all('a', href=re.compile(r'/tag/'))
            thread_data['tags'] = [clean_text(tag.get_text()) for tag in tag_links if tag.get_text().strip()]
            
            # ===== เนื้อหาโพสต์หลัก =====
            # ลองหาหลายวิธี
            content_div = soup.find('div', class_='display-post-story')
            if not content_div:
                content_div = soup.find('div', class_=re.compile(r'post-story'))
            if not content_div:
                content_div = soup.find('div', attrs={'data-type': 'message'})
            if not content_div:
                # หาจาก article แล้วหา div แรก
                article = soup.find('article')
                if article:
                    content_div = article.find('div', class_=re.compile(r'(content|story|message|body)'))
            
            if content_div:
                # ลบ elements ที่ไม่ต้องการ
                for unwanted in content_div.find_all(['script', 'style', 'iframe']):
                    unwanted.decompose()
                
                # ดึงข้อความ - ใช้ get_text() แบบละเอียด
                content_text = content_div.get_text(separator='\n', strip=True)
                thread_data['content'] = clean_text(content_text)
            
            # ถ้ายังไม่ได้เนื้อหา ลองหาจาก paragraph ทั้งหมด
            if not thread_data['content'] or len(thread_data['content']) < 20:
                # หาทุก p tag ภายใน article หรือ main content
                main_content = soup.find('article') or soup.find('main') or soup
                paragraphs = []
                for p in main_content.find_all(['p', 'div'], class_=re.compile(r'(paragraph|text-display)')):
                    text = clean_text(p.get_text())
                    if text and len(text) > 15 and 'comment' not in p.get('class', []):
                        paragraphs.append(text)
                
                if paragraphs:
                    thread_data['content'] = '\n\n'.join(paragraphs[:10])  # เอาแค่ 10 paragraphs แรก
            
            # ===== คอมเมนต์ =====
            # ลองหาหลายวิธี
            comment_divs = soup.find_all('div', class_='comment-item')
            if not comment_divs:
                comment_divs = soup.find_all('div', class_=re.compile(r'comment-wrapper'))
            if not comment_divs:
                comment_divs = soup.find_all('article', class_=re.compile(r'comment'))
            if not comment_divs:
                # หาจาก div ที่มี id หรือ class เกี่ยวกับ comment
                comment_section = soup.find('div', id=re.compile(r'comment', re.I))
                if comment_section:
                    comment_divs = comment_section.find_all('div', recursive=True)
            
            comment_count = 0
            for comment_div in comment_divs:
                if comment_count >= 20:  # ลดจาก 30 เป็น 20 comments
                    break
                
                # หา author
                comment_author_tag = comment_div.find('a', class_=re.compile(r'(author|name|owner)'))
                if not comment_author_tag:
                    comment_author_tag = comment_div.find('span', class_=re.compile(r'(author|name|user)'))
                if not comment_author_tag:
                    comment_author_tag = comment_div.find('div', class_=re.compile(r'name'))
                
                # หา content
                comment_text_tag = comment_div.find('div', class_=re.compile(r'(story|content|text|message|body)'))
                if not comment_text_tag:
                    # ลองหาจาก p tags
                    comment_paragraphs = comment_div.find_all('p')
                    if comment_paragraphs:
                        comment_text_tag = comment_paragraphs[0].parent
                
                if comment_text_tag:
                    # ลบ elements ที่ไม่ต้องการ
                    for unwanted in comment_text_tag.find_all(['script', 'style', 'iframe']):
                        unwanted.decompose()
                    
                    comment_text = clean_text(comment_text_tag.get_text(separator='\n', strip=True))
                    
                    # เอาเฉพาะที่มีเนื้อหายาวพอ และไม่ใช่ metadata
                    if len(comment_text) > 20 and not re.match(r'^(Like|Reply|Report|Share|\d+)', comment_text):
                        comment_count += 1
                        thread_data['comments'].append({
                            'author': clean_text(comment_author_tag.get_text()) if comment_author_tag else 'Anonymous',
                            'content': comment_text
                        })
            
            return thread_data
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)  # ลดจาก 2 เป็น 1
                continue
            else:
                return None
    
    return None


def main():
    """ฟังก์ชันหลัก"""
    
    # คำค้นหาสำหรับมอเตอร์ไซด์ 150cc+ และบิ๊กไบค์ - เพิ่มเป็น 110+ คำ
    SEARCH_KEYWORDS = [
        # บิ๊กไบค์ทั่วไป
        "บิ๊กไบค์ แนะนำ",
        "บิ๊กไบค์ ปัญหา",
        "bigbike แนะนำ",
        "bigbike ปัญหา",
        "bigbike มือใหม่",
        "bigbike ซื้อคันแรก",
        "bigbike ราคาถูก",
        
        # มอเตอร์ไซด์ 150cc+
        "มอเตอร์ไซด์ 150cc",
        "มอเตอร์ไซด์ 250cc",
        "มอเตอร์ไซด์ 300cc",
        "มอเตอร์ไซด์ 400cc",
        "มอเตอร์ไซด์ 500cc",
        "มอเตอร์ไซด์ 650cc",
        
        # Kawasaki
        "ninja 250",
        "ninja 300",
        "ninja 400",
        "ninja 650",
        "ninja 1000",
        "z250",
        "z300",
        "z400",
        "z650",
        "z900",
        "versys 650",
        "versys 1000",
        "er6n",
        "er6f",
        
        # Honda
        "cbr150",
        "cbr250",
        "cbr300",
        "cbr500",
        "cbr650",
        "cbr1000",
        "cb150r",
        "cb300f",
        "cb500x",
        "cb650r",
        "rebel 300",
        "rebel 500",
        "pcx 150",
        "pcx 160",
        "forza 300",
        
        # Yamaha
        "r15",
        "r3",
        "r6",
        "r1",
        "mt-03",
        "mt-07",
        "mt-09",
        "mt-10",
        "xsr700",
        "xsr900",
        "tracer 700",
        "tracer 900",
        "aerox 155",
        "nmax 155",
        
        # Suzuki
        "gsx-r150",
        "gsx-s150",
        "gsx250r",
        "gsx-s750",
        "gsx-s1000",
        "sv650",
        "v-strom 650",
        "hayabusa",
        
        # KTM
        "duke 200",
        "duke 250",
        "duke 390",
        "duke 790",
        "rc 200",
        "rc 390",
        "adventure 390",
        
        # BMW
        "bmw s1000rr",
        "bmw f750gs",
        "bmw f850gs",
        "bmw r1250gs",
        
        # Ducati
        "ducati monster",
        "ducati panigale",
        "ducati scrambler",
        
        # Triumph
        "triumph street triple",
        "triumph speed triple",
        "triumph tiger",
        
        # Harley Davidson
        "harley davidson",
        "harley sportster",
        
        # หัวข้อทั่วไป
        "แนะนำมอไซ",
        "ปัญหามอไซ",
        "ซ่อมมอไซ",
        "ซื้อมอไซ",
        "เปรียบเทียบมอไซ",
        
        # === เพิ่มใหม่: การดูแลรักษา ===
        "ซ่อมบิ๊กไบค์",
        "เปลี่ยนถ่ายน้ำมันเครื่อง บิ๊กไบค์",
        "ล้างโซ่บิ๊กไบค์",
        "เช็คระยะบิ๊กไบค์",
        "บำรุงรักษาบิ๊กไบค์",
        "ดูแลบิ๊กไบค์",
        
        # === เพิ่มใหม่: อะไหล่/อุปกรณ์ ===
        "ยางบิ๊กไบค์",
        "แบตเตอรี่บิ๊กไบค์",
        "ไฟหน้าบิ๊กไบค์",
        "ท่อบิ๊กไบค์",
        "เบรคบิ๊กไบค์",
        "ผ้าเบรคบิ๊กไบค์",
        "โช้คบิ๊กไบค์",
        "คลัตช์บิ๊กไบค์",
        
        # === เพิ่มใหม่: ปัญหา/แก้ไข ===
        "บิ๊กไบค์ดับ",
        "บิ๊กไบค์สตาร์ทไม่ติด",
        "เครื่องบิ๊กไบค์ร้อน",
        "บิ๊กไบค์เสียงดัง",
        "บิ๊กไบค์สั่น",
        "เกียร์บิ๊กไบค์เข้ายาก",
        
        # === รุ่นรถยอดนิยมเพิ่มเติม ===
        "xmax 300",
        "tmax 560",
        "msx 125",
        "monkey 125",
        "grom",
        "benelli tnt 150",
        "benelli 302r",
        "cfmoto 300nk",
        "gpx gentleman 200",
        "gpx legend 250",
        
        # === การใช้งาน ===
        "บิ๊กไบค์ทัวร์ริ่ง",
        "บิ๊กไบค์ไกลแดน",
        "บิ๊กไบค์ขึ้นดอย",
        "ขับบิ๊กไบค์ในเมือง",
        "บิ๊กไบค์ผู้หญิง",
        "บิ๊กไบค์คนตัวเล็ก",
        "บิ๊กไบค์คนเตี้ย",
        
        # === ค่าใช้จ่าย/ประกัน ===
        "ค่าบำรุงรักษาบิ๊กไบค์",
        "ประกันบิ๊กไบค์",
        "ภาษีบิ๊กไบค์",
        "ค่าน้ำมันบิ๊กไบค์",
        "ซื้อบิ๊กไบค์ผ่อน",
        "บิ๊กไบค์มือสอง",
        
        # === อุปกรณ์ Safety ===
        "หมวกกันน็อคบิ๊กไบค์",
        "เสื้อการ์ดบิ๊กไบค์",
        "ถุงมือบิ๊กไบค์",
        "รองเท้าบู๊ทบิ๊กไบค์",
        "ABS บิ๊กไบค์",
        
        # === ปัญหาเฉพาะ ===
        "บิ๊กไบค์น้ำมันรั่ว",
        "ยางบิ๊กไบค์แตก",
        "คลัตช์บิ๊กไบค์ลื่น",
        "เบรคบิ๊กไบค์อ่อน",
        "ไฟบิ๊กไบค์ไม่ติด",
        "แบตบิ๊กไบค์หมด",
    ]
    
    OUTPUT_FILE = "pantip.json"
    MAX_THREADS_PER_KEYWORD = 100  # ลดจาก 15 เป็น 10 เพื่อความเร็ว
    RECREATE_DRIVER_EVERY = 10  # สร้าง driver ใหม่ทุก 10 คำค้น (ลดจาก 20)
    AUTO_SAVE_EVERY = 5  # บันทึกข้อมูลทุก 5 keywords
    
    logger.info("%s", "=" * 80)
    logger.info("🚀 Pantip Motorcycle Scraper - FAST MODE")
    logger.info("%s", "=" * 80)
    logger.info("📋 คำค้นหา: %d คำ", len(SEARCH_KEYWORDS))
    logger.info("🎯 เป้าหมาย: มอเตอร์ไซด์ 150cc+ และบิ๊กไบค์")
    logger.info("📁 Output: %s", OUTPUT_FILE)
    logger.info("🔢 สูงสุด %d กระทู้/คำค้น", MAX_THREADS_PER_KEYWORD)
    logger.info("%s", "=" * 80 + "\n")
    
    driver = create_chrome_driver()
    
    all_threads = []
    seen_urls = set()
    start_time = datetime.now()
    
    try:
        for idx, keyword in enumerate(SEARCH_KEYWORDS):
            # Progress percentage
            progress = (idx / len(SEARCH_KEYWORDS)) * 100
            
            # ETA calculation
            if idx > 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                avg_time = elapsed / idx
                remaining = len(SEARCH_KEYWORDS) - idx
                eta_seconds = avg_time * remaining
                eta_str = f"{int(eta_seconds//60)}m {int(eta_seconds%60)}s"
            else:
                eta_str = "คำนวณ..."
            
            logger.info("\n[%5.1f%%] [%d/%d] ETA: %s | ", progress, idx+1, len(SEARCH_KEYWORDS), eta_str)
            
            # สร้าง driver ใหม่ทุก N keywords
            if idx > 0 and idx % RECREATE_DRIVER_EVERY == 0:
                logger.info("\n🔄 Driver refresh...")
                try:
                    driver.quit()
                except:
                    pass
                time.sleep(2)
                driver = create_chrome_driver()
                logger.info("OK")
                time.sleep(2)
            
            # Auto-save ทุก N keywords
            if idx > 0 and idx % AUTO_SAVE_EVERY == 0 and all_threads:
                logger.info("\n💾 Auto-save... (%d กระทู้)", len(all_threads))
                try:
                    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                        json.dump(all_threads, f, ensure_ascii=False, indent=2)
                    logger.info("✅")
                except Exception as e:
                    logger.error("❌ %s", e)
            
            # ค้นหากระทู้
            try:
                thread_urls = search_pantip(driver, keyword)
            except Exception as e:
                error_msg = str(e)
                logger.error("❌ Error: %s", error_msg[:200])
                
                # ถ้าเป็น session error หรือมีคำว่า RECREATE_DRIVER_NEEDED
                if 'RECREATE_DRIVER_NEEDED' in error_msg or 'session' in error_msg.lower() or 'invalid' in error_msg.lower() or 'disconnected' in error_msg.lower():
                    logger.info("🔄 Recreating driver due to session error...")
                    try:
                        driver.quit()
                    except:
                        pass
                    time.sleep(3)
                    driver = create_chrome_driver()
                    logger.info("✅ Driver recreated")
                    
                    # ลองอีกครั้งหลังสร้าง driver ใหม่
                    try:
                        thread_urls = search_pantip(driver, keyword)
                    except Exception as retry_error:
                        logger.error("❌ Retry failed: %s", str(retry_error)[:200])
                        continue
                else:
                    continue
                time.sleep(2)
                try:
                    thread_urls = search_pantip(driver, keyword)
                except:
                    logger.warning("Skip after retry")
                    continue
            
            logger.info("→ %d กระทู้", len(thread_urls))
            
            # จำกัดจำนวน
            thread_urls = thread_urls[:MAX_THREADS_PER_KEYWORD]
            
            # สกัดเนื้อหาแต่ละกระทู้
            total_threads = len(thread_urls)
            
            for i, url in enumerate(thread_urls, 1):
                # ข้ามถ้าเจอซ้ำ
                if url in seen_urls:
                    continue
                
                seen_urls.add(url)
                logger.info("  [%d/%d]", i, len(thread_urls))
                
                # ลองสกัดเนื้อหา ถ้า error ให้สร้าง driver ใหม่
                thread_data = None
                try:
                    thread_data = scrape_thread_content(driver, url)
                except Exception as e:
                    logger.exception("  ❌ Error: %s", e)
                    logger.info("  🔄 สร้าง driver ใหม่...")
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = create_chrome_driver()
                    time.sleep(2)
                    # ลองอีกครั้ง
                    try:
                        thread_data = scrape_thread_content(driver, url)
                    except:
                        logger.info("  ⏭️  ข้ามกระทู้นี้")
                
                if thread_data and thread_data.get('content'):
                    all_threads.append(thread_data)
                    logger.info("✅ %s... (%d chars)", thread_data['title'][:50], len(thread_data['content']))
                else:
                    logger.info("⏭️ Skip (no content)")
                
                # พักเล็กน้อย
                time.sleep(1)  # ลดจาก 2 เป็น 1
            
            # สรุปสั้นๆ
            logger.info("  → รวม: %d กระทู้ | ไม่ซ้ำ: %d URLs", len(all_threads), len(seen_urls))
        
        # บันทึกลงไฟล์
        logger.info("\n💾 กำลังบันทึกข้อมูล...")
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_threads, f, ensure_ascii=False, indent=2)
        
        logger.info("\n%s", "=" * 80)
        logger.info("✅ สำเร็จ! บันทึกข้อมูลลงไฟล์: %s", OUTPUT_FILE)
        logger.info("📊 จำนวนกระทู้ทั้งหมด: %d", len(all_threads))
        
        # สถิติ
        import os
        file_size = os.path.getsize(OUTPUT_FILE)
        logger.info("📁 ขนาดไฟล์: %d bytes (%.2f KB)", file_size, file_size/1024)
        
        total_content = sum(len(t['content']) for t in all_threads)
        total_comments = sum(len(t['comments']) for t in all_threads)
        total_views = sum(t['views'] for t in all_threads)
        
        logger.info("\n📈 สถิติ:")
        logger.info("  - เนื้อหาโพสต์รวม: %d ตัวอักษร", total_content)
        logger.info("  - ความคิดเห็นรวม: %d comments", total_comments)
        logger.info("  - ยอดวิวรวม: %d ครั้ง", total_views)
        logger.info("  - เฉลี่ยต่อกระทู้: %d ตัวอักษร", (total_content//len(all_threads) if all_threads else 0))
        logger.info("  - comments ต่อกระทู้: %.1f", (total_comments//len(all_threads) if all_threads else 0))
        
        # สรุปยี่ห้อรถที่พบ
        brands_found = {}
        brand_keywords = ['honda', 'yamaha', 'kawasaki', 'suzuki', 'ktm', 'ducati', 'bmw', 'triumph', 'harley']
        for thread in all_threads:
            title_lower = thread['title'].lower()
            for brand in brand_keywords:
                if brand in title_lower:
                    brands_found[brand] = brands_found.get(brand, 0) + 1
        
        if brands_found:
            logger.info("\n🏍️  ยี่ห้อที่พบมากที่สุด:")
            for brand, count in sorted(brands_found.items(), key=lambda x: x[1], reverse=True)[:5]:
                logger.info("  - %s: %d กระทู้", brand.upper(), count)
        
        # แสดงตัวอย่าง
        logger.info("\n📋 กระทู้ที่สกัดได้ (แสดง 5 อันดับแรก):")
        for i, thread in enumerate(all_threads[:5], 1):
            logger.info("\n  %d. %s", i, thread['title'])
            logger.info("     📍 URL: %s", thread['url'])
            logger.info("     👤 ผู้เขียน: %s", thread['author'])
            logger.info("     👁  ยอดวิว: %d", thread['views'])
            logger.info("     💬 ความคิดเห็น: %d", thread['comments_count'])
            logger.info("     📝 เนื้อหา: %d ตัวอักษร", len(thread['content']))
            if thread['tags']:
                logger.info("     🏷  Tags: %s", ', '.join(thread['tags'][:5]))
        
        if len(all_threads) > 5:
            logger.info("\n  ... และอีก %d กระทู้", len(all_threads) - 5)

        logger.info("\n🏁 เสร็จสิ้น")
        logger.info("%s", "=" * 80)
        
    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  ถูกยกเลิกโดยผู้ใช้")
        logger.info("💾 บันทึกข้อมูลที่สกัดได้แล้ว %d กระทู้...", len(all_threads))
        
        try:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_threads, f, ensure_ascii=False, indent=2)
            logger.info("✅ บันทึกเรียบร้อยแล้ว: %s", OUTPUT_FILE)
        except Exception as save_error:
            logger.error("❌ บันทึกไม่สำเร็จ: %s", save_error)
        
    except Exception as e:
        logger.exception("\n❌ เกิดข้อผิดพลาด: %s", e)
        import traceback
        traceback.print_exc()
        
        # พยายามบันทึกข้อมูลที่มีอยู่
        if all_threads:
            logger.info("\n💾 พยายามบันทึกข้อมูลที่สกัดได้...")
            try:
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(all_threads, f, ensure_ascii=False, indent=2)
                logger.info("✅ บันทึกเรียบร้อยแล้ว: %d กระทู้", len(all_threads))
            except Exception as save_error:
                logger.error("❌ บันทึกไม่สำเร็จ: %s", save_error)
    
    finally:
        # ปิด driver อย่างปลอดภัย
        try:
            driver.quit()
        except:
            pass  # Ignore errors when quitting driver


if __name__ == "__main__":
    setup_logging()
    main()
