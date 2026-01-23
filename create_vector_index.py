import psycopg2

conn = psycopg2.connect(
    dbname='the_one_db',
    user='suphasan',
    password='Fenrir@4927',
    host='localhost',
    port='5433'
)

cur = conn.cursor()

# สร้าง HNSW index สำหรับ cosine similarity
sql = 'CREATE INDEX IF NOT EXISTS knowbase_embedding_idx ON "KnowBase" USING hnsw (embedding vector_cosine_ops);'
print('Creating vector index...')
cur.execute(sql)
conn.commit()
print('✅ Vector index created successfully!')

# เช็ค index
cur.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'KnowBase';")
indexes = cur.fetchall()
print('\nIndexes on KnowBase table:')
for idx in indexes:
    print(f'  - {idx[0]}')

cur.close()
conn.close()
