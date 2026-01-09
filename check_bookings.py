#!/usr/bin/env python
"""Check for duplicate bookings"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_one.settings')
django.setup()

from booking.models import Booking
from django.db.models import Count

print("=" * 60)
print("BOOKING ANALYSIS")
print("=" * 60)

# Total bookings
total = Booking.objects.count()
print(f"\nTotal bookings: {total}")

# Recent bookings
print("\n--- Recent Bookings (Last 15) ---")
for b in Booking.objects.order_by('-id')[:15]:
    motorcycle_plate = b.motorcycle.license_plate if b.motorcycle else "N/A"
    print(f"ID:{b.id} | {b.customer.username} | {b.status} | {b.created_at.strftime('%Y-%m-%d %H:%M:%S')} | {motorcycle_plate}")

# Check for potential duplicates (same user, same motorcycle, same date, created within 1 minute)
print("\n--- Checking for potential duplicates ---")
from django.utils import timezone
from datetime import timedelta

duplicates = []
bookings = list(Booking.objects.order_by('-id')[:20])
for i, b1 in enumerate(bookings):
    for b2 in bookings[i+1:]:
        if (b1.customer_id == b2.customer_id and 
            b1.motorcycle_id == b2.motorcycle_id and
            abs((b1.created_at - b2.created_at).total_seconds()) < 60):
            duplicates.append((b1.id, b2.id))
            print(f"⚠️ Possible duplicate: ID {b1.id} and ID {b2.id}")
            print(f"   User: {b1.customer.username}")
            print(f"   Created: {b1.created_at} vs {b2.created_at}")

if not duplicates:
    print("✅ No duplicate bookings found in recent records")

print("\n" + "=" * 60)
