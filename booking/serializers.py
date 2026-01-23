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
        read_only_fields = ('id', 'owner', 'created_at', 'updated_at')


class BookingSerializer(serializers.ModelSerializer):
    """Serializer for Booking model"""
    customer_name = serializers.CharField(source='customer.username', read_only=True)
    mechanic_name = serializers.CharField(source='mechanic.username', read_only=True, allow_null=True)
    mechanic_full_name = serializers.SerializerMethodField()
    mechanic_phone = serializers.CharField(source='mechanic.phone_number', read_only=True, allow_null=True)
    motorcycle_info = serializers.SerializerMethodField()
    service_type = serializers.SerializerMethodField(read_only=True)
    chat_room_id = serializers.SerializerMethodField()
    
    # Optional fields for easier frontend submission (write-only)
    service_type_input = serializers.CharField(write_only=True, required=False)
    description = serializers.CharField(write_only=True, required=False, allow_blank=True)
    scheduled_date = serializers.DateField(write_only=True, required=False)
    time_slot = serializers.CharField(write_only=True, required=False, allow_blank=True)
    notes = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    # Make these not required on write (will be populated by create method)
    problem_description = serializers.CharField(required=False)
    appointment_date = serializers.DateTimeField(required=False)
    
    class Meta:
        model = Booking
        fields = ('id', 'customer', 'customer_name', 'motorcycle', 'motorcycle_info',
                  'mechanic', 'mechanic_name', 'mechanic_full_name', 'mechanic_phone',
                  'problem_description', 'appointment_date',
                  'status', 'estimated_cost', 'actual_cost', 'repair_notes',
                  'completion_date', 'pickup_date', 'created_at', 'updated_at',
                  'service_type', 'service_type_input', 'description', 'scheduled_date', 
                  'time_slot', 'notes', 'chat_room_id')
        read_only_fields = ('id', 'customer', 'created_at', 'updated_at')
    
    def get_service_type(self, obj):
        """Extract service type from problem_description"""
        if obj.problem_description:
            # Extract first part before colon (service type)
            parts = obj.problem_description.split(':', 1)
            if parts:
                return parts[0].strip()
        return None
    
    def get_mechanic_full_name(self, obj):
        """Get mechanic full name"""
        if obj.mechanic:
            first = obj.mechanic.first_name or ''
            last = obj.mechanic.last_name or ''
            full_name = f"{first} {last}".strip()
            return full_name if full_name else obj.mechanic.username
        return None
    
    def get_chat_room_id(self, obj):
        """Get chat room ID if exists"""
        try:
            if hasattr(obj, 'chat_room'):
                return obj.chat_room.id
        except Exception:
            pass
        return None
    
    def get_motorcycle_info(self, obj):
        """Get motorcycle info, handle case when motorcycle is deleted"""
        try:
            if obj.motorcycle:
                return f"{obj.motorcycle.brand} {obj.motorcycle.model} ({obj.motorcycle.license_plate})"
        except Motorcycle.DoesNotExist:
            return "รถถูกลบไปแล้ว"
        return "ไม่ระบุรถ"
    
    def create(self, validated_data):
        from datetime import timedelta
        from django.utils import timezone
        
        # Extract optional fields (use write-only field names)
        service_type = validated_data.pop('service_type_input', '')
        description = validated_data.pop('description', '')
        scheduled_date = validated_data.pop('scheduled_date', None)
        time_slot = validated_data.pop('time_slot', '')
        notes = validated_data.pop('notes', '')
        
        # Get customer from context (passed from view)
        customer = self.context['request'].user
        motorcycle = validated_data.get('motorcycle')
        
        # Check for duplicate booking (same customer, same motorcycle, within 2 minutes)
        if motorcycle:
            two_minutes_ago = timezone.now() - timedelta(minutes=2)
            existing = Booking.objects.filter(
                customer=customer,
                motorcycle=motorcycle,
                created_at__gte=two_minutes_ago
            ).first()
            
            if existing:
                # Return existing booking instead of creating duplicate
                return existing
        
        # Build problem_description from service_type and description
        problem_desc = f"{service_type}: {description}" if description else service_type
        if notes:
            problem_desc += f"\nหมายเหตุ: {notes}"
        validated_data['problem_description'] = problem_desc
        
        # Build appointment_date from scheduled_date and time_slot
        if scheduled_date:
            time_map = {
                'morning': '09:00:00',
                'afternoon': '13:00:00',
                'evening': '16:00:00'
            }
            time_str = time_map.get(time_slot, '09:00:00')
            from datetime import datetime
            from django.utils import timezone
            
            naive_datetime = datetime.combine(
                scheduled_date,
                datetime.strptime(time_str, '%H:%M:%S').time()
            )
            # Make timezone aware
            validated_data['appointment_date'] = timezone.make_aware(naive_datetime)
        
        # Don't auto-assign mechanic - let them accept the job
        from mechanics.models import WorkQueue
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Find all available mechanics
        available_mechanics = User.objects.filter(
            user_type='mechanic',
            mechanic_profile__is_available=True
        )
        
        # Create booking without mechanic assigned (status = pending)
        validated_data['mechanic'] = None  # No auto-assign
        booking = super().create(validated_data)
        
        # Create work queue entries for ALL available mechanics
        # so they can all see and compete for the job
        for mechanic in available_mechanics:
            WorkQueue.objects.create(
                mechanic=mechanic,
                booking=booking,
                status='pending'
            )
        
        return booking
