from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
from . import views_web
from . import views_notification

app_name = 'users'

urlpatterns = [
    # Web Views (Template-based)
    path('login/', views_web.login_view, name='login'),
    path('register/', views_web.register_view, name='register_web'),
    path('logout/', views_web.logout_view, name='logout'),
    path('profile/', views_web.profile_view, name='profile_web'),
    
    # Notification API Endpoints
    path('api/notifications/', views_notification.get_notifications, name='get_notifications'),
    path('api/notifications/<int:notification_id>/read/', views_notification.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/read-all/', views_notification.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('api/notifications/<int:notification_id>/delete/', views_notification.delete_notification, name='delete_notification'),
    
    # API Endpoints (JSON)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/register/', views.RegisterView.as_view(), name='register_api'),
    path('api/profile/', views.ProfileView.as_view(), name='profile_api'),
]
