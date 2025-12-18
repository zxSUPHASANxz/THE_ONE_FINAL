from django.db import models
from django.conf import settings


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


class MotorcycleKnowledge(models.Model):
    """ฐานความรู้เกี่ยวกับรถจักรยานยนต์ (สำหรับ RAG)"""
    brand = models.CharField(max_length=100, verbose_name='ยี่ห้อ')
    model = models.CharField(max_length=100, verbose_name='รุ่น')
    problem_category = models.CharField(
        max_length=100,
        verbose_name='ประเภทปัญหา'
    )
    symptom = models.TextField(verbose_name='อาการ')
    solution = models.TextField(verbose_name='วิธีแก้ไข')
    source_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='แหล่งที่มา'
    )
    scraped_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='ข้อมูลที่ดึงมา'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='วันที่เพิ่ม')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='วันที่อัปเดต')
    
    class Meta:
        verbose_name = 'ความรู้เกี่ยวกับรถ'
        verbose_name_plural = 'ความรู้เกี่ยวกับรถทั้งหมด'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.brand} {self.model} - {self.problem_category}"

