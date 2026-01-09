"""
KnowBase Model - Optimized for RAG and PGVector Store
Simple and clean structure for n8n integration
"""
from django.db import models
from pgvector.django import VectorField


class KnowBase(models.Model):
    """
    Knowledge Base for RAG - Honda BigBike Information
    Optimized for Postgres PGVector Store in n8n
    """
    
    # Primary Content
    title = models.CharField(
        max_length=500,
        verbose_name='Title',
        db_index=True
    )
    content = models.TextField(
        verbose_name='Content',
        help_text='Main content for RAG retrieval'
    )
    
    # Metadata for filtering and context
    source = models.CharField(
        max_length=100,
        default='honda',
        verbose_name='Source',
        db_index=True
    )
    brand = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Brand',
        db_index=True
    )
    model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Model',
        db_index=True
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Category',
        db_index=True
    )
    source_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='Source URL'
    )
    
    # Vector Embedding for RAG (768 dimensions for Google Gemini)
    embedding = VectorField(
        dimensions=768,
        null=True,
        blank=True,
        verbose_name='Vector Embedding'
    )
    
    # Additional data
    raw_data = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Raw JSON Data'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        db_index=True
    )
    
    class Meta:
        db_table = 'KnowBase'
        verbose_name = 'Knowledge Base'
        verbose_name_plural = 'Knowledge Base'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source', 'brand']),
            models.Index(fields=['brand', 'model']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.brand} {self.model}" if self.brand and self.model else self.title[:80]
    
    def get_context_text(self):
        """Return formatted text for embedding"""
        parts = []
        if self.brand and self.model:
            parts.append(f"{self.brand} {self.model}")
        parts.append(self.title)
        if self.content:
            parts.append(self.content[:1500])  # Limit content length
        return "\n".join(parts)
