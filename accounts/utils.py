# accounts/utils.py
from django.core.mail import send_mail
import requests
from django.conf import settings

def send_email_otp(to_email, code):
    subject = "Your OTP Code"
    body = f"Your verification code is: {code}"
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)

def send_sms_otp(mobile, code, api_key=None):
    if not mobile:
        return
    api_key = api_key or getattr(settings, "FAST2SMS_API_KEY", None)
    if not api_key:
        return
    url = (
        "https://www.fast2sms.com/dev/bulkV2?"
        f"authorization={api_key}&route=q&message=Your%20OTP%20is%20{code}"
        f"&language=english&flash=0&numbers={mobile}"
    )
    try:
        requests.get(url, headers={"cache-control": "no-cache"}, timeout=20)
    except Exception:
        pass
