from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    """
    Custom User Model for THE_ONE application
    Extends Django's AbstractUser with additional fields
    """
    USER_TYPE_CHOICES = (
        ('customer', 'ลูกค้า'),
        ('mechanic', 'ช่าง'),
        ('admin', 'ผู้ดูแลระบบ'),
    )
    
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='customer',
        verbose_name='ประเภทผู้ใช้'
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name='เบอร์โทรศัพท์'
    )
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name='ที่อยู่'
    )
    profile_image = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True,
        verbose_name='รูปโปรไฟล์'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='วันที่สร้าง')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='วันที่อัปเดต')
    
    class Meta:
        verbose_name = 'ผู้ใช้'
        verbose_name_plural = 'ผู้ใช้ทั้งหมด'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    @property
    def is_customer(self):
        return self.user_type == 'customer'
    
    @property
    def is_mechanic(self):
        return self.user_type == 'mechanic'
    
    @property
    def is_admin_user(self):
        return self.user_type == 'admin'


class Notification(models.Model):
    """
    Notification model for user notifications
    """
    NOTIFICATION_TYPES = (
        # Customer notifications
        ('booking_confirmed', 'การจองได้รับการยืนยัน'),
        ('booking_in_progress', 'เริ่มดำเนินการซ่อม'),
        ('booking_completed', 'งานเสร็จสิ้น'),
        ('booking_cancelled', 'การจองถูกยกเลิก'),
        ('booking_rejected', 'ช่างปฏิเสธงาน'),
        ('mechanic_assigned', 'มีช่างรับงาน'),
        # Mechanic notifications
        ('new_work_assigned', 'มีงานใหม่เข้ามา'),
        ('new_booking_available', 'มีงานใหม่รอรับ'),
        ('work_taken_by_other', 'มีช่างอื่นรับงานแล้ว'),
        ('work_cancelled_by_customer', 'ลูกค้ายกเลิกงาน'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='ผู้ใช้'
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        verbose_name='ประเภทการแจ้งเตือน'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='หัวข้อ'
    )
    message = models.TextField(
        verbose_name='ข้อความ'
    )
    booking = models.ForeignKey(
        'booking.Booking',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name='การจอง'
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='อ่านแล้ว'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='วันที่สร้าง'
    )
    
    class Meta:
        verbose_name = 'การแจ้งเตือน'
        verbose_name_plural = 'การแจ้งเตือนทั้งหมด'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.save()

