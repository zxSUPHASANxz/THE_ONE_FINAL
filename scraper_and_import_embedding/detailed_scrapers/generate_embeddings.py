"""
Management command to generate embeddings for KnowlageDatabase using Google Gemini API
"""
import os
import time
from django.core.management.base import BaseCommand
from chatbot.models import KnowlageDatabase
from google import genai
from google.genai import types


class Command(BaseCommand):
    help = 'Generate embeddings for all records in KnowlageDatabase using Google Gemini'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process in each batch'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate embeddings even if they already exist'
        )
        parser.add_argument(
            '--api-key',
            type=str,
            help='Google Gemini API key (or set GEMINI_API_KEY env variable)'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        force = options['force']
        api_key = options['api_key'] or os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            self.stdout.write(self.style.ERROR(
                '❌ Error: Google Gemini API key not found!\n'
                'Please provide API key using --api-key or set GEMINI_API_KEY environment variable'
            ))
            return
        
        # Configure Gemini API
        client = genai.Client(api_key=api_key)
        
        # Get records to process
        if force:
            queryset = KnowlageDatabase.objects.filter(is_active=True)
            self.stdout.write(self.style.WARNING(f'🔄 Force mode: Processing all {queryset.count()} records'))
        else:
            queryset = KnowlageDatabase.objects.filter(is_active=True, embedding__isnull=True)
            self.stdout.write(self.style.WARNING(f'📊 Processing {queryset.count()} records without embeddings'))
        
        total_count = queryset.count()
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('✅ All records already have embeddings!'))
            return
        
        processed = 0
        errors = 0
        start_time = time.time()
        
        self.stdout.write(self.style.WARNING(f'\n🚀 Starting embedding generation...'))
        self.stdout.write(self.style.WARNING(f'⏱️  Estimated time: {total_count * 0.5 / 60:.1f} minutes\n'))
        
        for record in queryset.iterator(chunk_size=batch_size):
            try:
                # Combine title and content for embedding
                # Limit content length to avoid token limits
                text = f"{record.title}\n{record.content[:1500]}"
                
                # Add brand/model info if available
                if record.brand and record.model:
                    text = f"{record.brand} {record.model}\n{text}"
                
                # Generate embedding with Google Gemini (new API)
                response = client.models.embed_content(
                    model='text-embedding-004',
                    contents=text
                )
                
                # Update record with embedding
                record.embedding = response.embeddings[0].values
                record.save(update_fields=['embedding'])
                
                processed += 1
                
                # Progress indicator
                if processed % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    eta = (total_count - processed) / rate if rate > 0 else 0
                    
                    self.stdout.write(
                        f'\r📝 Progress: {processed}/{total_count} '
                        f'({processed*100//total_count}%) | '
                        f'Rate: {rate:.1f} rec/s | '
                        f'ETA: {eta/60:.1f} min',
                        ending=''
                    )
                    self.stdout.flush()
                
                # Rate limiting: ~2 requests per second
                time.sleep(0.5)
                
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f'\n❌ Error processing record {record.id}: {str(e)}')
                )
                
                # If too many errors, stop
                if errors > 10:
                    self.stdout.write(self.style.ERROR('\n❌ Too many errors, stopping...'))
                    break
                
                # Wait longer on error
                time.sleep(2)
        
        elapsed_time = time.time() - start_time
        
        self.stdout.write('\n')
        self.stdout.write(self.style.SUCCESS(f'\n✅ Embedding generation completed!'))
        self.stdout.write(self.style.SUCCESS(f'📊 Processed: {processed} records'))
        self.stdout.write(self.style.SUCCESS(f'⚠️  Errors: {errors}'))
        self.stdout.write(self.style.SUCCESS(f'⏱️  Time: {elapsed_time/60:.1f} minutes'))
        self.stdout.write(self.style.SUCCESS(f'📈 Rate: {processed/elapsed_time:.1f} records/second'))
        
        # Verify embeddings
        total_with_embeddings = KnowlageDatabase.objects.filter(
            is_active=True,
            embedding__isnull=False
        ).count()
        total_active = KnowlageDatabase.objects.filter(is_active=True).count()
        
        self.stdout.write(self.style.SUCCESS(
            f'\n🎯 Final status: {total_with_embeddings}/{total_active} records have embeddings'
        ))
