from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, RegisterSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """API endpoint for user registration"""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'user': UserSerializer(user).data,
            'message': 'สมัครสมาชิกเรียบร้อยแล้ว'
        }, status=status.HTTP_201_CREATED)


class ProfileView(generics.RetrieveUpdateAPIView):
    """API endpoint for user profile"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user

