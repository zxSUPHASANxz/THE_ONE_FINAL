from django.urls import path
from . import views
from . import views_web
from booking.views import BookingCancelView

app_name = 'mechanics'

urlpatterns = [
    # Web Views (Template-based)
    path('dashboard/', views_web.dashboard_view, name='dashboard'),
    path('work/<int:pk>/accept/', views_web.accept_work_view, name='accept_work_web'),
    path('work/<int:pk>/reject/', views_web.reject_work_view, name='reject_work_web'),
    path('booking/<int:booking_id>/start/', views_web.start_work_view, name='start_work'),
    path('booking/<int:booking_id>/complete/', views_web.complete_work_view, name='complete_work'),
    
    # API Views (JSON)
    # Mechanic profile
    path('api/profile/', views.MechanicProfileView.as_view(), name='profile'),
    
    # Work queue
    path('api/queue/', views.WorkQueueListView.as_view(), name='queue_list'),
    path('api/queue/<int:pk>/accept/', views.AcceptWorkView.as_view(), name='accept_work'),
    path('api/queue/<int:pk>/reject/', views.RejectWorkView.as_view(), name='reject_work'),
    
    # Booking actions
    path('api/bookings/<int:pk>/start/', views.BookingStartView.as_view(), name='booking_start'),
    path('api/bookings/<int:pk>/complete/', views.BookingCompleteView.as_view(), name='booking_complete'),
    # Allow canceling a booking via mechanics namespace (delegates to booking app view)
    path('api/bookings/<int:pk>/cancel/', BookingCancelView.as_view(), name='booking_cancel'),
    
    # Reviews
    path('api/reviews/', views.ReviewListView.as_view(), name='review_list'),
    path('api/reviews/create/', views.ReviewCreateView.as_view(), name='review_create'),
]
