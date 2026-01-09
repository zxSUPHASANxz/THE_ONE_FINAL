from django.db import models
from django.conf import settings
from booking.models import Booking


class ChatRoom(models.Model):
    """
    Chat room between customer and mechanic for a specific booking
    """
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='chat_room',
        verbose_name='การจอง'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer_chats',
        verbose_name='ลูกค้า'
    )
    mechanic = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mechanic_chats',
        null=True,
        blank=True,
        verbose_name='ช่าง'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='วันที่สร้าง')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='วันที่อัปเดต')
    
    class Meta:
        verbose_name = 'ห้องแชท'
        verbose_name_plural = 'ห้องแชททั้งหมด'
        ordering = ['-updated_at']
    
    def __str__(self):
        mechanic_name = self.mechanic.username if self.mechanic else "ไม่มีช่าง"
        return f"Chat: {self.customer.username} - {mechanic_name} (Booking #{self.booking.id})"
    
    def get_other_user(self, current_user):
        """Get the other user in the chat"""
        if current_user == self.customer:
            return self.mechanic
        return self.customer
    
    def get_unread_count(self, user):
        """Get unread message count for specific user"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    """
    Individual message in a chat room
    """
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='ห้องแชท'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name='ผู้ส่ง'
    )
    message = models.TextField(verbose_name='ข้อความ')
    is_read = models.BooleanField(default=False, verbose_name='อ่านแล้ว')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='วันที่ส่ง')
    
    class Meta:
        verbose_name = 'ข้อความ'
        verbose_name_plural = 'ข้อความทั้งหมด'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}"
