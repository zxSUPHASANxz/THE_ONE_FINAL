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

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_one.settings')
django.setup()

from chatbot.models import KnowBase


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
                print(f"❌ ไม่พบไฟล์: {json_file}")
                return []
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"✅ โหลดข้อมูลจาก {json_file}: {len(data)} records")
            return data
            
        except Exception as e:
            print(f"❌ Error loading JSON: {str(e)}")
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
            print(f"❌ Transform error: {str(e)}")
            return None
    
    def save_to_database(self, data):
        """บันทึกลง Database"""
        try:
            # Check if already exists
            if KnowBase.objects.filter(source_url=data['url']).exists():
                return False
            
            # Create new record
            kb = KnowBase.objects.create(
                title=data['title'][:500],
                content=data['content'],
                category=data.get('category', ''),
                source='pantip',
                source_url=data['url'],
                raw_data={
                    'author': data.get('author', ''),
                    'views': data.get('views', 0),
                    'replies': data.get('replies', 0),
                    'likes': data.get('likes', 0),
                    'tags': data.get('tags', []),
                    'original': data
                },
                is_active=True
            )
            
            return True
            
        except Exception as e:
            print(f"  ❌ DB Error: {str(e)[:100]}")
            return False
    
    def save_to_json(self, all_data, filename='pantip_knowledge.json'):
        """บันทึกลงไฟล์ JSON"""
        try:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 บันทึกไฟล์: {filepath}")
            print(f"📊 จำนวน: {len(all_data)} records")
            return True
            
        except Exception as e:
            print(f"❌ JSON Error: {str(e)}")
            return False
    
    def run(self, json_source='scraper/bigbike_faq_complete.json', max_items=50, save_json=True):
        """รันการนำเข้าข้อมูลแบบอัตโนมัติ"""
        print("="*70)
        print("🤖 Pantip Auto Importer Started")
        print("="*70)
        
        # Step 1: Load from JSON
        items = self.load_from_json(json_source)
        
        if not items:
            print("❌ ไม่มีข้อมูลให้ประมวลผล")
            return
        
        items = items[:max_items]  # Limit
        
        # Step 2: Transform and import
        print(f"\n📥 กำลังนำเข้าข้อมูล {len(items)} รายการ...\n")
        
        processed_data = []
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for i, item in enumerate(items, 1):
            # Show title
            title = item.get('question', item.get('title', 'Unknown'))[:60]
            print(f"[{i}/{len(items)}] {title}...", end=' ')
            
            # Transform
            data = self.transform_to_knowledgebase_format(item)
            
            if not data:
                print("❌ ไม่สามารถแปลงข้อมูล")
                error_count += 1
                continue
            
            # Save to database
            if self.save_to_database(data):
                print("✅ บันทึกสำเร็จ")
                success_count += 1
                processed_data.append(data)
            else:
                print("⏭️ มีอยู่แล้ว")
                skip_count += 1
        
        # Step 3: Save to JSON
        if save_json and processed_data:
            self.save_to_json(processed_data)
        
        # Summary
        print("\n" + "="*70)
        print("📊 สรุปผลการนำเข้าข้อมูล")
        print("="*70)
        print(f"✅ สำเร็จ: {success_count}")
        print(f"⏭️ ข้ามไป (มีอยู่แล้ว): {skip_count}")
        print(f"❌ ล้มเหลว: {error_count}")
        print(f"📊 รวม: {len(items)}")
        print("="*70)
        
        # Show database stats
        total = KnowBase.objects.count()
        print(f"\n📚 ข้อมูลทั้งหมดในฐานข้อมูล: {total} records")
        
        return processed_data


if __name__ == '__main__':
    scraper = PantipScraper()
    scraper.run(
        json_source='scraper/bigbike_faq_complete.json',
        max_items=50,
        save_json=True
    )
