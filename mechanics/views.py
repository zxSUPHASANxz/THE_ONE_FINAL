from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from .models import MechanicProfile, WorkQueue, Review
from .serializers import MechanicProfileSerializer, WorkQueueSerializer, ReviewSerializer
from booking.models import Booking


class MechanicProfileView(generics.RetrieveUpdateAPIView):
    """Retrieve or update mechanic profile"""
    serializer_class = MechanicProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        profile, created = MechanicProfile.objects.get_or_create(user=self.request.user)
        return profile


class WorkQueueListView(generics.ListAPIView):
    """List all work queues for a mechanic"""
    serializer_class = WorkQueueSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return WorkQueue.objects.filter(mechanic=self.request.user)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class AcceptWorkView(APIView):
    """Accept a work queue"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        try:
            work_queue = WorkQueue.objects.get(pk=pk, mechanic=request.user)
            if work_queue.status == 'pending':
                work_queue.status = 'accepted'
                work_queue.responded_at = timezone.now()
                work_queue.save()
                
                # Update booking
                booking = work_queue.booking
                booking.mechanic = request.user
                booking.status = 'confirmed'
                booking.save()
                
                # Update mechanic profile
                profile = request.user.mechanic_profile
                profile.total_jobs += 1
                profile.save()
                
                return Response({
                    'message': 'รับงานเรียบร้อยแล้ว',
                    'success': True
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'ไม่สามารถรับงานได้ในสถานะปัจจุบัน',
                    'message': 'ไม่สามารถรับงานได้ในสถานะปัจจุบัน'
                }, status=status.HTTP_400_BAD_REQUEST)
        except WorkQueue.DoesNotExist:
            return Response({
                'error': 'ไม่พบคิวงาน',
                'message': 'ไม่พบคิวงาน'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'เกิดข้อผิดพลาด'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(ensure_csrf_cookie, name='dispatch')

class RejectWorkView(APIView):
    """Reject a work queue"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        try:
            work_queue = WorkQueue.objects.get(pk=pk, mechanic=request.user)
            if work_queue.status == 'pending':
                work_queue.status = 'rejected'
                work_queue.responded_at = timezone.now()
                work_queue.save()
                
                return Response({
                    'message': 'ปฏิเสธงานเรียบร้อยแล้ว',
                    'success': True
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'ไม่สามารถปฏิเสธงานได้ในสถานะปัจจุบัน',
                    'message': 'ไม่สามารถปฏิเสธงานได้ในสถานะปัจจุบัน'
                }, status=status.HTTP_400_BAD_REQUEST)
        except WorkQueue.DoesNotExist:
            return Response({
                'error': 'ไม่พบคิวงาน',
                'message': 'ไม่พบคิวงาน'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'เกิดข้อผิดพลาด'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReviewListView(generics.ListAPIView):
    """List all reviews for a mechanic"""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Review.objects.filter(mechanic=self.request.user)


class ReviewCreateView(generics.CreateAPIView):
    """Create a review for a mechanic"""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        review = serializer.save(customer=self.request.user)
        
        # Update mechanic rating
        mechanic_profile = review.mechanic.mechanic_profile
        reviews = Review.objects.filter(mechanic=review.mechanic)
        avg_rating = sum([r.rating for r in reviews]) / len(reviews)
        mechanic_profile.rating = round(avg_rating, 2)
        mechanic_profile.save()

@method_decorator(ensure_csrf_cookie, name='dispatch')

class BookingStartView(APIView):
    """Start a booking work"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, mechanic=request.user, status='confirmed')
            booking.status = 'in_progress'
            booking.save()
            
            return Response({
                'message': 'เริ่มงานเรียบร้อยแล้ว',
                'success': True
            }, status=status.HTTP_200_OK)
        except Booking.DoesNotExist:
            return Response({
                'error': 'ไม่พบการจองหรือสถานะไม่ถูกต้อง',
                'message': 'ไม่พบการจองหรือสถานะไม่ถูกต้อง'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'เกิดข้อผิดพลาด'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@method_decorator(ensure_csrf_cookie, name='dispatch')


class BookingCompleteView(APIView):
    """Complete a booking work"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, mechanic=request.user, status='in_progress')
            booking.status = 'completed'
            booking.save()
            
            return Response({
                'message': 'ทำงานเสร็จเรียบร้อยแล้ว',
                'success': True
            }, status=status.HTTP_200_OK)
        except Booking.DoesNotExist:
            return Response({
                'error': 'ไม่พบการจองหรือสถานะไม่ถูกต้อง',
                'message': 'ไม่พบการจองหรือสถานะไม่ถูกต้อง'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'เกิดข้อผิดพลาด'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

