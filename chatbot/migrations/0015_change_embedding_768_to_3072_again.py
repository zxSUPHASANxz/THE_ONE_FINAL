"""
Migration: Change KnowBase embedding dimensions from 768 back to 3072.
Reason: n8n Gemini Embeddings node uses gemini-embedding-001 default output (3072).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0014_change_embedding_3072_to_768'),
    ]

    operations = [
        migrations.RunSQL(
            sql='DROP INDEX IF EXISTS knowbase_embedding_idx;',
            reverse_sql='CREATE INDEX IF NOT EXISTS knowbase_embedding_idx ON "knowbase" USING hnsw (embedding vector_cosine_ops);',
        ),
        migrations.RunSQL(
            sql='UPDATE "knowbase" SET embedding = NULL;',
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql='ALTER TABLE "knowbase" ALTER COLUMN embedding TYPE vector(3072);',
            reverse_sql='ALTER TABLE "knowbase" ALTER COLUMN embedding TYPE vector(768);',
        ),
    ]
