"""
Re-embed all KnowBase records with gemini-embedding-001 (3072 dims)
===================================================================
Free tier limit: 1,000 requests/day/model
With 1,848 records → needs ~2 days (or run with --batch to do partial)

Usage:
    python reembed_knowbase.py                  # Re-embed all (with auto-pause on rate limit)
    python reembed_knowbase.py --batch 500      # Re-embed 500 records then stop
    python reembed_knowbase.py --status         # Check current status only
"""

import os
import sys
import time
import argparse
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_one.settings')

from dotenv import load_dotenv
load_dotenv()
django.setup()

import google.generativeai as genai
from chatbot.models import KnowBase

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL = "models/gemini-embedding-001"
if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY not found in .env")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)


def show_status():
    total = KnowBase.objects.count()
    with_embed = KnowBase.objects.exclude(embedding__isnull=True).count()
    without = total - with_embed
    pct = (with_embed / total * 100) if total > 0 else 0
    print(f"📊 KnowBase Status:")
    print(f"   Total:     {total}")
    print(f"   Embedded:  {with_embed} ({pct:.1f}%)")
    print(f"   Missing:   {without}")
    return without


def generate_embedding(text: str, max_retries: int = 3):
    """Generate 3072-dim embedding with gemini-embedding-001"""
    for attempt in range(max_retries):
        try:
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=text,
            )
            return result['embedding']
        except Exception as e:
            error_str = str(e)
            if '429' in error_str or 'ResourceExhausted' in error_str:
                # Rate limited - extract wait time or use default
                if 'retry in' in error_str.lower():
                    # Try to parse wait time
                    import re
                    match = re.search(r'retry in (\d+\.?\d*)', error_str)
                    wait = float(match.group(1)) + 5 if match else 65
                else:
                    wait = 65
                print(f"\n   ⏳ Rate limited. Waiting {wait:.0f}s...")
                time.sleep(wait)
            elif attempt < max_retries - 1:
                wait = (2 ** attempt) * 2
                print(f"\n   ⚠️ Error (attempt {attempt+1}): {error_str[:80]}")
                time.sleep(wait)
            else:
                print(f"\n   ❌ Failed: {error_str[:80]}")
                return None
    return None


def reembed(batch_limit: int = 0):
    """Re-embed records that have no embedding"""
    missing = show_status()
    if missing == 0:
        print("\n✅ All records already have embeddings!")
        return

    qs = KnowBase.objects.filter(embedding__isnull=True)
    if batch_limit > 0:
        qs = qs[:batch_limit]
        print(f"\n🔄 Processing batch of {batch_limit} records...")
    else:
        print(f"\n🔄 Processing all {missing} records...")

    success = 0
    errors = 0
    start_time = time.time()

    records = list(qs)  # Materialize to avoid queryset mutation issues
    total = len(records)

    for i, obj in enumerate(records):
        # Progress
        elapsed = time.time() - start_time
        rate = success / elapsed if elapsed > 0 and success > 0 else 0.5
        eta = (total - i) / rate if rate > 0 else 0
        print(f"\r  [{i+1}/{total}] {success}✅ {errors}❌ | {rate:.1f} rec/s | ETA: {eta/60:.1f}m | {obj.title[:40]}...", end="", flush=True)

        # Build embedding text
        embedding_text = f"{obj.title}\n{obj.content[:2000]}"
        embedding = generate_embedding(embedding_text)

        if embedding:
            obj.embedding = embedding
            obj.save(update_fields=['embedding'])
            success += 1
        else:
            errors += 1

        # Small delay between requests (avoid burst)
        if (i + 1) % 5 == 0:
            time.sleep(1.0)

    elapsed = time.time() - start_time
    print(f"\n\n{'='*50}")
    print(f"✅ Done in {elapsed/60:.1f} minutes")
    print(f"   Success: {success}, Errors: {errors}")
    show_status()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Re-embed KnowBase with gemini-embedding-001 (3072 dims)')
    parser.add_argument('--batch', type=int, default=0, help='Limit number of records to process (0=all)')
    parser.add_argument('--status', action='store_true', help='Show status only')
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        reembed(args.batch)
