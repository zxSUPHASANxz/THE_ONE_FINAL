from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.conf import settings
import requests
import uuid
from .models import ChatSession, ChatMessage, KnowlageDatabase
from .serializers import ChatSessionSerializer, ChatMessageSerializer, KnowlageDatabaseSerializer


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
        print(f"📤 Sending to n8n: {n8n_url}")
        print(f"👤 User: {request.user.username} (ID: {request.user.id}, Type: {request.user.user_type})")
        print(f"💬 Message: {message}")
        
        response = requests.post(n8n_url, json={
            'message': message,
            'user_id': request.user.id,
            'username': request.user.username,
            'user_type': request.user.user_type
        }, timeout=30)
        
        print(f"📥 n8n response status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            # n8n AI Agent returns 'output' field
            bot_response = response_data.get('output', response_data.get('response', response_data.get('text', 'ไม่สามารถประมวลผลได้')))
            print(f"✅ Bot response: {bot_response[:100]}...")
        else:
            print(f"⚠️ n8n error: {response.status_code} - {response.text[:200]}")
            bot_response = generate_simple_response(message)
            
    except requests.exceptions.Timeout:
        print("⏱️ n8n timeout, using fallback response")
        bot_response = generate_simple_response(message)
    except requests.exceptions.RequestException as e:
        print(f"❌ n8n connection error: {e}")
        bot_response = generate_simple_response(message)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        bot_response = generate_simple_response(message)
    
    return Response({
        'response': bot_response,
        'message': message
    }, status=status.HTTP_200_OK)


def generate_simple_response(message):
    """Generate a simple response based on keywords"""
    message_lower = message.lower()
    
    # Keywords mapping
    if any(word in message_lower for word in ['สวัสดี', 'หวัดดี', 'hello', 'hi']):
        return 'สวัสดีครับ! ผมคือ AI ผู้ช่วยของ THE ONE ยินดีให้คำปรึกษาเกี่ยวกับรถจักรยานยนต์ครับ'
    
    elif any(word in message_lower for word in ['สตาร์ท', 'ติด', 'เครื่อง']):
        return '''หากรถสตาร์ทไม่ติด อาจเกิดจากสาเหตุดังนี้:
1. 🔋 แบตเตอรี่หมด - ลองตรวจสอบไฟหน้ารถว่าสว่างหรือไม่
2. ⛽ น้ำมันหมด - ตรวจสอบปริมาณน้ำมันในถัง
3. 🔌 หัวเทียนชำรุด - อายุการใช้งานประมาณ 10,000-15,000 กม.
4. 🛢️ น้ำมันเครื่องน้อย - อาจทำให้เครื่องยนต์ล็อค

แนะนำให้นำรถเข้าตรวจสอบที่ THE ONE ครับ'''
    
    elif any(word in message_lower for word in ['เบรค', 'ห้าม']):
        return '''การดูแลระบบเบรค:
🛑 อาการที่ต้องระวัง:
- มีเสียงดังเวลาเบรค
- เบรคไม่แน่น ต้องบีบแรง
- มีเสียงเครือเวลาหยุด
- รถดันหรือเบรคด้านเดียว

💡 คำแนะนำ:
- ตรวจสอบผ้าเบรคทุก 5,000 กม.
- เปลี่ยนน้ำมันเบรคทุก 10,000 กม.
- อย่าปล่อยให้ผ้าเบรคบางจนหมด

หากพบอาการดังกล่าว แนะนำให้จองคิวซ่อมที่ THE ONE ครับ'''
    
    elif any(word in message_lower for word in ['น้ำมัน', 'เปลี่ยน', 'ถ่าย']):
        return '''การเปลี่ยนน้ำมันเครื่อง:
🛢️ ระยะเวลาเปลี่ยน:
- รถเครื่องเล็ก 100-150cc: ทุก 1,000-1,500 กม.
- รถเครื่องกลาง 250-500cc: ทุก 3,000-4,000 กม.
- รถเครื่องใหญ่ 600cc+: ทุก 5,000-6,000 กม.

💰 ราคาโดยประมาณ:
- น้ำมันสังเคราะห์: 250-500 บาท
- น้ำมันกึ่งสังเคราะห์: 150-300 บาท
- น้ำมันแร่: 80-150 บาท

จองคิวเปลี่ยนน้ำมันที่ THE ONE ได้เลยครับ!'''
    
    elif any(word in message_lower for word in ['ราคา', 'ค่า', 'เท่าไหร่']):
        return '''💰 ค่าบริการโดยประมาณ:

🔧 ซ่อมบำรุงทั่วไป: 300-800 บาท
⚙️ ซ่อมเครื่องยนต์: 1,000-5,000 บาท
🛑 ซ่อมเบรค: 500-1,500 บาท
⚡ ระบบไฟฟ้า: 500-2,000 บาท
🛞 เปลี่ยนยาง: 800-3,000 บาท

*ราคาอาจแตกต่างตามรุ่นรถและอะไหล่*

สามารถจองคิวเพื่อประเมินราคาที่แม่นยำได้ครับ!'''
    
    elif any(word in message_lower for word in ['จอง', 'นัด', 'คิว']):
        return 'คุณสามารถจองคิวซ่อมได้ที่หน้า "จองคิวซ่อม" หรือคลิกที่เมนูด้านบนครับ เพียงเลือกรถ วันที่ และประเภทการซ่อมที่ต้องการ เราจะดูแลรถของคุณอย่างดีที่สุดครับ!'
    
    else:
        return f'''ขอบคุณสำหรับคำถามครับ! 

สำหรับ "{message}" แนะนำให้คุณ:
1. 📝 จองคิวเพื่อตรวจสอบรถให้แน่ใจ
2. 🔍 ถ่ายรูปอาการส่งให้ช่างดู
3. 📞 โทรติดต่อ THE ONE โดยตรง

เรามีช่างมืออาชีพพร้อมให้บริการครับ!'''


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
            KnowlageDatabase.objects.create(
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


class KnowlageDatabaseListView(generics.ListAPIView):
    """List all knowledge database entries"""
    serializer_class = KnowlageDatabaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = KnowlageDatabase.objects.filter(is_active=True)
    
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
            queryset = queryset.filter(problem_category__icontains=category)
        
        return queryset

