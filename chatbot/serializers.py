from rest_framework import serializers
from .models import ChatSession, ChatMessage, KnowlageDatabase


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for ChatMessage model"""
    
    class Meta:
        model = ChatMessage
        fields = ('id', 'session', 'sender', 'message', 'n8n_response', 'created_at')
        read_only_fields = ('id', 'created_at')


class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for ChatSession model"""
    messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatSession
        fields = ('id', 'user', 'session_id', 'started_at', 'ended_at', 
                  'is_active', 'messages')
        read_only_fields = ('id', 'started_at')


class KnowlageDatabaseSerializer(serializers.ModelSerializer):
    """Serializer for KnowlageDatabase model"""
    
    class Meta:
        model = KnowlageDatabase
        fields = ('id', 'source', 'source_url', 'title', 'content', 'category',
                  'author', 'brand', 'model', 'price', 'views', 'comments_count',
                  'raw_data', 'published_at', 'created_at', 'updated_at', 'is_active')
        read_only_fields = ('id', 'created_at', 'updated_at')
