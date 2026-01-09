from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    Notification model for user notifications
    """
    NOTIFICATION_TYPES = (
        ('booking_confirmed', 'การจองได้รับการยืนยัน'),
        ('booking_in_progress', 'เริ่มดำเนินการซ่อม'),
        ('booking_completed', 'งานเสร็จสิ้น'),
        ('booking_cancelled', 'การจองถูกยกเลิก'),
        ('booking_rejected', 'ช่างปฏิเสธงาน'),
        ('mechanic_assigned', 'มีช่างรับงาน'),
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
