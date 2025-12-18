#!/usr/bin/env python3
"""
Document Embedding Pipeline - Hugging Face Sentence Transformers
Free, unlimited, runs locally with Thai language support
"""

import json
import os
import sys
import time
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer

# Configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'the_one_db',
    'user': 'suphasan',
    'password': 'Fenrir@4927'
}

# File paths
PANTIP_JSON = 'pantip.json'
BIGBIKE_JSON = 'scraper/bigbike_faq_complete.json'

# Chunking settings
MAX_CHUNK_SIZE = 2000  # Characters per chunk
OVERLAP = 200          # Overlap between chunks

# Model selection - choose one:
# 'paraphrase-multilingual-MiniLM-L12-v2' -> 384 dims, fast, Thai support
# 'intfloat/multilingual-e5-base' -> 768 dims, better quality, Thai support
MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'

print("=" * 80)
print("🚀 Document Embedding Pipeline - Hugging Face")
print("=" * 80)
print(f"📦 Loading model: {MODEL_NAME}")

# Load model (downloads on first run, cached after)
model = SentenceTransformer(MODEL_NAME)
embedding_dim = model.get_sentence_embedding_dimension()
print(f"✓ Model loaded: {embedding_dim} dimensions")


def chunk_text(text, max_size=MAX_CHUNK_SIZE, overlap=OVERLAP):
    """Split text into chunks with overlap"""
    if not text or len(text.strip()) == 0:
        return []
    
    # Limit total text size to prevent memory issues
    text_length = len(text)
    if text_length > 100000:  # 100KB limit
        print(f"  ⚠️  Content truncated from {text_length} to 100,000 chars")
        text = text[:100000]
        text_length = 100000
    
    chunks = []
    start = 0
    max_chunks = 50  # Limit number of chunks
    
    while start < text_length and len(chunks) < max_chunks:
        end = start + max_size
        
        # Find sentence boundary
        if end < text_length:
            # Look for sentence end
            for punct in ['. ', '! ', '? ', '\n\n']:
                last_punct = text.rfind(punct, start, end)
                if last_punct != -1:
                    end = last_punct + len(punct)
                    break
        
        chunk = text[start:end].strip()
        if chunk and len(chunk) > 50:  # Skip very short chunks
            chunks.append(chunk)
        
        start = end - overlap if end < text_length else end
    
    return chunks


def get_embedding(text):
    """Get embedding from Sentence Transformer"""
    try:
        embedding = model.encode(text, show_progress_bar=False)
        return embedding.tolist()
    except Exception as e:
        print(f"  ❌ Embedding error: {e}")
        return None


def connect_db():
    """Connect to PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print(f"✓ Connected to database: {DB_CONFIG['database']}\n")
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        sys.exit(1)


def insert_source(conn, name, source_type, base_url=None):
    """Insert or get source ID"""
    with conn.cursor() as cur:
        # Check if source exists
        cur.execute(
            "SELECT id FROM sources WHERE name = %s",
            (name,)
        )
        result = cur.fetchone()
        
        if result:
            return result[0]
        
        # Insert new source
        cur.execute(
            """
            INSERT INTO sources (name, type, base_url, created_at)
            VALUES (%s, %s, %s, NOW())
            RETURNING id
            """,
            (name, source_type, base_url)
        )
        source_id = cur.fetchone()[0]
        conn.commit()
        return source_id


def insert_document(conn, source_id, url, title, content, metadata):
    """Insert or get document ID"""
    with conn.cursor() as cur:
        # Check if document exists
        cur.execute(
            "SELECT id FROM documents WHERE url = %s",
            (url,)
        )
        result = cur.fetchone()
        
        if result:
            print(f"  ⏭️  Document exists: {title[:50]}")
            return result[0]
        
        # Insert new document
        cur.execute(
            """
            INSERT INTO documents (source_id, url, title, content, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (source_id, url, title, content, json.dumps(metadata))
        )
        doc_id = cur.fetchone()[0]
        conn.commit()
        return doc_id


def insert_chunks(conn, doc_id, chunks_data):
    """Batch insert document chunks with embeddings"""
    if not chunks_data:
        return 0
    
    with conn.cursor() as cur:
        # Check existing chunks
        cur.execute(
            "SELECT chunk_index FROM document_chunks WHERE document_id = %s",
            (doc_id,)
        )
        existing_indices = {row[0] for row in cur.fetchall()}
        
        # Filter out existing chunks
        new_chunks = [
            chunk for chunk in chunks_data 
            if chunk['index'] not in existing_indices
        ]
        
        if not new_chunks:
            return 0
        
        # Prepare data for batch insert
        values = [
            (
                doc_id,
                chunk['index'],
                chunk['content'],
                chunk['embedding'],
                json.dumps(chunk['metadata'])
            )
            for chunk in new_chunks
        ]
        
        # Batch insert
        execute_values(
            cur,
            """
            INSERT INTO document_chunks (document_id, chunk_index, content, embedding, metadata)
            VALUES %s
            """,
            values,
            template="(%s, %s, %s, %s::vector, %s)"
        )
        
        conn.commit()
        return len(values)


def process_pantip_data(conn):
    """Process Pantip forum threads"""
    print("=" * 80)
    print("📋 Processing Pantip Data")
    print("=" * 80)
    
    if not os.path.exists(PANTIP_JSON):
        print(f"❌ File not found: {PANTIP_JSON}")
        return 0, 0
    
    # Load data
    with open(PANTIP_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 Found {len(data)} threads\n")
    
    # Create source
    source_id = insert_source(conn, "Pantip", "forum", "https://pantip.com")
    
    total_docs = 0
    total_chunks = 0
    
    for i, thread in enumerate(data, 1):
        title = thread.get('title', 'No title')[:60]
        print(f"[{i}/{len(data)}] {title}")
        
        # Prepare content
        content = thread.get('content', '')
        comments = thread.get('comments', [])
        comments_text = '\n\n'.join([
            f"Comment by {c.get('author', 'Anonymous')}: {c.get('content', '')}"
            for c in comments[:10]  # Limit to 10 comments
        ])
        
        full_content = f"{content}\n\n{comments_text}" if comments_text else content
        
        # Skip if content too large
        if len(full_content) > 100000:
            print(f"  ⚠️  Content too large ({len(full_content)} chars), truncating...")
            full_content = full_content[:100000]
        
        # Insert document
        metadata = {
            'author': thread.get('author', ''),
            'tags': thread.get('tags', []),
            'views': thread.get('views', 0),
            'comments_count': thread.get('comments_count', 0)
        }
        
        doc_id = insert_document(
            conn,
            source_id,
            thread.get('url', f'pantip://thread/{i}'),
            thread.get('title', 'Untitled'),
            full_content,
            metadata
        )
        
        if not doc_id:
            continue
        
        total_docs += 1
        
        # Create chunks
        chunks = chunk_text(full_content)
        if not chunks:
            print(f"  ⚠️  No valid chunks created")
            continue
            
        print(f"  📝 Creating {len(chunks)} chunks...")
        
        chunks_data = []
        for idx, chunk_content in enumerate(chunks):
            # Get embedding
            embedding = get_embedding(chunk_content)
            
            if embedding:
                chunks_data.append({
                    'index': idx,
                    'content': chunk_content,
                    'embedding': embedding,
                    'metadata': {'length': len(chunk_content)}
                })
                print(f"  ✓ Chunk {idx + 1}/{len(chunks)}: {len(chunk_content)} chars")
        
        # Insert chunks
        if chunks_data:
            inserted = insert_chunks(conn, doc_id, chunks_data)
            total_chunks += inserted
            print(f"  ✅ Inserted {inserted} chunks\n")
        else:
            print(f"  ⚠️  No chunks to insert\n")
    
    return total_docs, total_chunks


def process_bigbike_data(conn):
    """Process BigBike FAQ articles"""
    print("=" * 80)
    print("📋 Processing BigBike FAQ Data")
    print("=" * 80)
    
    if not os.path.exists(BIGBIKE_JSON):
        print(f"❌ File not found: {BIGBIKE_JSON}")
        return 0, 0
    
    # Load data
    with open(BIGBIKE_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 Found {len(data)} articles\n")
    
    # Create source
    source_id = insert_source(conn, "BigBike FAQ", "official", "https://www.bigbikeinfo.com")
    
    total_docs = 0
    total_chunks = 0
    
    for i, article in enumerate(data, 1):
        title = article.get('title', 'No title')[:60]
        print(f"[{i}/{len(data)}] {title}")
        
        content = article.get('content', '')
        
        # Skip if empty
        if not content or len(content.strip()) < 50:
            print(f"  ⚠️  Content too short, skipping\n")
            continue
        
        # Insert document
        doc_id = insert_document(
            conn,
            source_id,
            article.get('url', f'bigbike://article/{i}'),
            article.get('title', 'Untitled'),
            content,
            {}
        )
        
        if not doc_id:
            continue
        
        total_docs += 1
        
        # Create chunks
        chunks = chunk_text(content)
        if not chunks:
            print(f"  ⚠️  No valid chunks created\n")
            continue
            
        print(f"  📝 Creating {len(chunks)} chunks...")
        
        chunks_data = []
        for idx, chunk_content in enumerate(chunks):
            # Get embedding
            embedding = get_embedding(chunk_content)
            
            if embedding:
                chunks_data.append({
                    'index': idx,
                    'content': chunk_content,
                    'embedding': embedding,
                    'metadata': {'length': len(chunk_content)}
                })
                print(f"  ✓ Chunk {idx + 1}/{len(chunks)}: {len(chunk_content)} chars")
        
        # Insert chunks
        if chunks_data:
            inserted = insert_chunks(conn, doc_id, chunks_data)
            total_chunks += inserted
            print(f"  ✅ Inserted {inserted} chunks\n")
        else:
            print(f"  ⚠️  No chunks to insert\n")
    
    return total_docs, total_chunks


def main():
    """Main pipeline"""
    try:
        # Connect to database
        conn = connect_db()
        
        # Process data
        pantip_docs, pantip_chunks = process_pantip_data(conn)
        bigbike_docs, bigbike_chunks = process_bigbike_data(conn)
        
        # Summary
        print("=" * 80)
        print("📊 Processing Complete")
        print("=" * 80)
        print(f"Pantip:  {pantip_docs} documents, {pantip_chunks} chunks")
        print(f"BigBike: {bigbike_docs} documents, {bigbike_chunks} chunks")
        print(f"Total:   {pantip_docs + bigbike_docs} documents, {pantip_chunks + bigbike_chunks} chunks")
        print(f"Model:   {MODEL_NAME} ({embedding_dim} dimensions)")
        print("=" * 80)
        
        conn.close()
        print("✓ Database connection closed")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
