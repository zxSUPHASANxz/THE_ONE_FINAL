from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

from . import views_web
from . import views_notification
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

app_name = 'users'

urlpatterns = [
    # Web Views (Template-based)
    path('login/', views_web.login_view, name='login'),
    path('register/', views_web.register_view, name='register_web'),
    path('logout/', views_web.logout_view, name='logout'),
    path('profile/', views_web.profile_view, name='profile_web'),
    
    # Direct Password Reset (No Email Verification)
    path('password-reset/', views_web.direct_password_reset_view, name='password_reset'),
    
    # Email Password Reset (Disabled for now)
    # path('password-reset/', 
    #      auth_views.PasswordResetView.as_view(
    #          template_name='users/password_reset/password_reset_form.html',
    #          email_template_name='users/password_reset/password_reset_email.html',
    #          success_url=reverse_lazy('users:password_reset_done')
    #      ), 
    #      name='password_reset'),
         
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/password_reset/password_reset_done.html'
         ), 
         name='password_reset_done'),
         
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/password_reset/password_reset_confirm.html',
             success_url=reverse_lazy('users:password_reset_complete')
         ), 
         name='password_reset_confirm'),
         
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/password_reset/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
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
