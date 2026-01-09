from rest_framework import serializers
from users.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    
    booking_id = serializers.IntegerField(source='booking.id', read_only=True)
    created_at_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'title',
            'message',
            'booking_id',
            'is_read',
            'created_at',
            'created_at_formatted'
        ]
    
    def get_created_at_formatted(self, obj):
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.total_seconds() < 60:
            return 'เมื่อสักครู่'
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f'{minutes} นาทีที่แล้ว'
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f'{hours} ชั่วโมงที่แล้ว'
        else:
            return obj.created_at.strftime('%d/%m/%Y %H:%M')
