import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_one.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

# Get all tables
cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    ORDER BY table_name;
""")

tables = cursor.fetchall()

print("✓ Tables created successfully:")
print(f"  Total: {len(tables)} tables\n")

for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
    count = cursor.fetchone()[0]
    print(f"  - {table[0]:<40} ({count:,} rows)")

cursor.close()
