from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Motorcycle, Booking
from .serializers import MotorcycleSerializer, BookingSerializer
import logging

logger = logging.getLogger(__name__)


class MotorcycleListCreateView(generics.ListCreateAPIView):
    """List all motorcycles or create a new one"""
    serializer_class = MotorcycleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Motorcycle.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class MotorcycleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a motorcycle"""
    serializer_class = MotorcycleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Motorcycle.objects.filter(owner=self.request.user)


class BookingListCreateView(generics.ListCreateAPIView):
    """List all bookings or create a new one"""
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_mechanic:
            return Booking.objects.filter(mechanic=user)
        return Booking.objects.filter(customer=user)
    
    def perform_create(self, serializer):
        # Pass customer to serializer, it will handle the creation
        serializer.save(customer=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Override create to catch errors and return proper JSON response"""
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Booking creation error: {str(e)}", exc_info=True)
            return Response({
                'error': f'เกิดข้อผิดพลาดในการสร้างการจอง: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BookingDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or update a booking"""
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_mechanic:
            return Booking.objects.filter(mechanic=user)
        return Booking.objects.filter(customer=user)


class BookingCancelView(APIView):
    """Cancel a booking"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        try:
            # Allow customer, admin, or mechanic to cancel
            if request.user.is_staff or request.user.is_mechanic:
                booking = Booking.objects.get(pk=pk)
            else:
                booking = Booking.objects.get(pk=pk, customer=request.user)
            
            if booking.status in ['pending', 'confirmed']:
                booking.status = 'cancelled'
                booking.save()
                return Response({
                    'message': 'ยกเลิกการจองเรียบร้อยแล้ว',
                    'booking_id': booking.id,
                    'status': booking.status
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': f'ไม่สามารถยกเลิกการจองได้ในสถานะปัจจุบัน (สถานะ: {booking.status})'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Booking.DoesNotExist:
            return Response({
                'error': f'ไม่พบการจอง #{pk} หรือคุณไม่มีสิทธิ์เข้าถึง (User: {request.user.username})'
            }, status=status.HTTP_404_NOT_FOUND)

