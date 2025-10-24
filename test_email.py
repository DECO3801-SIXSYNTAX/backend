import os
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SiPanit.settings')
BASE_DIR = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(BASE_DIR))

django.setup()

from django.core.mail import send_mail
from django.conf import settings

print("="*60)
print("EMAIL CONFIGURATION TEST")
print("="*60)
print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD)}")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print("="*60)

try:
    print("\n📧 Sending test email...")
    send_mail(
        subject='Test Email from SiPanit',
        message='This is a test email. If you receive this, email configuration works!',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.EMAIL_HOST_USER],  # Send to yourself
        fail_silently=False,
    )
    print("✅ Email sent successfully!")
    print("Check your inbox at:", settings.EMAIL_HOST_USER)
except Exception as e:
    print(f"❌ Email failed: {e}")
    import traceback
    traceback.print_exc()
    