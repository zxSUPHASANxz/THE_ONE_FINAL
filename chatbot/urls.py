from django.urls import path
from . import views
from . import views_web

app_name = 'chatbot'

urlpatterns = [
    # Web View (Template-based) - requires login
    path('', views_web.chatbot_view, name='chatbot_web'),
    
    # API endpoints (JSON)
    path('api/chat/', views.simple_chat_view, name='simple_chat'),  # Simple chat endpoint
    
    # Session history APIs (ChatGPT-like)
    path('api/sessions/', views.session_list_api, name='session_list_api'),
    path('api/sessions/create/', views.session_create_api, name='session_create_api'),
    path('api/sessions/<str:session_id>/', views.session_messages_api, name='session_messages_api'),
    path('api/sessions/<str:session_id>/rename/', views.session_rename_api, name='session_rename_api'),
    path('api/sessions/<str:session_id>/delete/', views.session_delete_api, name='session_delete_api'),
    
    # Legacy DRF endpoints
    path('sessions/', views.ChatSessionListCreateView.as_view(), name='session_list'),
    path('sessions/<str:session_id>/', views.ChatSessionDetailView.as_view(), name='session_detail'),
    path('messages/', views.ChatMessageCreateView.as_view(), name='message_create'),
    path('messages/<int:pk>/', views.ChatMessageDetailView.as_view(), name='message_detail'),
    
    # n8n webhook
    path('webhook/', views.N8NWebhookView.as_view(), name='n8n_webhook'),
    
    # Knowledge base
    path('knowledge/', views.KnowbaseListView.as_view(), name='knowledge_list'),
]
