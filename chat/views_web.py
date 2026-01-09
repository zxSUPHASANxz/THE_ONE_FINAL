"""
Web Views for Chat
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import ChatRoom, Message


@login_required
def chat_list_view(request):
    """Show all chat rooms for current user"""
    user = request.user
    
    # Get all chat rooms where user is either customer or mechanic
    chat_rooms = ChatRoom.objects.filter(
        Q(customer=user) | Q(mechanic=user)
    ).select_related('customer', 'mechanic', 'booking__motorcycle').order_by('-updated_at')
    
    # Add unread count and other info for each room
    for room in chat_rooms:
        room.unread_count = room.get_unread_count(user)
        room.other_user = room.get_other_user(user)
        # Get last message
        room.last_message = room.messages.order_by('-created_at').first()
    
    context = {
        'chat_rooms': chat_rooms,
    }
    
    return render(request, 'chat/list.html', context)


@login_required
def chat_detail_view(request, chat_id):
    """Show messages in a specific chat room"""
    user = request.user
    
    # Get chat room
    chat_room = get_object_or_404(
        ChatRoom,
        Q(customer=user) | Q(mechanic=user),
        id=chat_id
    )
    
    # Mark all messages as read
    Message.objects.filter(
        chat_room=chat_room,
        is_read=False
    ).exclude(sender=user).update(is_read=True)
    
    # Get messages
    messages_list = chat_room.messages.select_related('sender').all()
    
    # Get other user
    other_user = chat_room.get_other_user(user)
    
    context = {
        'chat_room': chat_room,
        'messages': messages_list,
        'other_user': other_user,
    }
    
    return render(request, 'chat/detail.html', context)
