#!/usr/bin/env python
"""Delete duplicate bookings - keep only the first one"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_one.settings')
django.setup()

from booking.models import Booking
from mechanics.models import WorkQueue
from datetime import timedelta

print("=" * 60)
print("DUPLICATE BOOKING CLEANUP")
print("=" * 60)

# Find duplicates (same customer, motorcycle, within 2 minutes)
bookings = list(Booking.objects.order_by('id'))
duplicates_to_delete = []

for i, b1 in enumerate(bookings):
    for b2 in bookings[i+1:]:
        if (b1.customer_id == b2.customer_id and 
            b1.motorcycle_id == b2.motorcycle_id and
            abs((b1.created_at - b2.created_at).total_seconds()) < 120):  # 2 minutes
            # Keep the first one (b1), mark the later one (b2) for deletion
            duplicates_to_delete.append(b2.id)
            print(f"⚠️ Duplicate found: ID {b2.id} is duplicate of ID {b1.id}")
            print(f"   User: {b2.customer.username}")
            print(f"   Created: {b2.created_at}")

if duplicates_to_delete:
    print(f"\n{'=' * 60}")
    print(f"Found {len(duplicates_to_delete)} duplicate(s) to delete")
    
    confirm = input("Delete these duplicates? (yes/no): ")
    if confirm.lower() == 'yes':
        # Delete associated WorkQueue first
        WorkQueue.objects.filter(booking_id__in=duplicates_to_delete).delete()
        # Then delete bookings
        deleted_count = Booking.objects.filter(id__in=duplicates_to_delete).delete()[0]
        print(f"✅ Deleted {deleted_count} duplicate booking(s)")
    else:
        print("❌ Deletion cancelled")
else:
    print("✅ No duplicate bookings found!")

print("\n" + "=" * 60)
print(f"Total bookings remaining: {Booking.objects.count()}")
