"""
Management command to import Honda BigBike data into KnowBase
"""
import json
import os
from django.core.management.base import BaseCommand
from chatbot.models import KnowBase
import google.generativeai as genai
import time
from typing import List


class Command(BaseCommand):
    help = 'Import Honda BigBike data from JSON file into KnowBase with Gemini embedding-001 (3072 dimensions)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='scraper/database/honda_bigbike_all.json',
            help='Path to Honda BigBike JSON file'
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

    def generate_embedding_with_retry(self, text: str, max_retries: int = 3) -> List[float]:
        """Generate embedding with retry logic and exponential backoff"""
        for attempt in range(max_retries):
            try:
                # ไม่ระบุ task_type เพื่อให้ match กับ n8n Embeddings node (ใช้ default)
                result = genai.embed_content(
                    model="models/gemini-embedding-001",
                    content=text
                )
                return result['embedding']
            except Exception as e:
                wait_time = (2 ** attempt) * 2  # 2, 4, 8 seconds
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
                honda_data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error reading file: {e}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'✅ Loaded {len(honda_data)} records'))
        
        # Configure Gemini if not skipping embeddings
        if not no_embed:
            if not api_key:
                self.stdout.write(self.style.ERROR(
                    '❌ API key required for embeddings. Use --gemini-key or set GEMINI_API_KEY'
                ))
                return
            genai.configure(api_key=api_key)
            self.stdout.write(self.style.SUCCESS('✅ Gemini 2.0 Flash configured'))
            self.stdout.write(self.style.SUCCESS(f'📦 Batch size: {batch_size}, Delay: {delay}s'))
        
        imported = 0
        updated = 0
        errors = 0
        
        for item in honda_data:
            try:
                # Extract data
                brand = item.get('brand', 'Honda')
                model_name = item.get('model', '')
                url = item.get('url', '')
                category = item.get('category', 'BigBike')
                
                # Build content
                title = f"{brand} {model_name}"
                content_parts = []
                
                # Price
                price_info = item.get('price', {})
                if price_info:
                    price_text = price_info.get('price_text', price_info.get('price', ''))
                    if price_text:
                        content_parts.append(f"ราคา: {price_text}")
                
                # Specifications
                specs = item.get('specifications', {})
                if specs:
                    content_parts.append("\n--- สเปคทั่วไป ---")
                    for key, value in list(specs.items())[:15]:  # Limit to 15 specs
                        content_parts.append(f"{key}: {value}")
                
                # Features
                features = item.get('features', [])
                if features:
                    content_parts.append("\n--- คุณสมบัติ ---")
                    for feature in features[:10]:  # Limit to 10 features
                        if isinstance(feature, str):
                            # Extract first 200 chars of feature
                            content_parts.append(f"• {feature[:200]}")
                
                content = '\n'.join(content_parts)
                
                # Create or update record
                obj, created = KnowBase.objects.update_or_create(
                    source='honda',
                    brand=brand,
                    model=model_name,
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
                        
                        # Batch rate limiting
                        if (imported + updated) % batch_size == 0:
                            self.stdout.write(self.style.WARNING(
                                f'⏸️  Processed {imported + updated} records, pausing {delay * 2}s...'
                            ))
                            time.sleep(delay * 2)
                        else:
                            time.sleep(delay)
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            f'❌ Failed to generate embedding for {model_name}: {str(e)[:100]}'
                        ))
                        errors += 1
                        continue
                
                if created:
                    imported += 1
                else:
                    updated += 1
                    
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f'❌ Error processing {item.get("model", "unknown")}: {e}'))
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'\n✅ Import completed!'))
        self.stdout.write(self.style.SUCCESS(f'📊 New records: {imported}'))
        self.stdout.write(self.style.SUCCESS(f'🔄 Updated records: {updated}'))
        if errors:
            self.stdout.write(self.style.WARNING(f'⚠️  Errors: {errors}'))
        
        # Final stats
        total = KnowBase.objects.filter(is_active=True).count()
        with_embeddings = KnowBase.objects.filter(is_active=True, embedding__isnull=False).count()
        
        self.stdout.write(self.style.SUCCESS(f'\n📈 Total active records: {total}'))
        self.stdout.write(self.style.SUCCESS(f'🎯 Records with embeddings: {with_embeddings}'))
