from django.contrib.auth.models import AbstractUser
from django.db import models


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

