"""
Migration: Change embedding vector dimensions from 768 to 3072
Reason: Switching from text-embedding-004 (deprecated) to gemini-embedding-001
Note: pgvector HNSW/IVFFlat indexes max 2000 dims, so no vector index for 3072.
      With ~1,848 records, sequential scan is fast enough.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0012_rename_knowbase_source_da5da4_idx_knowbase_source_eae662_idx_and_more'),
    ]

    operations = [
        # Step 1: Drop the existing HNSW index (tied to old 768-dim vectors)
        migrations.RunSQL(
            sql='DROP INDEX IF EXISTS knowbase_embedding_idx;',
            reverse_sql='CREATE INDEX IF NOT EXISTS knowbase_embedding_idx ON "knowbase" USING hnsw (embedding vector_cosine_ops);',
        ),
        # Step 2: Set all existing embeddings to NULL (768-dim vs 3072-dim incompatible)
        migrations.RunSQL(
            sql='UPDATE "knowbase" SET embedding = NULL;',
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Step 3: Change the column type from vector(768) to vector(3072)
        migrations.RunSQL(
            sql='ALTER TABLE "knowbase" ALTER COLUMN embedding TYPE vector(3072);',
            reverse_sql='ALTER TABLE "knowbase" ALTER COLUMN embedding TYPE vector(768);',
        ),
        # No vector index needed - pgvector limits HNSW/IVFFlat to 2000 dims
        # Sequential scan is fine for ~1,848 records
    ]
