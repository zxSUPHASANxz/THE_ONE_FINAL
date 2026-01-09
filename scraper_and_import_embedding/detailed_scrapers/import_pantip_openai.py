"""
Management command to import Pantip data with OpenAI embeddings
"""
import json
import os
from django.core.management.base import BaseCommand
from chatbot.models import KnowBase
from openai import OpenAI
import time
from typing import List
import warnings
warnings.filterwarnings("ignore")


class Command(BaseCommand):
    help = 'Import Pantip forum data with OpenAI text-embedding-3-large (1536 dimensions)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='scraper/database/pantip.json',
            help='Path to Pantip JSON file'
        )
        parser.add_argument(
            '--no-embed',
            action='store_true',
            help='Skip generating embeddings (import data only)'
        )
        parser.add_argument(
            '--openai-key',
            type=str,
            help='OpenAI API key (or set OPENAI_API_KEY env variable)'
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
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of records to import (0 = no limit)'
        )

    def generate_embedding(self, client: OpenAI, text: str, max_retries: int = 3) -> List[float]:
        """Generate embedding with OpenAI text-embedding-3-large"""
        for attempt in range(max_retries):
            try:
                response = client.embeddings.create(
                    model="text-embedding-3-large",
                    input=text,
                    dimensions=1536
                )
                return response.data[0].embedding
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
        api_key = options['openai_key'] or os.getenv('OPENAI_API_KEY')
        batch_size = options['batch_size']
        delay = options['delay']
        limit = options['limit']
        
        from django.conf import settings
        base_path = settings.BASE_DIR
        full_path = os.path.join(base_path, file_path)
        
        if not os.path.exists(full_path):
            self.stdout.write(self.style.ERROR(f'❌ File not found: {full_path}'))
            return
        
        self.stdout.write(self.style.WARNING(f'📂 Reading file: {full_path}'))
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                pantip_data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error reading file: {e}'))
            return
        
        if limit > 0:
            pantip_data = pantip_data[:limit]
            self.stdout.write(self.style.WARNING(f'⚠️  Limited to {limit} records'))
        
        self.stdout.write(self.style.SUCCESS(f'✅ Loaded {len(pantip_data)} records'))
        
        # Initialize OpenAI client
        client = None
        if not no_embed:
            if not api_key:
                self.stdout.write(self.style.ERROR('❌ OpenAI API key not provided'))
                return
            client = OpenAI(api_key=api_key)
            self.stdout.write(self.style.SUCCESS('✅ OpenAI client initialized'))
        
        self.stdout.write(self.style.WARNING(f'📦 Batch size: {batch_size}, Delay: {delay}s'))
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        for i, item in enumerate(pantip_data):
            topic_id = item.get('topic_id', str(i))
            title = item.get('title', f'Pantip Topic {topic_id}')
            
            # Build content
            content_parts = [title]
            if item.get('first_comment'):
                content_parts.append(item['first_comment'][:1000])
            
            # Add comments
            comments = item.get('comments', [])
            for j, comment in enumerate(comments[:5]):  # Max 5 comments
                if isinstance(comment, dict):
                    comment_text = comment.get('text', '')[:300]
                else:
                    comment_text = str(comment)[:300]
                content_parts.append(f"ความคิดเห็นที่ {j+1}: {comment_text}")
            
            content = '\n\n'.join(content_parts)
            
            # Truncate if too long
            if len(content) > 8000:
                content = content[:8000]
            
            # Generate embedding
            embedding = None
            if not no_embed and client:
                try:
                    embedding = self.generate_embedding(client, content)
                    time.sleep(delay)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Embedding error for {topic_id}: {e}'))
                    error_count += 1
                    continue
            
            # Determine source URL
            source_url = item.get('url', f'https://pantip.com/topic/{topic_id}')
            
            # Create or update record
            try:
                obj, created = KnowBase.objects.update_or_create(
                    title=title[:500],
                    source='pantip',
                    model=str(topic_id),
                    defaults={
                        'content': content,
                        'brand': 'pantip',
                        'category': item.get('tags', ['มอเตอร์ไซค์'])[0] if item.get('tags') else 'มอเตอร์ไซค์',
                        'source_url': source_url,
                        'embedding': embedding,
                        'raw_data': item,
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ DB error for {topic_id}: {e}'))
                error_count += 1
                continue
            
            # Progress update
            if (i + 1) % batch_size == 0:
                self.stdout.write(f'⏸️  Processed {i + 1}/{len(pantip_data)} records...')
                time.sleep(delay)
        
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Import completed!'))
        self.stdout.write(self.style.SUCCESS(f'📊 New records: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'🔄 Updated records: {updated_count}'))
        self.stdout.write(self.style.WARNING(f'❌ Errors: {error_count}'))
        
        total = KnowBase.objects.filter(is_active=True).count()
        with_embeddings = KnowBase.objects.filter(is_active=True, embedding__isnull=False).count()
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'📈 Total active records: {total}'))
        self.stdout.write(self.style.SUCCESS(f'🎯 Records with embeddings: {with_embeddings}'))
