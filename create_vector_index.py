"""
Create vector index for KnowBase table.

Note: pgvector HNSW/IVFFlat indexes only support up to 2000 dimensions.
    gemini-embedding-001 produces 3072 dimensions, so we cannot use HNSW.
    For current dataset size, sequential scan with cosine distance is acceptable.
"""
import psycopg2

conn = psycopg2.connect(
    dbname='the_one_db',
    user='suphasan',
    password='Fenrir@4927',
    host='localhost',
    port='5433'
)

cur = conn.cursor()

# Drop old HNSW index if exists (incompatible with 3072 dims)
print('Dropping HNSW vector index if exists...')
cur.execute('DROP INDEX IF EXISTS knowbase_embedding_idx;')
conn.commit()
print('✅ HNSW index removed (3072-dim mode)')

# Verify table structure
cur.execute("""
    SELECT column_name, data_type, udt_name
    FROM information_schema.columns
    WHERE table_name = 'knowbase'
    ORDER BY ordinal_position;
""")
columns = cur.fetchall()
print('\nTable "knowbase" columns:')
for col in columns:
    print(f'  - {col[0]}: {col[1]} ({col[2]})')

# Count records
cur.execute('SELECT COUNT(*) FROM "knowbase";')
total = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM "knowbase" WHERE embedding IS NOT NULL;')
with_embed = cur.fetchone()[0]
print(f'\n📊 Records: {total} total, {with_embed} with embeddings')

# Check existing indexes
cur.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'knowbase';")
indexes = cur.fetchall()
print('\n📇 Indexes on knowbase:')
for idx in indexes:
    print(f'  - {idx[0]}')
    print(f'    {idx[1]}')

cur.close()
conn.close()
print('\n✅ Done')
