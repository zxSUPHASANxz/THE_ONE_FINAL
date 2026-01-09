from django.urls import path
from . import views
from . import views_web

app_name = 'booking'

urlpatterns = [
    # Web Views (Template-based) - requires login
    path('', views_web.booking_list_view, name='booking_list_web'),
    path('create/', views_web.booking_create_view, name='booking_create_web'),
    path('motorcycles/', views_web.motorcycles_view, name='motorcycles_web'),
    
    # API endpoints (JSON)
    path('api/motorcycles/', views.MotorcycleListCreateView.as_view(), name='motorcycle_list'),
    path('api/motorcycles/<int:pk>/', views.MotorcycleDetailView.as_view(), name='motorcycle_detail'),
    
    path('api/bookings/', views.BookingListCreateView.as_view(), name='booking_list'),
    path('api/bookings/<int:pk>/', views.BookingDetailView.as_view(), name='booking_detail'),
    path('api/bookings/<int:pk>/cancel/', views.BookingCancelView.as_view(), name='booking_cancel'),
]
