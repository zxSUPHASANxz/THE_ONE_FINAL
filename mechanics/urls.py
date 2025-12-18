from django.urls import path
from . import views

app_name = 'mechanics'

urlpatterns = [
    # Mechanic profile
    path('profile/', views.MechanicProfileView.as_view(), name='profile'),
    
    # Work queue
    path('queue/', views.WorkQueueListView.as_view(), name='queue_list'),
    path('queue/<int:pk>/accept/', views.AcceptWorkView.as_view(), name='accept_work'),
    path('queue/<int:pk>/reject/', views.RejectWorkView.as_view(), name='reject_work'),
    
    # Reviews
    path('reviews/', views.ReviewListView.as_view(), name='review_list'),
    path('reviews/create/', views.ReviewCreateView.as_view(), name='review_create'),
]
