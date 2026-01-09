import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_one.settings')
django.setup()

from chatbot.models import KnowBase

print("Deleting Pantip records...")
deleted = KnowBase.objects.filter(source='pantip').delete()
print(f"✅ Deleted {deleted[0]} Pantip records")

total = KnowBase.objects.count()
print(f"📊 Remaining records: {total}")
