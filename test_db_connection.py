import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_one.settings')
django.setup()

from django.db import connection

try:
    connection.ensure_connection()
    print("✓ Database connection successful!")
    print(f"  Database: {connection.settings_dict['NAME']}")
    print(f"  Host: {connection.settings_dict['HOST']}:{connection.settings_dict['PORT']}")
    print(f"  User: {connection.settings_dict['USER']}")
    
    # Check if pgvector is enabled
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM document_chunks;")
        count = cursor.fetchone()[0]
        print(f"  ✓ Embeddings: {count:,} rows")
except Exception as e:
    print(f"✗ Database connection failed: {e}")
