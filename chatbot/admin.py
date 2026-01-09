from django.contrib import admin
from .models import ChatSession, ChatMessage, KnowlageDatabase


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


@admin.register(KnowlageDatabase)
class KnowledgeDatabaseAdmin(admin.ModelAdmin):
    list_display = ('title_preview', 'source', 'brand', 'model', 'category', 'views', 'created_at')
    list_filter = ('source', 'category', 'brand', 'is_active', 'created_at')
    search_fields = ('title', 'content', 'brand', 'model', 'author')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50
    
    def title_preview(self, obj):
        return obj.title[:80] + '...' if len(obj.title) > 80 else obj.title
    title_preview.short_description = 'หัวข้อ'
    
    fieldsets = (
        ('ข้อมูลหลัก', {
            'fields': ('source', 'title', 'content', 'category')
        }),
        ('แหล่งที่มา', {
            'fields': ('source_url', 'author')
        }),
        ('ข้อมูลรถ', {
            'fields': ('brand', 'model', 'price')
        }),
        ('สถิติ', {
            'fields': ('views', 'comments_count')
        }),
        ('ข้อมูลดิบ', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
        ('อื่นๆ', {
            'fields': ('is_active', 'published_at', 'created_at', 'updated_at')
        }),
    )

