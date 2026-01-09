"""
API Views for Chat
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer


class ChatRoomListView(generics.ListAPIView):
    """List all chat rooms for current user"""
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return ChatRoom.objects.filter(
            Q(customer=user) | Q(mechanic=user)
        ).select_related('customer', 'mechanic', 'booking').order_by('-updated_at')


class MessageListCreateView(generics.ListCreateAPIView):
    """List messages in a chat room or create new message"""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        chat_id = self.kwargs['pk']
        user = self.request.user
        
        # Verify user has access to this chat room
        ChatRoom.objects.get(
            Q(customer=user) | Q(mechanic=user),
            id=chat_id
        )
        
        return Message.objects.filter(
            chat_room_id=chat_id
        ).select_related('sender').order_by('created_at')
    
    def create(self, request, *args, **kwargs):
        chat_id = self.kwargs['pk']
        user = request.user
        
        # Verify user has access
        chat_room = ChatRoom.objects.get(
            Q(customer=user) | Q(mechanic=user),
            id=chat_id
        )
        
        # Create message
        message = Message.objects.create(
            chat_room=chat_room,
            sender=user,
            message=request.data.get('message', '')
        )
        
        # Update chat room timestamp
        chat_room.save()
        
        serializer = self.get_serializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MarkMessageReadView(APIView):
    """Mark message as read"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        user = request.user
        
        # Get message
        message = Message.objects.get(pk=pk)
        
        # Verify user is recipient
        if message.sender == user:
            return Response({'error': 'Cannot mark own message as read'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark as read
        message.is_read = True
        message.save()
        
        return Response({'status': 'marked as read'}, status=status.HTTP_200_OK)


class UnreadMessageCountView(APIView):
    """Get total unread message count for current user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get all chat rooms for this user
        chat_rooms = ChatRoom.objects.filter(
            Q(customer=user) | Q(mechanic=user)
        )
        
        # Count unread messages
        total_unread = 0
        for room in chat_rooms:
            total_unread += room.get_unread_count(user)
        
        return Response({
            'unread_count': total_unread
        }, status=status.HTTP_200_OK)
