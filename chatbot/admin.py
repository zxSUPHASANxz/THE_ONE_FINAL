from django.contrib import admin
from .models import ChatSession, ChatMessage, MotorcycleKnowledge


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'is_active', 'started_at', 'ended_at')
    list_filter = ('is_active', 'started_at')
    search_fields = ('session_id', 'user__username')
    readonly_fields = ('started_at',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'sender', 'message_preview', 'created_at')
    list_filter = ('sender', 'created_at')
    search_fields = ('message', 'session__session_id')
    readonly_fields = ('created_at',)
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'ข้อความ'


@admin.register(MotorcycleKnowledge)
class MotorcycleKnowledgeAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model', 'problem_category', 'created_at')
    list_filter = ('brand', 'problem_category', 'created_at')
    search_fields = ('brand', 'model', 'symptom', 'solution')
    readonly_fields = ('created_at', 'updated_at')
