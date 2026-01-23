@echo off
cd /d D:\Project\THE__ONE_V3
call .venv\Scripts\activate.bat
echo Deleting Pantip records...
python manage.py shell -c "from chatbot.models import KnowBase; deleted = KnowBase.objects.filter(source='pantip').delete(); print(f'Deleted {deleted[0]} records')"
echo.
echo Re-generating Honda embeddings...
python manage.py import_honda --gemini-key AIzaSyDu2sGMNZPdAIhZUp0tsZ_7DrKDPqhwhtY
echo.
echo Done! Check status:
python manage.py shell -c "from chatbot.models import KnowBase; total = KnowBase.objects.count(); with_embed = KnowBase.objects.exclude(embedding=None).count(); print(f'Total: {total}, With embeddings: {with_embed}')"
pause
