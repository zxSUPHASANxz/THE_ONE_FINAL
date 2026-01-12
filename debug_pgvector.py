"""Debug PGVector search issue"""
import psycopg2
import google.generativeai as genai
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Connect to DB
conn = psycopg2.connect(
    dbname='the_one_db',
    user='suphasan', 
    password='Fenrir@4927',
    host='localhost',
    port='5433'
)
cur = conn.cursor()

print("=" * 60)
print("🔍 Debugging PGVector Search Issue")
print("=" * 60)

# 1. Check table name
print("\n1️⃣ Checking table names...")
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name ILIKE '%knowbase%'")
tables = cur.fetchall()
print(f"   Tables found: {tables}")

# 2. Check CBR250 data
print("\n2️⃣ Looking for CBR250 records...")
cur.execute("""
    SELECT id, title, model, 
           CASE WHEN embedding IS NULL THEN 'NO' ELSE 'YES' END as has_embedding
    FROM "KnowBase" 
    WHERE title ILIKE '%cbr250%' OR model ILIKE '%cbr250%'
""")
results = cur.fetchall()
if results:
    for r in results:
        print(f"   ID: {r[0]}, Title: {r[1]}, Model: {r[2]}, Has Embedding: {r[3]}")
else:
    print("   ❌ No CBR250 records found!")

# 3. Check embedding dimensions
print("\n3️⃣ Checking embedding dimensions...")
cur.execute("""
    SELECT id, title, array_length(embedding::float[], 1) as dim
    FROM "KnowBase" 
    WHERE embedding IS NOT NULL
    LIMIT 3
""")
results = cur.fetchall()
for r in results:
    print(f"   ID: {r[0]}, Title: {r[1][:40]}..., Dimensions: {r[2]}")

# 4. Test similarity search manually
print("\n4️⃣ Testing vector similarity search...")

# Generate query embedding with Gemini
genai.configure(api_key='AIzaSyDu2sGMNZPdAIhZUp0tsZ_7DrKDPqhwhtY')
query = "CBR250rr"
print(f"   Query: '{query}'")

result = genai.embed_content(
    model="models/text-embedding-004",
    content=query,
    task_type="retrieval_query"  # Use query type for searching
)
query_embedding = result['embedding']
print(f"   Query embedding dimensions: {len(query_embedding)}")

# Convert to postgres array format
embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

# Search using cosine similarity
cur.execute(f"""
    SELECT id, title, model, 
           1 - (embedding <=> %s::vector) as similarity
    FROM "KnowBase"
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> %s::vector
    LIMIT 5
""", (embedding_str, embedding_str))

results = cur.fetchall()
print("\n   Top 5 matches:")
for r in results:
    print(f"   • [{r[3]:.4f}] ID: {r[0]}, {r[1]} ({r[2]})")

# 5. Check if n8n uses different table
print("\n5️⃣ Checking all vector tables in database...")
cur.execute("""
    SELECT table_name, column_name 
    FROM information_schema.columns 
    WHERE udt_name = 'vector'
""")
vector_tables = cur.fetchall()
print(f"   Tables with vector columns: {vector_tables}")

cur.close()
conn.close()

print("\n" + "=" * 60)
print("✅ Debug complete!")
