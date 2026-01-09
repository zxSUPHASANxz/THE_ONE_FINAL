from django.db.models.signals import post_save
from django.dispatch import receiver
from booking.models import Booking
from .models import ChatRoom


@receiver(post_save, sender=Booking)
def create_chat_room(sender, instance, created, **kwargs):
    """
    Create chat room when booking is confirmed and has mechanic assigned
    """
    booking = instance
    
    # Create chat room when booking is confirmed and has mechanic
    if booking.status == 'confirmed' and booking.mechanic:
        # Check if chat room already exists
        if not hasattr(booking, 'chat_room'):
            ChatRoom.objects.create(
                booking=booking,
                customer=booking.customer,
                mechanic=booking.mechanic
            )
