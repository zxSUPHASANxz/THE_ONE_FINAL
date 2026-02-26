"""
Management command to import Honda BigBike data with Gemini embedding-001 (3072 dimensions)
"""
import json
import os
from django.core.management.base import BaseCommand
from chatbot.models import KnowBase
import google.generativeai as genai
import time
from typing import List
import warnings
warnings.filterwarnings("ignore")


class Command(BaseCommand):
    help = 'Import Honda BigBike data with Gemini embedding-001 (3072 dimensions)'

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
            default=10,
            help='Number of records to process before pause'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='Delay in seconds between API calls'
        )

    def generate_embedding(self, text: str, max_retries: int = 3) -> List[float]:
        """Generate embedding with Gemini embedding-001 (3072 dimensions)"""
        for attempt in range(max_retries):
            try:
                result = genai.embed_content(
                    model="models/gemini-embedding-001",
                    content=text,
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
                honda_data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error reading file: {e}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'✅ Loaded {len(honda_data)} records'))
        
        # Initialize Gemini
        if not no_embed:
            if not api_key:
                self.stdout.write(self.style.ERROR('❌ Gemini API key not provided'))
                return
            genai.configure(api_key=api_key)
            self.stdout.write(self.style.SUCCESS('✅ Gemini client initialized'))
        
        self.stdout.write(self.style.WARNING(f'📦 Batch size: {batch_size}, Delay: {delay}s'))
        
        created_count = 0
        updated_count = 0
        
        for i, item in enumerate(honda_data):
            # Build content for embedding
            name = item.get('name', '')
            price = item.get('price', '')
            colors = ', '.join(item.get('colors', []))
            engine = item.get('engine', {})
            engine_info = f"Engine: {engine.get('type', '')} {engine.get('displacement', '')} {engine.get('power', '')} {engine.get('torque', '')}"
            transmission = item.get('transmission', {})
            trans_info = f"Transmission: {transmission.get('type', '')} {transmission.get('gears', '')}"
            
            content = f"""
Honda {name}
ราคา: {price}
สีที่มี: {colors}
{engine_info}
{trans_info}
""".strip()
            
            # Generate embedding
            embedding = None
            if not no_embed:
                try:
                    embedding = self.generate_embedding(content)
                    time.sleep(delay)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Embedding error for {name}: {e}'))
                    continue
            
            # Create or update record
            obj, created = KnowBase.objects.update_or_create(
                title=f"Honda {name}",
                source='honda',
                defaults={
                    'content': content,
                    'brand': 'Honda',
                    'model': name,
                    'category': 'BigBike',
                    'source_url': item.get('url', ''),
                    'embedding': embedding,
                    'raw_data': item,
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
            
            # Progress update
            if (i + 1) % batch_size == 0:
                self.stdout.write(f'⏸️  Processed {i + 1} records, pausing {delay * 2}s...')
                time.sleep(delay * 2)
        
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Import completed!'))
        self.stdout.write(self.style.SUCCESS(f'📊 New records: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'🔄 Updated records: {updated_count}'))
        
        total = KnowBase.objects.filter(is_active=True).count()
        with_embeddings = KnowBase.objects.filter(is_active=True, embedding__isnull=False).count()
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'📈 Total active records: {total}'))
        self.stdout.write(self.style.SUCCESS(f'🎯 Records with embeddings: {with_embeddings}'))
