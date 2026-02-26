from django.contrib import admin
from .models import ChatSession, ChatMessage, Knowbase


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


@admin.register(Knowbase)
class KnowbaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'brand', 'model', 'category', 'created_at')
    list_filter = ('source', 'category', 'brand', 'is_active', 'created_at')
    search_fields = ('title', 'content', 'brand', 'model')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50

