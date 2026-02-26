from django.contrib import admin
from .models import MechanicProfile, WorkQueue


@admin.register(MechanicProfile)
class MechanicProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'years_of_experience', 'rating', 'total_jobs', 'is_available')
    list_filter = ('specialization', 'is_available', 'years_of_experience')
    search_fields = ('user__username', 'certification')
    readonly_fields = ('created_at', 'updated_at', 'total_jobs', 'rating')


@admin.register(WorkQueue)
class WorkQueueAdmin(admin.ModelAdmin):
    list_display = ('mechanic', 'booking', 'status', 'assigned_at', 'responded_at')
    list_filter = ('status', 'assigned_at')
    search_fields = ('mechanic__username', 'booking__id')
    readonly_fields = ('assigned_at',)