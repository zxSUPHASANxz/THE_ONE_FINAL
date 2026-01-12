"""
Import Thai Honda Motorcycle data into KnowBase with Gemini embeddings
=====================================================================
สำหรับข้อมูลจาก thaihonda.co.th (รถจักรยานยนต์ Honda ทุกรุ่น)
ใช้กับไฟล์ thaihonda_all_models.json

รันด้วย: python manage.py import_thaihonda --file scraper_and_import_embedding/database/thaihonda_all_models.json
"""
import json
import os
import re
import time
from typing import List, Dict
from django.core.management.base import BaseCommand
from chatbot.models import KnowBase
import google.generativeai as genai


class Command(BaseCommand):
    help = 'Import Thai Honda motorcycle data from JSON file into KnowBase with Gemini embeddings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='scraper_and_import_embedding/database/thaihonda_all_models.json',
            help='Path to Thai Honda JSON file'
        )
        parser.add_argument(
            '--no-embed',
            action='store_true',
            help='Skip generating embeddings (import data only)'
        )
        parser.add_argument(
            '--gemini-key',
            type=str,
            help='Gemini API key (or set GEMINI_API_KEY env variable)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=5,
            help='Number of records to process before rate limit pause'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Delay in seconds between API calls'
        )

    def clean_specs(self, specs: Dict) -> Dict[str, str]:
        """
        ทำความสะอาด specifications ที่มี key/value ติดกัน
        """
        cleaned = {}
        
        # Common spec keys to look for
        spec_patterns = {
            r'เครื่องยนต์': 'เครื่องยนต์',
            r'ปริมาตรกระบอกสูบ.*?(\d[\d,\.]+)': 'ปริมาตรกระบอกสูบ (ซีซี)',
            r'ความกว้างกระบอกสูบ.*?(\d+[\d\.\,x ]+)': 'ความกว้างกระบอกสูบ x ช่วงชัก',
            r'อัตราส่วนแรงอัด.*?(\d+[\.\:\d ]+)': 'อัตราส่วนแรงอัด',
            r'ระบบคลัทช์(.+?)(?:ระบบ|$)': 'ระบบคลัทช์',
            r'ระบบส่งกำลัง.*?(.+?)(?:ระบบ|$)': 'ระบบส่งกำลัง',
            r'ขนาด กว้าง.*?(\d+[,\. x\d]+)': 'ขนาด กว้าง x ยาว x สูง (มม.)',
            r'ระยะห่างช่วงล้อ.*?(\d+[,\.\d]+)': 'ระยะห่างช่วงล้อ (มม.)',
            r'ความสูงของเบาะ.*?(\d+[,\.\d]+)': 'ความสูงของเบาะ (มม.)',
            r'น้ำหนักสุทธิ.*?(\d+[,\.\d]+)': 'น้ำหนักสุทธิ (กก.)',
            r'ระบบห้ามล้อ.*?หน้า.*?(.+?)(?:ระบบ|$)': 'ระบบเบรกหน้า',
            r'ระบบห้ามล้อ.*?หลัง.*?(.+?)(?:ระบบ|$)': 'ระบบเบรกหลัง',
            r'ขนาดยาง.*?หน้า.*?(.+?)(?:ขนาด|$)': 'ขนาดยางหน้า',
            r'ขนาดยาง.*?หลัง.*?(.+?)$': 'ขนาดยางหลัง',
        }
        
        for key, value in specs.items():
            # Skip overly long or duplicate keys
            if len(key) > 100 or key == value:
                continue
            
            # Clean basic key/value
            clean_key = re.sub(r'\s+', ' ', key).strip()
            clean_value = re.sub(r'\s+', ' ', str(value)).strip()
            
            if clean_key and clean_value and len(clean_key) < 80:
                cleaned[clean_key] = clean_value
        
        return cleaned

    def format_content(self, item: Dict) -> str:
        """
        สร้าง content string สำหรับ embedding และ RAG
        """
        parts = []
        
        name = item.get('name', '')
        price = item.get('price', '')
        category = item.get('category', '')
        
        # Header
        parts.append(f"รุ่น: {name}")
        if price:
            parts.append(f"ราคา: {price}")
        if category:
            parts.append(f"ประเภท: {category}")
        
        # Colors
        colors = item.get('colors', [])
        if colors:
            parts.append(f"สีที่มี: {', '.join(colors)}")
        
        # Specifications
        specs = item.get('specifications', {})
        if specs:
            parts.append("\n--- สเปค ---")
            cleaned_specs = self.clean_specs(specs)
            for key, value in list(cleaned_specs.items())[:20]:  # Limit to 20 specs
                parts.append(f"{key}: {value}")
        
        return '\n'.join(parts)

    def generate_embedding_with_retry(self, text: str, max_retries: int = 3) -> List[float]:
        """Generate embedding with retry logic and exponential backoff"""
        for attempt in range(max_retries):
            try:
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text
                )
                return result['embedding']
            except Exception as e:
                wait_time = (2 ** attempt) * 2
                if attempt < max_retries - 1:
                    self.stdout.write(self.style.WARNING(
                        f'⚠️  API error (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}'
                    ))
                    self.stdout.write(self.style.WARNING(f'   Waiting {wait_time}s before retry...'))
                    time.sleep(wait_time)
                else:
                    raise

    def handle(self, *args, **options):
        file_path = options['file']
        no_embed = options['no_embed']
        api_key = options['gemini_key'] or os.getenv('GEMINI_API_KEY')
        batch_size = options['batch_size']
        delay = options['delay']
        
        from django.conf import settings
        base_path = settings.BASE_DIR
        full_path = os.path.join(base_path, file_path)
        
        if not os.path.exists(full_path):
            self.stdout.write(self.style.ERROR(f'❌ File not found: {full_path}'))
            return
        
        self.stdout.write(self.style.WARNING(f'📂 Reading file: {full_path}'))
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error reading file: {e}'))
            return
        
        # Handle both list and dict formats
        if isinstance(data, dict):
            if 'motorcycles' in data:
                honda_data = data['motorcycles']
            else:
                honda_data = [data]
        else:
            honda_data = data
        
        self.stdout.write(self.style.SUCCESS(f'✅ Loaded {len(honda_data)} records'))
        
        # Configure Gemini if not skipping embeddings
        if not no_embed:
            if not api_key:
                self.stdout.write(self.style.ERROR(
                    '❌ API key required for embeddings. Use --gemini-key or set GEMINI_API_KEY'
                ))
                return
            genai.configure(api_key=api_key)
            self.stdout.write(self.style.SUCCESS('✅ Gemini configured'))
            self.stdout.write(self.style.SUCCESS(f'📦 Batch size: {batch_size}, Delay: {delay}s'))
        
        imported = 0
        updated = 0
        errors = 0
        
        for i, item in enumerate(honda_data):
            try:
                # Extract data
                name = item.get('name', '').strip()
                if not name or name == 'UNKNOWN':
                    continue
                
                url = item.get('url', '')
                category = item.get('category', 'มอเตอร์ไซค์')
                price = item.get('price', '')
                
                # Build title
                title = f"Honda {name}"
                
                # Build content
                content = self.format_content(item)
                
                # Create or update record
                obj, created = KnowBase.objects.update_or_create(
                    source='thaihonda',
                    brand='Honda',
                    model=name,
                    defaults={
                        'title': title,
                        'content': content,
                        'category': category,
                        'source_url': url,
                        'raw_data': item,
                        'is_active': True,
                    }
                )
                
                # Generate embedding if not skipping
                if not no_embed:
                    try:
                        # Build text for embedding
                        embed_text = f"{title}\n{content[:3000]}"
                        
                        # Generate embedding with retry
                        embedding = self.generate_embedding_with_retry(embed_text)
                        
                        # Update embedding
                        obj.embedding = embedding
                        obj.save(update_fields=['embedding'])
                        
                        # Progress log
                        self.stdout.write(f'  ✓ [{i+1}/{len(honda_data)}] {name}')
                        
                        # Batch rate limiting
                        if (imported + updated + 1) % batch_size == 0:
                            self.stdout.write(self.style.WARNING(
                                f'⏸️  Processed {imported + updated + 1} records, pausing {delay * 2}s...'
                            ))
                            time.sleep(delay * 2)
                        else:
                            time.sleep(delay)
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            f'❌ Failed to generate embedding for {name}: {str(e)[:100]}'
                        ))
                        errors += 1
                        continue
                
                if created:
                    imported += 1
                else:
                    updated += 1
                    
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(
                    f'❌ Error processing {item.get("name", "unknown")}: {e}'
                ))
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'\n✅ Import completed!'))
        self.stdout.write(self.style.SUCCESS(f'📊 New records: {imported}'))
        self.stdout.write(self.style.SUCCESS(f'🔄 Updated records: {updated}'))
        if errors:
            self.stdout.write(self.style.WARNING(f'⚠️  Errors: {errors}'))
        
        # Final stats
        total = KnowBase.objects.filter(source='thaihonda', is_active=True).count()
        with_embeddings = KnowBase.objects.filter(
            source='thaihonda', 
            is_active=True, 
            embedding__isnull=False
        ).count()
        
        self.stdout.write(self.style.SUCCESS(f'\n📈 Total thaihonda records: {total}'))
        self.stdout.write(self.style.SUCCESS(f'🎯 Records with embeddings: {with_embeddings}'))
