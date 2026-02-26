from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.conf import settings
import requests
import uuid
import json
import logging
from .models import ChatSession, ChatMessage, Knowbase
from .serializers import ChatSessionSerializer, ChatMessageSerializer, KnowbaseSerializer

logger = logging.getLogger(__name__)


def generate_simple_response(message):
    """
    Fallback response generator when n8n is unavailable.
    Tries Gemini API first, then falls back to keyword matching.
    """
    # 1) Try Gemini API if available
    gemini_key = getattr(settings, 'GEMINI_API_KEY', '')
    if gemini_key:
        try:
            gemini_response = _call_gemini_api(message, gemini_key)
            if gemini_response:
                return gemini_response
        except Exception as e:
            logger.warning(f"Gemini API fallback failed: {e}")

    # 2) Keyword-based fallback
    msg = message.lower()

    if any(w in msg for w in ['สวัสดี', 'หวัดดี', 'hello', 'hi']):
        return 'สวัสดีครับ! 👋 ยินดีต้อนรับสู่ THE ONE AI ผมช่วยอะไรเกี่ยวกับรถจักรยานยนต์ได้บ้างครับ?'

    if any(w in msg for w in ['น้ำมัน', 'เปลี่ยนน้ำมัน', 'oil']):
        return ('🔧 **การเปลี่ยนน้ำมันเครื่อง**\n\n'
                'ควรเปลี่ยนน้ำมันเครื่องทุก 3,000–5,000 กม. หรือทุก 3–6 เดือน '
                'ขึ้นอยู่กับการใช้งานครับ\n\n'
                'หากต้องการจองคิวเปลี่ยนน้ำมัน สามารถไปที่เมนู **"จองตัวช่อม"** ได้เลยครับ!')

    if any(w in msg for w in ['เบรก', 'brake', 'ผ้าเบรก']):
        return ('🔧 **ระบบเบรก**\n\n'
                'ควรตรวจสอบผ้าเบรกทุก 10,000 กม. หากรู้สึกว่าเบรกไม่อยู่หรือมีเสียงดัง '
                'ควรนำรถเข้าตรวจทันทีครับ')

    if any(w in msg for w in ['ยาง', 'tire', 'ลม']):
        return ('🏍️ **การดูแลยาง**\n\n'
                'ตรวจเช็คลมยางทุกสัปดาห์ ค่าลมยางที่เหมาะสมอยู่ที่ 28-32 PSI (ดูตามคู่มือรถ) '
                'และควรเปลี่ยนยางเมื่อดอกยางสึกหรอครับ')

    if any(w in msg for w in ['จอง', 'booking', 'นัด', 'คิว']):
        return ('📅 หากต้องการจองคิวซ่อมรถ สามารถกดที่เมนู **"จองตัวช่อม"** ด้านบน '
                'หรือ [คลิกที่นี่](/booking/create/) เพื่อจองคิวได้เลยครับ!')

    if any(w in msg for w in ['ราคา', 'ค่า', 'price', 'cost']):
        return ('💰 ราคาค่าบริการขึ้นอยู่กับประเภทงานและรุ่นรถครับ\n\n'
                'สามารถจองคิวเพื่อให้ช่างประเมินราคาได้ฟรี!')

    if any(w in msg for w in ['ขอบคุณ', 'thank']):
        return 'ยินดีครับ! 😊 หากมีคำถามเพิ่มเติมสามารถถามได้ตลอดเลยนะครับ'

    # Default response
    return ('ขอบคุณสำหรับคำถามครับ 🙏\n\n'
            'ขออภัยครับ ตอนนี้ระบบ AI กำลังเชื่อมต่ออยู่ '
            'กรุณาลองใหม่อีกครั้งในอีกสักครู่ หรือสามารถจองคิวปรึกษาช่างได้โดยตรง '
            'ที่เมนู **"จองตัวช่อม"** ครับ')


def _call_gemini_api(message, api_key):
    """Call Google Gemini API for intelligent fallback responses."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    payload = {
        "contents": [{
            "parts": [{
                "text": (
                    "คุณเป็น AI ผู้เชี่ยวชาญด้านรถจักรยานยนต์ของระบบ THE ONE "
                    "ให้คำปรึกษาเกี่ยวกับการดูแลรักษารถมอเตอร์ไซค์ การซ่อมบำรุง "
                    "และปัญหาทั่วไป ตอบเป็นภาษาไทยสุภาพ กระชับ ไม่เกิน 200 คำ "
                    "ถ้าไม่เกี่ยวกับรถจักรยานยนต์ ให้บอกว่าเชี่ยวชาญเรื่องรถจักรยานยนต์เท่านั้น\n\n"
                    f"คำถาม: {message}"
                )
            }]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 500
        }
    }

    resp = requests.post(url, json=payload, timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        candidates = data.get('candidates', [])
        if candidates:
            parts = candidates[0].get('content', {}).get('parts', [])
            if parts:
                return parts[0].get('text', '')
    return None


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def simple_chat_view(request):
    """Simple chat endpoint without session management - sends to n8n"""
    message = request.data.get('message', '')
    
    if not message:
        return Response({
            'error': 'Message is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get n8n webhook URL from settings
        n8n_url = getattr(settings, 'N8N_WEBHOOK_URL', 'http://localhost:5678/webhook/chatbot-rag')
        
        # Always try to send to n8n first
        logger.info("Sending to n8n: %s", n8n_url)
        logger.info("User: %s (ID: %s, Type: %s)", request.user.username, request.user.id, request.user.user_type)
        logger.info("Message: %s", message)
        
        response = requests.post(n8n_url, json={
            'message': message,
            'user_id': request.user.id,
            'username': request.user.username,
        }, timeout=20)
        
        logger.info("n8n response status: %s", response.status_code)
        
        if response.status_code == 200:
            response_data = response.json()
            # n8n AI Agent returns 'output' field
            bot_response = response_data.get('output', response_data.get('response', response_data.get('text', 'ไม่สามารถประมวลผลได้')))
            logger.info("Bot response received (length: %d)", len(bot_response))
        else:
            logger.warning("n8n error: %s - %s", response.status_code, response.text[:200])
            bot_response = generate_simple_response(message)
            
    except requests.exceptions.Timeout:
        logger.warning("n8n timeout, using fallback response")
        bot_response = generate_simple_response(message)
    except requests.exceptions.RequestException as e:
        logger.warning("n8n connection error: %s", str(e))
        bot_response = generate_simple_response(message)
    except Exception as e:
        logger.error("Unexpected error in chat view: %s", str(e), exc_info=True)
        bot_response = generate_simple_response(message)
    
    return Response({
        'response': bot_response,
        'message': message
    }, status=status.HTTP_200_OK)
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
            Knowbase.objects.create(
                source=data.get('source', 'n8n'),
                title=data.get('title', f"{data.get('brand', '')} {data.get('model', '')}"),
                content=f"{data.get('symptom', '')}\n\n{data.get('solution', '')}",
                category=data.get('category', ''),
                brand=data.get('brand'),
                model=data.get('model'),
                source_url=data.get('source_url'),
                raw_data=data
            )
        
        return Response({'status': 'success'}, status=status.HTTP_200_OK)


class KnowbaseListView(generics.ListAPIView):
    """List all knowbase entries"""
    serializer_class = KnowbaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Knowbase.objects.filter(is_active=True)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        source = self.request.query_params.get('source')
        brand = self.request.query_params.get('brand')
        model = self.request.query_params.get('model')
        category = self.request.query_params.get('category')
        
        if source:
            queryset = queryset.filter(source=source)
        if brand:
            queryset = queryset.filter(brand__icontains=brand)
        if model:
            queryset = queryset.filter(model__icontains=model)
        if category:
            queryset = queryset.filter(category__icontains=category)
        
        return queryset

