"""
Import Data into KnowBase with Gemini embeddings
================================================
Imports:
1. JSON files from 'database/'
2. PDF files from 'database/yamaha_manuals_pdf/'

Usage:
    python scraper_and_import_embedding/import_to_knowbase.py
"""

import os
import json
import time
import sys
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv
import django
import logging

logger = logging.getLogger(__name__)
from the_one.logging_config import setup_logging

# --- Setup Django Environment (Standalone Script) ---
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
load_dotenv(BASE_DIR / '.env')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_one.settings')
django.setup()

from chatbot.models import KnowBase

# --- Configuration ---
# Load GEMINI API key from environment only. Do NOT keep secrets in source.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    logger.critical("GEMINI_API_KEY not set. Add it to your .env or environment variables.")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

class KnowBaseImporter:
    def __init__(self, batch_size=5, delay=1.0):
        self.batch_size = batch_size
        self.delay = delay
        self.total_imported = 0
        self.total_updated = 0
        self.total_errors = 0

    def print_progress(self, current, total, prefix=""):
        if total == 0:
            return
        percent = int((current / total) * 100)
        logger.info("%s Progress: %d%% (%d/%d)", prefix, percent, current, total)

    def generate_embedding_with_retry(self, text: str, max_retries: int = 3):
        """Generate embedding with retry logic and exponential backoff"""
        from google.api_core.exceptions import PermissionDenied, InvalidArgument
        
        for attempt in range(max_retries):
            try:
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text
                )
                return result['embedding']
                    setup_logging()
                    main()
                logger.critical("\n\n❌ CRITICAL ERROR: API Key refused.")
                logger.critical("Your GEMINI_API_KEY has been reported as leaked or is invalid.")
                logger.critical("Please generate a new key at https://aistudio.google.com/app/apikey")
                logger.critical("Then update your .env file with the new key.")
                sys.exit(1) # Fatal error, stop immediately
            except InvalidArgument as e:
                logger.error("\n❌ Error: Invalid Argument: %s", e)
                return None # Skip this item
            except Exception as e:
                wait_time = (2 ** attempt) * 2
                if attempt < max_retries - 1:
                    logger.warning('⚠️  API error (attempt %d/%d): %s', attempt + 1, max_retries, str(e)[:200])
                    logger.warning('   Waiting %d s before retry...', wait_time)
                    time.sleep(wait_time)
                else:
                    logger.error('❌ Failed to generate embedding after %d attempts.', max_retries)
                    # Don't raise, just return None so we can continue with other items if possible?
                    # Or raise if we want to be strict. Let's return None to not break the loop.
                    return None

    def save_to_knowbase(self, title, content, source, brand, category, raw_data, model=None, url=None):
        try:
            # Check for existing duplicates with the same title and strictly clean them up if found
            # This prevents MultipleObjectsReturned error from update_or_create
            existing = KnowBase.objects.filter(title=title)
            if existing.count() > 1:
                logger.warning("  ⚠️ Found %d duplicates for '%s'. Cleaning up...", existing.count(), title)
                existing.delete() # Delete all to ensure clean state
            
            # Embed header/summary or first 2000 chars (safe limit)
            embedding_text = f"{title}\n{content[:2000]}"
            embedding = self.generate_embedding_with_retry(embedding_text)
            
            if not embedding:
                self.total_errors += 1
                return

            obj, created = KnowBase.objects.update_or_create(
                title=title,
                defaults={
                    'content': content,
                    'source': source,
                    'brand': brand,
                    'model': model,
                    'category': category,
                    'source_url': url,
                    'embedding': embedding,
                    'raw_data': raw_data,
                    'is_active': True
                }
            )

            if created:
                self.total_imported += 1
            else:
                self.total_updated += 1
                
        except Exception as e:
            self.total_errors += 1
            logger.exception("\n❌ Error saving %s: %s", title, e)

    def import_json_files(self, db_dir):
        logger.info("\n--- Importing JSON Files from %s ---", db_dir)
        json_files = list(db_dir.glob('*.json'))
        logger.info("Found %d JSON files.", len(json_files))

        total_records = 0
        current_count = 0
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                logger.error("\n❌ Error reading %s: %s", json_file.name, e)
                continue

            if isinstance(data, dict):
                data = [data]

            logger.info("\nProcessing %s (%d items)...", json_file.name, len(data))

            for i, item in enumerate(data):
                content = item.get('content', json.dumps(item, ensure_ascii=False))
                
                # Improved Title Generation
                # Prioritize explicit title -> model -> name -> filename + index
                candidate_title = item.get('title')
                if not candidate_title:
                   model_name = item.get('model')
                   name_val = item.get('name')
                   if model_name:
                       candidate_title = f"{item.get('brand', '')} {model_name}".strip()
                   elif name_val:
                       candidate_title = f"{item.get('brand', '')} {name_val}".strip()
                   else:
                       candidate_title = f"{json_file.stem} - Item {i+1}"
                
                title = candidate_title
                
                self.save_to_knowbase(
                    title=title,
                    content=content,
                    source=item.get('source', 'import'),
                    brand=item.get('brand'),
                    model=item.get('model'),
                    category=item.get('category'),
                    raw_data=item,
                    url=item.get('source_url') or item.get('url')
                )
                
                current_count += 1
                # Rate Limiting
                if current_count % self.batch_size == 0:
                    time.sleep(self.delay)

    def import_pdf_files(self, pdf_dir):
        if not pdf_dir.exists():
            logger.warning("\n⚠️ Directory not found: %s", pdf_dir)
            return

        logger.info("\n--- Importing PDF Files from %s ---", pdf_dir)
        import pdfplumber
        
        pdf_files = list(pdf_dir.glob('*.pdf'))
        logger.info("Found %d PDF files.", len(pdf_files))
        
        for i, pdf_file in enumerate(pdf_files):
            try:
                logger.info("Processing (%d/%d): %s", i+1, len(pdf_files), pdf_file.name)
                text = ""
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
                
                if not text.strip():
                    logger.info("  Skipping empty PDF: %s", pdf_file.name)
                    continue
                
                self.save_to_knowbase(
                    title=pdf_file.name,
                    content=text,
                    source='yamaha_manual',
                    brand='yamaha',
                    category='manual',
                    raw_data={'file': str(pdf_file.name)},
                    model=None
                )
                
                # Rate Limiting
                if (i + 1) % self.batch_size == 0:
                    time.sleep(self.delay)
                    
            except Exception as e:
                self.total_errors += 1
                logger.exception("\n❌ Error reading %s: %s", pdf_file.name, e)

    def fill_missing_embeddings(self):
        logger.info("\n--- Checking for Missing Embeddings ---")
        missing_count = KnowBase.objects.filter(embedding__isnull=True).count()
        if missing_count == 0:
            logger.info("✅ All records have embeddings.")
            return

        logger.info("found %d records without embeddings. Processing...", missing_count)
        
        # Process in chunks to avoid memory issues
        # Django's iterator() is good for this
        qs = KnowBase.objects.filter(embedding__isnull=True)
        
        for i, obj in enumerate(qs.iterator()):
            try:
            logger.info("Generating embedding for: %s...", obj.title[:50])
                embedding_text = f"{obj.title}\n{obj.content[:2000]}"
                embedding = self.generate_embedding_with_retry(embedding_text)
                
                if embedding:
                    obj.embedding = embedding
                    obj.save()
                    self.total_updated += 1
                    logger.info("  ✅ Saved embedding for %s", obj.id)
                else:
                    self.total_errors += 1
                    logger.warning("  ❌ Failed to generate embedding for %s", obj.id)
                
                # Rate Limiting
                if (i + 1) % self.batch_size == 0:
                    time.sleep(self.delay)
                    
            except Exception as e:
                self.total_errors += 1
                logger.exception("  ❌ Error processing %s: %s", obj.id, e)

    def run(self):
        db_dir = Path(__file__).parent / 'database'
        self.import_json_files(db_dir)
        
        pdf_dir = db_dir / 'yamaha_manuals_pdf'
        self.import_pdf_files(pdf_dir)
        
        # Sub-task: Fill missing embeddings
        self.fill_missing_embeddings()
        
        logger.info("\n" + "="*50)
        logger.info("✅ Import & Fix Cycle Completed")
        logger.info("📊 New: %d, Updated: %d, Errors: %d", self.total_imported, self.total_updated, self.total_errors)

if __name__ == "__main__":
    setup_logging()
    importer = KnowBaseImporter()
    importer.run()
