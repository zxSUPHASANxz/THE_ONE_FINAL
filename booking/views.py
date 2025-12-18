from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Motorcycle, Booking
from .serializers import MotorcycleSerializer, BookingSerializer


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
        serializer.save(customer=self.request.user)


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
            booking = Booking.objects.get(pk=pk, customer=request.user)
            if booking.status in ['pending', 'confirmed']:
                booking.status = 'cancelled'
                booking.save()
                return Response({
                    'message': 'ยกเลิกการจองเรียบร้อยแล้ว'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'ไม่สามารถยกเลิกการจองได้ในสถานะปัจจุบัน'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Booking.DoesNotExist:
            return Response({
                'error': 'ไม่พบการจอง'
            }, status=status.HTTP_404_NOT_FOUND)

