from django.db import models
from django.conf import settings


class MechanicProfile(models.Model):
    """ข้อมูลช่างซ่อม"""
    SPECIALIZATION_CHOICES = (
        ('engine', 'เครื่องยนต์'),
        ('electrical', 'ระบบไฟฟ้า'),
        ('brake', 'ระบบเบรก'),
        ('suspension', 'ระบบกันสะเทือน'),
        ('transmission', 'ระบบส่งกำลัง'),
        ('body', 'โครงสร้างและตัวถัง'),
        ('all', 'ซ่อมทั่วไป'),
    )
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mechanic_profile',
        verbose_name='ผู้ใช้'
    )
    specialization = models.CharField(
        max_length=20,
        choices=SPECIALIZATION_CHOICES,
        default='all',
        verbose_name='ความเชี่ยวชาญ'
    )
    years_of_experience = models.IntegerField(
        default=0,
        verbose_name='ประสบการณ์ (ปี)'
    )
    certification = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='ใบรับรอง'
    )
    bio = models.TextField(blank=True, null=True, verbose_name='ประวัติ')
    is_available = models.BooleanField(default=True, verbose_name='พร้อมรับงาน')
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        verbose_name='คะแนนเฉลี่ย'
    )
    total_jobs = models.IntegerField(default=0, verbose_name='งานทั้งหมด')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='วันที่สร้าง')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='วันที่อัปเดต')
    
    class Meta:
        verbose_name = 'โปรไฟล์ช่าง'
        verbose_name_plural = 'โปรไฟล์ช่างทั้งหมด'
        ordering = ['-rating', '-total_jobs']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_specialization_display()}"


class WorkQueue(models.Model):
    """คิวงานของช่าง"""
    STATUS_CHOICES = (
        ('pending', 'รอรับงาน'),
        ('accepted', 'รับงานแล้ว'),
        ('in_progress', 'กำลังซ่อม'),
        ('completed', 'เสร็จสิ้น'),
        ('rejected', 'ปฏิเสธงาน'),
    )
    
    mechanic = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='work_queues',
        verbose_name='ช่าง'
    )
    booking = models.ForeignKey(
        'booking.Booking',
        on_delete=models.CASCADE,
        related_name='work_queues',
        verbose_name='การจอง'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='สถานะ'
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name='มอบหมายเมื่อ')
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='ตอบรับเมื่อ'
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='เริ่มงานเมื่อ'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='เสร็จสิ้นเมื่อ'
    )
    priority = models.CharField(
        max_length=20,
        choices=[
            ('low', 'ต่ำ'),
            ('medium', 'ปานกลาง'),
            ('high', 'สูง'),
            ('urgent', 'ด่วน'),
        ],
        default='medium',
        verbose_name='ความสำคัญ'
    )
    
    class Meta:
        verbose_name = 'คิวงาน'
        verbose_name_plural = 'คิวงานทั้งหมด'
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.mechanic.username} - Booking #{self.booking.id}"


class Review(models.Model):
    """รีวิวช่างซ่อม"""
    booking = models.OneToOneField(
        'booking.Booking',
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name='การจอง'
    )
    mechanic = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='ช่าง'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='given_reviews',
        verbose_name='ลูกค้า'
    )
    rating = models.IntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        verbose_name='คะแนน'
    )
    comment = models.TextField(blank=True, null=True, verbose_name='ความคิดเห็น')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='วันที่รีวิว')
    
    class Meta:
        verbose_name = 'รีวิว'
        verbose_name_plural = 'รีวิวทั้งหมด'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review for {self.mechanic.username} - {self.rating}★"

