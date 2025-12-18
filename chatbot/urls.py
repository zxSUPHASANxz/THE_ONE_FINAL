from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    # Chat endpoints
    path('sessions/', views.ChatSessionListCreateView.as_view(), name='session_list'),
    path('sessions/<str:session_id>/', views.ChatSessionDetailView.as_view(), name='session_detail'),
    path('messages/', views.ChatMessageCreateView.as_view(), name='message_create'),
    path('messages/<int:pk>/', views.ChatMessageDetailView.as_view(), name='message_detail'),
    
    # n8n webhook
    path('webhook/', views.N8NWebhookView.as_view(), name='n8n_webhook'),
    
    # Knowledge base
    path('knowledge/', views.MotorcycleKnowledgeListView.as_view(), name='knowledge_list'),
]
