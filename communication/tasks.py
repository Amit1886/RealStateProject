from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from communication.models import EmailLog, MessageLog, SMSLog
from notifications.services import notify_user


@shared_task
def send_email_log_task(email_log_id: int):
    email_log = EmailLog.objects.filter(id=email_log_id).first()
    if not email_log:
        return False
    if not email_log.recipient:
        email_log.status = EmailLog.Status.FAILED
        email_log.save(update_fields=["status"])
        return False
    email_log.status = EmailLog.Status.SENT
    email_log.sent_at = timezone.now()
    email_log.provider_ref = email_log.provider_ref or f"email-{email_log.id}"
    email_log.save(update_fields=["status", "sent_at", "provider_ref"])
    return True


@shared_task
def send_sms_log_task(sms_log_id: int):
    sms_log = SMSLog.objects.filter(id=sms_log_id).first()
    if not sms_log:
        return False
    if not sms_log.phone:
        sms_log.status = SMSLog.Status.FAILED
        sms_log.save(update_fields=["status"])
        return False
    sms_log.status = SMSLog.Status.SENT
    sms_log.sent_at = timezone.now()
    sms_log.provider_ref = sms_log.provider_ref or f"sms-{sms_log.id}"
    sms_log.save(update_fields=["status", "sent_at", "provider_ref"])
    return True


@shared_task
def send_whatsapp_message_task(message_log_id: int, whatsapp_number: str = ""):
    message_log = MessageLog.objects.filter(id=message_log_id).first()
    if not message_log:
        return False
    if not whatsapp_number:
        message_log.status = MessageLog.Status.FAILED
        message_log.save(update_fields=["status"])
        return False
    message_log.status = MessageLog.Status.SENT
    message_log.delivered_at = timezone.now()
    message_log.provider_ref = message_log.provider_ref or f"wa-{message_log.id}"
    message_log.save(update_fields=["status", "delivered_at", "provider_ref"])
    return True


@shared_task
def dispatch_in_app_notification_task(user_id: int, title: str, body: str = "", data=None):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.filter(id=user_id).first()
    if not user:
        return False
    notify_user(user=user, title=title, body=body, data=data or {})
    return True
