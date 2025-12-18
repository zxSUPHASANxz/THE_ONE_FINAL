from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                  'user_type', 'phone_number', 'address', 'profile_image',
                  'created_at')
        read_only_fields = ('id', 'created_at')


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'first_name', 
                  'last_name', 'user_type', 'phone_number')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "รหัสผ่านไม่ตรงกัน"})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user
