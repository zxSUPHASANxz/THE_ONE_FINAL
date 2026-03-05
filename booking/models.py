from django.db import models
from django.conf import settings


class Motorcycle(models.Model):
    """รถจักรยานยนต์ของลูกค้า"""
    BIKE_TYPES = (
        ('classic', 'Classic'),
        ('standard', 'Standard'),
        ('sport', 'Sport'),
        ('touring', 'Touring'),
        ('adventure', 'Adventure'),
        ('super_sport', 'Super Sport'),
        ('sport_touring', 'Sport Touring'),
        ('custom_bobber', 'Custom Bobber'),
        ('race', 'Race (Track only)'),
    )
    
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='motorcycles',
        verbose_name='เจ้าของ'
    )
    brand = models.CharField(max_length=100, verbose_name='ยี่ห้อ')
    model = models.CharField(max_length=100, verbose_name='รุ่น')
    year = models.IntegerField(verbose_name='ปี')
    cc = models.IntegerField(verbose_name='ความจุกระบอกสูบ (cc)')
    bike_type = models.CharField(
        max_length=20,
        choices=BIKE_TYPES,
        default='classic',
        verbose_name='ประเภทรถ'
    )
    license_plate = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='ทะเบียนรถ'
    )
    color = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='สี'
    )
    mileage = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='เลขไมล์ (กม.)'
    )
    notes = models.TextField(blank=True, null=True, verbose_name='หมายเหตุ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='วันที่เพิ่ม')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='วันที่อัปเดต')
    
    class Meta:
        verbose_name = 'รถจักรยานยนต์'
        verbose_name_plural = 'รถจักรยานยนต์ทั้งหมด'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.brand} {self.model} ({self.license_plate})"


class Booking(models.Model):
    """การจองคิวซ่อมรถ"""
    STATUS_CHOICES = (
        ('pending', 'รอยืนยัน'),
        ('confirmed', 'ยืนยันแล้ว'),
        ('in_progress', 'กำลังซ่อม'),
        ('completed', 'เสร็จสิ้น'),
        ('cancelled', 'ยกเลิก'),
    )
    
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='ลูกค้า'
    )
    motorcycle = models.ForeignKey(
        Motorcycle,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='รถจักรยานยนต์'
    )
    mechanic = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mechanic_bookings',
        verbose_name='ช่างที่รับผิดชอบ'
    )
    problem_description = models.TextField(verbose_name='อาการที่พบ')
    appointment_date = models.DateTimeField(verbose_name='วันเวลานัด')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='สถานะ'
    )
    repair_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='รายละเอียดการซ่อม'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='วันที่จอง')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='วันที่อัปเดต')

    # เพิ่มฟิลด์ค่าประเมินการซ่อม (สามารถเป็นทศนิยม)
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='ค่าประเมินการซ่อม'
    )
    
    actual_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='ค่าซ่อมจริง'
    )
    
    completion_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='วันที่ซ่อมเสร็จ'
    )
    
    pickup_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='วันที่รับรถ'
    )
    
    class Meta:
        verbose_name = 'การจองคิว'
        verbose_name_plural = 'การจองคิวทั้งหมด'
        ordering = ['-appointment_date']
    
    def __str__(self):
        return f"Booking #{self.id} - {self.customer.username} - {self.get_status_display()}"


class BookingImage(models.Model):
    """รูปภาพประกอบการจอง (อาการรถ)"""
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='การจอง'
    )
    image = models.ImageField(
        upload_to='booking_images/',
        verbose_name='รูปภาพ'
    )
    caption = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='คำอธิบายรูป'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='อัปโหลดเมื่อ')

    class Meta:
        verbose_name = 'รูปภาพการจอง'
        verbose_name_plural = 'รูปภาพการจองทั้งหมด'
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Image for Booking #{self.booking_id}"

