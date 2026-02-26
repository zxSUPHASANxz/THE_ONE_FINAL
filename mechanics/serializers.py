from rest_framework import serializers
from .models import MechanicProfile, WorkQueue


class MechanicProfileSerializer(serializers.ModelSerializer):
    """Serializer for MechanicProfile model"""
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = MechanicProfile
        fields = ('id', 'user', 'username', 'specialization', 'years_of_experience',
                  'certification', 'qualification', 'shop_address', 'shop_photo',
                  'qualification_file', 'license_file', 'bio', 'is_available',
                  'rating', 'total_jobs', 'created_at', 'updated_at')
        read_only_fields = ('id', 'rating', 'total_jobs', 'created_at', 'updated_at')


class WorkQueueSerializer(serializers.ModelSerializer):
    """Serializer for WorkQueue model"""
    mechanic_name = serializers.CharField(source='mechanic.username', read_only=True)
    booking_details = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkQueue
        fields = ('id', 'mechanic', 'mechanic_name', 'booking', 'booking_details',
                  'status', 'assigned_at', 'responded_at')
        read_only_fields = ('id', 'assigned_at', 'responded_at')
    
    def get_booking_details(self, obj):
        from booking.serializers import BookingSerializer
        return BookingSerializer(obj.booking).data