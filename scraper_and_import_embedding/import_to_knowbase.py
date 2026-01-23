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

# --- Setup Django Environment (Standalone Script) ---
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
load_dotenv(BASE_DIR / '.env')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_one.settings')
django.setup()

from chatbot.models import KnowBase

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in .env")
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
        print(f"{prefix} Progress: {percent}% ({current}/{total})", end='\r')

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
            except PermissionDenied:
                print("\n\n❌ CRITICAL ERROR: API Key refused.")
                print("Your GEMINI_API_KEY has been reported as leaked or is invalid.")
                print("Please generate a new key at https://aistudio.google.com/app/apikey")
                print("Then update your .env file with the new key.")
                sys.exit(1) # Fatal error, stop immediately
            except InvalidArgument as e:
                print(f"\n❌ Error: Invalid Argument: {e}")
                return None # Skip this item
            except Exception as e:
                wait_time = (2 ** attempt) * 2
                if attempt < max_retries - 1:
                    print(f'\n⚠️  API error (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}')
                    print(f'   Waiting {wait_time}s before retry...')
                    time.sleep(wait_time)
                else:
                    print(f'\n❌ Failed to generate embedding after {max_retries} attempts.')
                    # Don't raise, just return None so we can continue with other items if possible?
                    # Or raise if we want to be strict. Let's return None to not break the loop.
                    return None

    def save_to_knowbase(self, title, content, source, brand, category, raw_data, model=None, url=None):
        try:
            # Check for existing duplicates with the same title and strictly clean them up if found
            # This prevents MultipleObjectsReturned error from update_or_create
            existing = KnowBase.objects.filter(title=title)
            if existing.count() > 1:
                print(f"  ⚠️ Found {existing.count()} duplicates for '{title}'. Cleaning up...")
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
            print(f"\n❌ Error saving {title}: {e}")

    def import_json_files(self, db_dir):
        print(f"\n--- Importing JSON Files from {db_dir} ---")
        json_files = list(db_dir.glob('*.json'))
        print(f"Found {len(json_files)} JSON files.")

        total_records = 0
        current_count = 0
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                print(f"\n❌ Error reading {json_file.name}: {e}")
                continue

            if isinstance(data, dict):
                data = [data]

            print(f"\nProcessing {json_file.name} ({len(data)} items)...")

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
            print(f"\n⚠️ Directory not found: {pdf_dir}")
            return

        print(f"\n--- Importing PDF Files from {pdf_dir} ---")
        import pdfplumber
        
        pdf_files = list(pdf_dir.glob('*.pdf'))
        print(f"Found {len(pdf_files)} PDF files.")
        
        for i, pdf_file in enumerate(pdf_files):
            try:
                print(f"Processing ({i+1}/{len(pdf_files)}): {pdf_file.name}")
                text = ""
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
                
                if not text.strip():
                    print(f"  Skipping empty PDF: {pdf_file.name}")
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
                print(f"\n❌ Error reading {pdf_file.name}: {e}")

    def fill_missing_embeddings(self):
        print(f"\n--- Checking for Missing Embeddings ---")
        missing_count = KnowBase.objects.filter(embedding__isnull=True).count()
        if missing_count == 0:
            print("✅ All records have embeddings.")
            return

        print(f"found {missing_count} records without embeddings. Processing...")
        
        # Process in chunks to avoid memory issues
        # Django's iterator() is good for this
        qs = KnowBase.objects.filter(embedding__isnull=True)
        
        for i, obj in enumerate(qs.iterator()):
            try:
                print(f"Generating embedding for: {obj.title[:50]}...")
                embedding_text = f"{obj.title}\n{obj.content[:2000]}"
                embedding = self.generate_embedding_with_retry(embedding_text)
                
                if embedding:
                    obj.embedding = embedding
                    obj.save()
                    self.total_updated += 1
                    print(f"  ✅ Saved embedding for {obj.id}")
                else:
                    self.total_errors += 1
                    print(f"  ❌ Failed to generate embedding for {obj.id}")
                
                # Rate Limiting
                if (i + 1) % self.batch_size == 0:
                    time.sleep(self.delay)
                    
            except Exception as e:
                self.total_errors += 1
                print(f"  ❌ Error processing {obj.id}: {e}")

    def run(self):
        db_dir = Path(__file__).parent / 'database'
        self.import_json_files(db_dir)
        
        pdf_dir = db_dir / 'yamaha_manuals_pdf'
        self.import_pdf_files(pdf_dir)
        
        # Sub-task: Fill missing embeddings
        self.fill_missing_embeddings()
        
        print("\n" + "="*50)
        print(f"✅ Import & Fix Cycle Completed")
        print(f"📊 New: {self.total_imported}, Updated: {self.total_updated}, Errors: {self.total_errors}")

if __name__ == "__main__":
    importer = KnowBaseImporter()
    importer.run()
