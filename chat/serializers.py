from rest_framework import serializers
from .models import ChatRoom, Message
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'user_type')


class ChatRoomSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    mechanic = UserSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    booking_info = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = ('id', 'booking', 'customer', 'mechanic', 'unread_count', 'last_message', 'other_user', 'booking_info', 'created_at', 'updated_at')
    
    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.get_unread_count(user)
    
    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return {
                'id': last_msg.id,
                'message': last_msg.message,
                'sender_id': last_msg.sender.id,
                'sender': last_msg.sender.username,
                'created_at': last_msg.created_at
            }
        return None
    
    def get_other_user(self, obj):
        user = self.context['request'].user
        other = obj.get_other_user(user)
        if other:
            return {
                'id': other.id,
                'username': other.username,
                'first_name': other.first_name or '',
                'last_name': other.last_name or '',
                'user_type': other.user_type
            }
        return None
    
    def get_booking_info(self, obj):
        if obj.booking and obj.booking.motorcycle:
            return {
                'id': obj.booking.id,
                'brand': obj.booking.motorcycle.brand,
                'model': obj.booking.motorcycle.model
            }
        return None


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ('id', 'chat_room', 'sender', 'message', 'is_read', 'created_at')
        read_only_fields = ('sender', 'is_read', 'created_at')
