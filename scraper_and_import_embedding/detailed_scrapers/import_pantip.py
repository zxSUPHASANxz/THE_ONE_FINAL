"""
Management command to import Pantip data into KnowBase
"""
import json
import os
from django.core.management.base import BaseCommand
from chatbot.models import KnowBase
import google.generativeai as genai
import time
from typing import List
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)


class Command(BaseCommand):
    help = 'Import Pantip forum data from JSON file into KnowBase with Gemini embeddings'

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
                    model="models/text-embedding-004",
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
                pantip_data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error reading file: {e}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'✅ Loaded {len(pantip_data)} records'))
        
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
        
        for item in pantip_data:
            try:
                # Extract data
                title = item.get('title', 'ไม่มีหัวข้อ')
                url = item.get('url', '')
                author = item.get('author', '')
                views = item.get('views', 0)
                comments_count = item.get('comments_count', 0)
                
                # Build content
                content_parts = [item.get('content', '')]
                
                # Add comments
                comments = item.get('comments', [])
                if comments:
                    content_parts.append('\n\n--- ความคิดเห็น ---')
                    for i, comment in enumerate(comments[:10], 1):  # Limit to 10 comments
                        comment_text = comment.get('content', '')
                        if comment_text:
                            content_parts.append(f"\nคอมเมนต์ {i}: {comment_text[:200]}")
                
                content = '\n'.join(content_parts)
                
                # Create unique identifier from URL
                source_id = url.split('/')[-1] if url else f'pantip_{imported + updated}'
                
                # Create or update record
                obj, created = KnowBase.objects.update_or_create(
                    source='pantip',
                    source_url=url,
                    defaults={
                        'title': title,
                        'content': content[:10000],  # Limit content length
                        'category': 'มอเตอร์ไซค์',
                        'brand': 'pantip',
                        'model': source_id,
                        'raw_data': {
                            'author': author,
                            'views': views,
                            'comments_count': comments_count,
                            **item
                        },
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
                            f'❌ Failed to generate embedding for {title[:50]}: {str(e)[:100]}'
                        ))
                        errors += 1
                        continue
                
                if created:
                    imported += 1
                else:
                    updated += 1
                    
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f'❌ Error processing item: {e}'))
        
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
        pantip_count = KnowBase.objects.filter(source='pantip', is_active=True).count()
        
        self.stdout.write(self.style.SUCCESS(f'\n📈 Total active records: {total}'))
        self.stdout.write(self.style.SUCCESS(f'🎯 Records with embeddings: {with_embeddings}'))
        self.stdout.write(self.style.SUCCESS(f'📰 Pantip records: {pantip_count}'))
