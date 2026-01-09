# สคริปต์นี้จะ auto migrate chat_room ให้ booking ที่ยืนยันแล้วทันทีเมื่อรัน
from booking.models import Booking
from chat.models import ChatRoom

def migrate_chat_rooms():
    count = 0
    for b in Booking.objects.filter(status='confirmed').exclude(chat_room__isnull=False):
        if b.mechanic:
            ChatRoom.objects.create(booking=b, customer=b.customer, mechanic=b.mechanic)
            count += 1
    print(f"สร้าง chat_room ย้อนหลังให้ {count} booking เรียบร้อยแล้ว!")

if __name__ == "__main__":
    migrate_chat_rooms()
