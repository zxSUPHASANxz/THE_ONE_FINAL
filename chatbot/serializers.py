from rest_framework import serializers
from .models import ChatSession, ChatMessage, MotorcycleKnowledge


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


class MotorcycleKnowledgeSerializer(serializers.ModelSerializer):
    """Serializer for MotorcycleKnowledge model"""
    
    class Meta:
        model = MotorcycleKnowledge
        fields = ('id', 'brand', 'model', 'problem_category', 'symptom', 
                  'solution', 'source_url', 'scraped_data', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
