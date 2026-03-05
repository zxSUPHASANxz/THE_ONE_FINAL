from django.db import models
from django.conf import settings
from pgvector.django import VectorField


class ChatSession(models.Model):
    """เซสชันการสนทนากับ Chatbot"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        verbose_name='ผู้ใช้'
    )
    session_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='รหัสเซสชัน'
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='เริ่มเมื่อ')
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='สิ้นสุดเมื่อ'
    )
    is_active = models.BooleanField(default=True, verbose_name='กำลังใช้งาน')
    
    class Meta:
        verbose_name = 'เซสชันแชท'
        verbose_name_plural = 'เซสชันแชททั้งหมด'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Chat #{self.session_id} - {self.user.username}"


class ChatMessage(models.Model):
    """ข้อความในการสนทนา"""
    SENDER_CHOICES = (
        ('user', 'ผู้ใช้'),
        ('bot', 'บอท'),
    )
    
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='เซสชัน'
    )
    sender = models.CharField(
        max_length=10,
        choices=SENDER_CHOICES,
        verbose_name='ผู้ส่ง'
    )
    message = models.TextField(verbose_name='ข้อความ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='เวลา')
    
    # For tracking n8n integration
    n8n_response = models.JSONField(
        null=True,
            blank=True,
        verbose_name='ข้อมูลจาก n8n'
    )
    
    class Meta:
        verbose_name = 'ข้อความแชท'
        verbose_name_plural = 'ข้อความแชททั้งหมด'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.get_sender_display()}: {self.message[:50]}"


class KnowlageDatabase(models.Model):
    """ฐานความรู้รวม - จาก Pantip และ Honda BigBike พร้อม Vector Embeddings"""
    
    # Source Info
    source = models.CharField(
        max_length=50,
        verbose_name='แหล่งที่มา',
        help_text='pantip หรือ honda'
    )
    source_url = models.URLField(
        verbose_name='URL แหล่งที่มา',
        blank=True,
        null=True
    )
    
    # Content
    title = models.CharField(max_length=500, verbose_name='หัวข้อ/ชื่อรุ่น')
    content = models.TextField(verbose_name='เนื้อหา/รายละเอียด')
    category = models.CharField(
        max_length=100,
        verbose_name='หมวดหมู่',
        blank=True
    )
    
    # Metadata (เก็บข้อมูลดิบทั้งหมดเพื่อความยืดหยุ่น)
    raw_data = models.JSONField(
        verbose_name='ข้อมูลดิบ JSON',
        help_text='เก็บข้อมูลทั้งหมดจาก source'
    )
    
    # Additional fields
    author = models.CharField(
        max_length=200,
        verbose_name='ผู้เขียน',
        blank=True,
        null=True
    )
    brand = models.CharField(
        max_length=100,
        verbose_name='ยี่ห้อ',
        blank=True,
        null=True
    )
    model = models.CharField(
        max_length=100,
        verbose_name='รุ่น',
        blank=True,
        null=True
    )
    price = models.CharField(
        max_length=50,
        verbose_name='ราคา',
        blank=True,
        null=True
    )
    
    # Stats
    views = models.IntegerField(default=0, verbose_name='ยอดเข้าชม')
    comments_count = models.IntegerField(default=0, verbose_name='จำนวนคอมเมนต์')
    
    # Timestamps
    published_at = models.DateTimeField(
        verbose_name='เผยแพร่เมื่อ',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='สร้างเมื่อ'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='อัพเดทล่าสุด'
    )
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='ใช้งาน')
    
    # Vector Embedding for RAG (3072 dimensions for gemini-embedding-001)
    embedding = VectorField(
        dimensions=3072,
        null=True,
        blank=True,
        verbose_name='Vector Embedding'
    )
    
    class Meta:
        db_table = 'DatabaseKnowlage'
        verbose_name = 'ฐานความรู้'
        verbose_name_plural = 'ฐานความรู้ทั้งหมด'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source', 'category']),
            models.Index(fields=['brand', 'model']),
            models.Index(fields=['is_active']),
            models.Index(fields=['-published_at']),
        ]
    
    def __str__(self):
        return f"[{self.source}] {self.title[:80]}"


class Knowbase(models.Model):
    """
    Knowledge Base for RAG - Simple structure optimized for PGVector Store
    """
    
    # Primary Content
    title = models.CharField(max_length=500, verbose_name='Title', db_index=True)
    content = models.TextField(verbose_name='Content')
    
    # Metadata
    source = models.CharField(max_length=100, default='Brand', db_index=True)
    brand = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    model = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    category = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    source_url = models.URLField(blank=True, null=True)
    
    # Vector Embedding (3072 dimensions for gemini-embedding-001 default output)
    embedding = VectorField(dimensions=3072, null=True, blank=True)
    
    # Additional data
    raw_data = models.JSONField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        db_table = 'knowbase'
        verbose_name = 'Knowbase'
        verbose_name_plural = 'Knowbases'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source', 'brand']),
            models.Index(fields=['brand', 'model']),
        ]
    
    def __str__(self):
        return f"{self.brand} {self.model}" if self.brand and self.model else self.title[:80]


# Backwards compatibility aliases for older imports
# Some scripts and management commands reference `KnowBase` (capital B).
# Keep that name working by pointing it to the current `Knowbase` class.
KnowBase = Knowbase


class KnowbaseEmbedQueue(Knowbase):
    """
    Proxy model สำหรับหน้าจัดการ 'คิว Embedding' ใน Admin โดยเฉพาะ
    ไม่สร้าง DB table ใหม่ (proxy=True) — ใช้ตาราง 'knowbase' ตารางเดิม
    Admin จะ filter เฉพาะ record ที่ embedding=NULL เท่านั้น
    เมื่อ embed สำเร็จ record จะหายออกจากหน้านี้อัตโนมัติ
    เมื่อ embed ล้มเหลว record จะยังอยู่ให้ retry ได้
    """
    class Meta:
        proxy = True
        verbose_name = 'Embedding (รอดำเนินการ)'
        verbose_name_plural = 'Embedding '