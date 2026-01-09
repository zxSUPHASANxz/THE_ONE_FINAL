from django.urls import path
from . import views_web, views

app_name = 'chat'

urlpatterns = [
    # Web views
    path('', views_web.chat_list_view, name='list'),
    path('<int:chat_id>/', views_web.chat_detail_view, name='detail'),
    
    # API endpoints
    path('api/rooms/', views.ChatRoomListView.as_view(), name='api_rooms'),
    path('api/rooms/<int:pk>/messages/', views.MessageListCreateView.as_view(), name='api_messages'),
    path('api/messages/<int:pk>/read/', views.MarkMessageReadView.as_view(), name='api_mark_read'),
    path('api/unread-count/', views.UnreadMessageCountView.as_view(), name='api_unread_count'),
]
