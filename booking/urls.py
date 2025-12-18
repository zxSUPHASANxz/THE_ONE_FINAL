from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    # Motorcycle endpoints
    path('motorcycles/', views.MotorcycleListCreateView.as_view(), name='motorcycle_list'),
    path('motorcycles/<int:pk>/', views.MotorcycleDetailView.as_view(), name='motorcycle_detail'),
    
    # Booking endpoints
    path('bookings/', views.BookingListCreateView.as_view(), name='booking_list'),
    path('bookings/<int:pk>/', views.BookingDetailView.as_view(), name='booking_detail'),
    path('bookings/<int:pk>/cancel/', views.BookingCancelView.as_view(), name='booking_cancel'),
]
