"""
Migration: Change embedding vector dimensions from 3072 back to 768
Reason: Using gemini-embedding-001 with output_dimensionality=768
        768 dims allows HNSW index (pgvector limit is 2000 dims)
        Faster search, less storage, and still high quality embeddings
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0013_change_embedding_768_to_3072'),
    ]

    operations = [
        # Step 1: Set all existing embeddings to NULL (3072 vs 768 incompatible)
        migrations.RunSQL(
            sql='UPDATE "knowbase" SET embedding = NULL;',
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Step 2: Change the column type from vector(3072) to vector(768)
        migrations.RunSQL(
            sql='ALTER TABLE "knowbase" ALTER COLUMN embedding TYPE vector(768);',
            reverse_sql='ALTER TABLE "knowbase" ALTER COLUMN embedding TYPE vector(3072);',
        ),
        # Step 3: Create HNSW index (now possible with 768 dims!)
        migrations.RunSQL(
            sql='CREATE INDEX IF NOT EXISTS knowbase_embedding_idx ON "knowbase" USING hnsw (embedding vector_cosine_ops);',
            reverse_sql='DROP INDEX IF EXISTS knowbase_embedding_idx;',
        ),
    ]
