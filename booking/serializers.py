from rest_framework import serializers
from .models import Motorcycle, Booking


class MotorcycleSerializer(serializers.ModelSerializer):
    """Serializer for Motorcycle model"""
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    
    class Meta:
        model = Motorcycle
        fields = ('id', 'owner', 'owner_name', 'brand', 'model', 'year', 'cc', 
                  'bike_type', 'license_plate', 'color', 'mileage', 'notes',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class BookingSerializer(serializers.ModelSerializer):
    """Serializer for Booking model"""
    customer_name = serializers.CharField(source='customer.username', read_only=True)
    mechanic_name = serializers.CharField(source='mechanic.username', read_only=True, allow_null=True)
    motorcycle_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = ('id', 'customer', 'customer_name', 'motorcycle', 'motorcycle_info',
                  'mechanic', 'mechanic_name', 'problem_description', 'appointment_date',
                  'status', 'estimated_cost', 'actual_cost', 'repair_notes',
                  'completion_date', 'pickup_date', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_motorcycle_info(self, obj):
        return f"{obj.motorcycle.brand} {obj.motorcycle.model} ({obj.motorcycle.license_plate})"
