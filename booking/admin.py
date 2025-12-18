from django.contrib import admin
from .models import Motorcycle, Booking


@admin.register(Motorcycle)
class MotorcycleAdmin(admin.ModelAdmin):
    list_display = ('license_plate', 'brand', 'model', 'year', 'cc', 'bike_type', 'owner')
    list_filter = ('bike_type', 'brand', 'year')
    search_fields = ('license_plate', 'brand', 'model', 'owner__username')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'motorcycle', 'status', 'appointment_date', 'mechanic')
    list_filter = ('status', 'appointment_date', 'created_at')
    search_fields = ('customer__username', 'motorcycle__license_plate', 'problem_description')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'appointment_date'
