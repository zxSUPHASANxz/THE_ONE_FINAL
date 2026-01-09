from django.db.models.signals import post_save
from django.dispatch import receiver
from booking.models import Booking
from chat.models import ChatRoom
from users.models import Notification
from django.contrib.auth import get_user_model


@receiver(post_save, sender=Booking)
def create_booking_notification(sender, instance, created, **kwargs):
    """
    Create notification when booking is created or status changes
    - NEW booking: notify all available mechanics
    - Status changes: notify customer
    - Cancellation: notify mechanic
    """
    booking = instance
    customer = booking.customer
    mechanic = booking.mechanic
    
    # Get motorcycle info safely
    motorcycle_text = "รถจักรยานยนต์"
    try:
        if booking.motorcycle:
            motorcycle_text = f"{booking.motorcycle.brand} {booking.motorcycle.model}"
    except Exception:
        pass
    
    if created:  # NEW BOOKING - notify all mechanics
        User = get_user_model()
        # Find all available mechanics
        all_mechanics = User.objects.filter(
            user_type='mechanic',
            mechanic_profile__is_available=True
        )
        
        for mech in all_mechanics:
            Notification.objects.create(
                user=mech,
                booking=booking,
                notification_type='new_booking_available',
                title='🆕 มีงานใหม่รอรับ!',
                message=f'ลูกค้า {customer.first_name or customer.username} จองคิวซ่อม {motorcycle_text} - การจอง #{booking.id}'
            )
        return  # Exit after handling new booking
    
    # EXISTING BOOKING - status update
    if not created:
        booking = instance
        customer = booking.customer
        mechanic = booking.mechanic

        # --- สร้าง ChatRoom อัตโนมัติเมื่อ booking ถูกยืนยัน ---
        if booking.status == 'confirmed' and mechanic:
            # ถ้ายังไม่มี chat_room ให้สร้าง
            if not hasattr(booking, 'chat_room'):
                ChatRoom.objects.create(
                    booking=booking,
                    customer=customer,
                    mechanic=mechanic
                )

        # Customer Notifications (exclude mechanics)
        if customer and customer.user_type != 'mechanic':
            notification_data = None
            
            if booking.status == 'confirmed':
                notification_data = {
                    'notification_type': 'booking_confirmed',
                    'title': '🎉 การจองได้รับการยืนยัน',
                    'message': f'ช่าง {mechanic.first_name} {mechanic.last_name} ได้รับงานของคุณแล้ว การจอง #{booking.id}'
                }
            elif booking.status == 'in_progress':
                notification_data = {
                    'notification_type': 'booking_in_progress',
                    'title': '🔧 เริ่มดำเนินการซ่อมแล้ว',
                    'message': f'ช่างกำลังซ่อมรถของคุณ การจอง #{booking.id}'
                }
            elif booking.status == 'completed':
                notification_data = {
                    'notification_type': 'booking_completed',
                    'title': '✅ งานเสร็จสิ้นแล้ว',
                    'message': f'ช่างได้ซ่อมรถของคุณเสร็จเรียบร้อยแล้ว การจอง #{booking.id}'
                }
            elif booking.status == 'cancelled':
                notification_data = {
                    'notification_type': 'booking_cancelled',
                    'title': '❌ การจองถูกยกเลิก',
                    'message': f'การจอง #{booking.id} ถูกยกเลิกแล้ว'
                }
            
            if notification_data:
                Notification.objects.create(
                    user=customer,
                    booking=booking,
                    **notification_data
                )
        
        # Mechanic Notifications (only for cancellation)
        if mechanic and mechanic.user_type == 'mechanic' and booking.status == 'cancelled':
            # Get motorcycle info safely
            motorcycle_text = "รถจักรยานยนต์"
            try:
                if booking.motorcycle:
                    motorcycle_text = f"{booking.motorcycle.brand} {booking.motorcycle.model}"
            except Exception:
                pass
            
            Notification.objects.create(
                user=mechanic,
                booking=booking,
                notification_type='work_cancelled_by_customer',
                title='❌ ลูกค้ายกเลิกงาน',
                message=f'ลูกค้ายกเลิกการจอง #{booking.id} - {motorcycle_text}'
            )
