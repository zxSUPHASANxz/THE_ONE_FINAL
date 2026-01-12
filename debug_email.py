import os
import django
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_one.settings')
django.setup()

def test_email():
    print(f"Current EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    
    print("\n--- Sending Test Email ---")
    try:
        send_mail(
            'Test Subject',
            'Test Message',
            'noreply@test.com',
            ['test@example.com'],
            fail_silently=False,
        )
        print("Test email sent successfully (check output above if using console backend)")
    except Exception as e:
        print(f"Error sending email: {e}")

    print("\n--- Existing Users ---")
    User = get_user_model()
    for user in User.objects.all():
        print(f"Username: {user.username}, Email: {user.email}")

if __name__ == "__main__":
    test_email()
