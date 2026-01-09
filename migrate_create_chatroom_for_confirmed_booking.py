# สคริปต์สำหรับสร้าง chat_room ย้อนหลังให้ booking ที่ยืนยันแล้วแต่ยังไม่มีห้องแชท
from booking.models import Booking
from chat.models import ChatRoom

count = 0
for b in Booking.objects.filter(status='confirmed').exclude(chat_room__isnull=False):
    if b.mechanic:
        ChatRoom.objects.create(booking=b, customer=b.customer, mechanic=b.mechanic)
        count += 1
print(f"สร้าง chat_room ย้อนหลังให้ {count} booking เรียบร้อยแล้ว!")
