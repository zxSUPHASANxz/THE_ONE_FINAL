from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
import requests
import uuid
from .models import ChatSession, ChatMessage, MotorcycleKnowledge
from .serializers import ChatSessionSerializer, ChatMessageSerializer, MotorcycleKnowledgeSerializer


class ChatSessionListCreateView(generics.ListCreateAPIView):
    """List all chat sessions or create a new one"""
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        session_id = str(uuid.uuid4())
        serializer.save(user=self.request.user, session_id=session_id)


class ChatSessionDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or update a chat session"""
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'session_id'
    
    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user)


class ChatMessageCreateView(generics.CreateAPIView):
    """Create a new chat message"""
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        # Create user message
        user_message = ChatMessage.objects.create(
            session_id=request.data.get('session'),
            sender='user',
            message=request.data.get('message')
        )
        
        # Send to n8n for processing
        try:
            n8n_url = settings.N8N_WEBHOOK_URL
            response = requests.post(n8n_url, json={
                'session_id': user_message.session.session_id,
                'user_message': user_message.message,
                'user_id': request.user.id
            }, timeout=10)
            
            if response.status_code == 200:
                bot_response = response.json().get('response', 'ขออภัย ไม่สามารถประมวลผลได้')
                n8n_data = response.json()
            else:
                bot_response = 'ขออภัย เกิดข้อผิดพลาดในการเชื่อมต่อ'
                n8n_data = None
        except Exception as e:
            bot_response = 'ขออภัย เกิดข้อผิดพลาดในการเชื่อมต่อ'
            n8n_data = {'error': str(e)}
        
        # Create bot response message
        bot_message = ChatMessage.objects.create(
            session=user_message.session,
            sender='bot',
            message=bot_response,
            n8n_response=n8n_data
        )
        
        return Response({
            'user_message': ChatMessageSerializer(user_message).data,
            'bot_message': ChatMessageSerializer(bot_message).data
        }, status=status.HTTP_201_CREATED)


class ChatMessageDetailView(generics.RetrieveAPIView):
    """Retrieve a chat message"""
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ChatMessage.objects.all()


class N8NWebhookView(APIView):
    """Webhook endpoint for n8n to send data back"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # Handle incoming data from n8n
        data = request.data
        
        # Save to knowledge base if it's scraping data
        if data.get('type') == 'knowledge':
            MotorcycleKnowledge.objects.create(
                brand=data.get('brand'),
                model=data.get('model'),
                problem_category=data.get('category'),
                symptom=data.get('symptom'),
                solution=data.get('solution'),
                source_url=data.get('source_url'),
                scraped_data=data
            )
        
        return Response({'status': 'success'}, status=status.HTTP_200_OK)


class MotorcycleKnowledgeListView(generics.ListAPIView):
    """List all motorcycle knowledge entries"""
    serializer_class = MotorcycleKnowledgeSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = MotorcycleKnowledge.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        brand = self.request.query_params.get('brand')
        model = self.request.query_params.get('model')
        category = self.request.query_params.get('category')
        
        if brand:
            queryset = queryset.filter(brand__icontains=brand)
        if model:
            queryset = queryset.filter(model__icontains=model)
        if category:
            queryset = queryset.filter(problem_category__icontains=category)
        
        return queryset

