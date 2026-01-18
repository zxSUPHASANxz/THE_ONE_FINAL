"""
Auto Pantip Scraper - สกัดข้อมูลจาก Pantip อัตโนมัติ
รองรับการบันทึกลง Database และ JSON file
"""
import os
import sys
import django
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import time
import logging
from the_one.logging_config import setup_logging

logger = logging.getLogger(__name__)

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_one.settings')
django.setup()

from chatbot.models import Knowledgebase


class PantipScraper:
    """Scraper สำหรับ Pantip"""
    
    def __init__(self):
        self.base_url = "https://pantip.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'th,en-US;q=0.9,en;q=0.8',
        })
    
    def load_from_json(self, json_file='scraper/bigbike_faq_complete.json'):
        """โหลดข้อมูลจาก JSON ที่มีอยู่"""
        try:
            if not os.path.exists(json_file):
                logger.error("❌ ไม่พบไฟล์: %s", json_file)
                return []
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info("✅ โหลดข้อมูลจาก %s: %d records", json_file, len(data))
            return data
            
        except Exception as e:
            logger.exception("❌ Error loading JSON: %s", str(e))
            return []
    
    def transform_to_knowledgebase_format(self, item):
        """แปลงข้อมูลเป็นรูปแบบที่เหมาะสม"""
        try:
            # Extract from different formats
            if 'question' in item and 'answer' in item:
                # FAQ format
                title = item.get('question', '')
                content = item.get('answer', '')
                category = item.get('category', 'FAQ')
                url = item.get('url', f"https://pantip.com/topic/{item.get('id', 'unknown')}")
            elif 'title' in item:
                # Topic format
                title = item.get('title', '')
                content = item.get('content', item.get('description', ''))
                category = item.get('category', 'General')
                url = item.get('url', '')
            else:
                return None
            
            if not title or not content:
                return None
            
            data = {
                'title': title[:500],
                'content': content,
                'category': category,
                'url': url,
                'author': item.get('author', 'Unknown'),
                'views': item.get('views', 0),
                'replies': item.get('replies', 0),
                'likes': item.get('likes', item.get('votes', 0)),
                'tags': item.get('tags', []),
                'raw_data': item,
                'scraped_at': datetime.now().isoformat()
            }
            
            return data
            
        except Exception as e:
            logger.exception("❌ Transform error: %s", str(e))
            return None
    
    def save_to_database(self, data):
        """บันทึกลง Database"""
        try:
            # Check if already exists
            if Knowledgebase.objects.filter(source_url=data['url']).exists():
                return False
            
            # Create new record
            kb = Knowledgebase.objects.create(
                title=data['title'][:500],
                content=data['content'],
                category=data.get('category', ''),
                source='pantip',
                source_url=data['url'],
                author=data.get('author', '')[:200],
                views=data.get('views', 0),
                replies=data.get('replies', 0),
                likes=data.get('likes', 0),
                tags=data.get('tags', []),
                raw_data=data,
                is_active=True,
                is_verified=False
            )
            
            return True
            
        except Exception as e:
            logger.exception("  ❌ DB Error: %s", str(e)[:200])
            return False
    
    def save_to_json(self, all_data, filename='pantip_knowledge.json'):
        """บันทึกลงไฟล์ JSON"""
        try:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            
            logger.info("\n💾 บันทึกไฟล์: %s", filepath)
            logger.info("📊 จำนวน: %d records", len(all_data))
            return True
            
        except Exception as e:
            logger.exception("❌ JSON Error: %s", str(e))
            return False
    
    def run(self, json_source='scraper/bigbike_faq_complete.json', max_items=50, save_json=True):
        """รันการนำเข้าข้อมูลแบบอัตโนมัติ"""
        setup_logging()
        logger.info("%s", "="*70)
        logger.info("🤖 Pantip Auto Importer Started")
        logger.info("%s", "="*70)
        
        # Step 1: Load from JSON
        items = self.load_from_json(json_source)
        
        if not items:
            logger.warning("❌ ไม่มีข้อมูลให้ประมวลผล")
            return
        
        items = items[:max_items]  # Limit
        
        # Step 2: Transform and import
        logger.info("\n📥 กำลังนำเข้าข้อมูล %d รายการ...\n", len(items))
        
        processed_data = []
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for i, item in enumerate(items, 1):
            # Show title
            title = item.get('question', item.get('title', 'Unknown'))[:60]
            logger.info("[%d/%d] %s...", i, len(items), title)
            
            # Transform
            data = self.transform_to_knowledgebase_format(item)
            
            if not data:
                logger.warning("❌ ไม่สามารถแปลงข้อมูล")
                error_count += 1
                continue
            
            # Save to database
            if self.save_to_database(data):
                logger.info("✅ บันทึกสำเร็จ")
                success_count += 1
                processed_data.append(data)
            else:
                logger.info("⏭️ มีอยู่แล้ว")
                skip_count += 1
        
        # Step 3: Save to JSON
        if save_json and processed_data:
            self.save_to_json(processed_data)
        
        # Summary
        logger.info("\n" + "="*70)
        logger.info("📊 สรุปผลการนำเข้าข้อมูล")
        logger.info("="*70)
        logger.info("✅ สำเร็จ: %d", success_count)
        logger.info("⏭️ ข้ามไป (มีอยู่แล้ว): %d", skip_count)
        logger.info("❌ ล้มเหลว: %d", error_count)
        logger.info("📊 รวม: %d", len(items))
        logger.info("="*70)
        
        # Show database stats
        total = Knowledgebase.objects.count()
        logger.info("\n📚 ข้อมูลทั้งหมดในฐานข้อมูล: %d records", total)
        
        return processed_data


if __name__ == '__main__':
    scraper = PantipScraper()
    scraper.run(
        json_source='scraper/bigbike_faq_complete.json',
        max_items=50,
        save_json=True
    )
