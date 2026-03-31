from __future__ import annotations

from typing import Iterable

from django.conf import settings

from communication.models import EmailLog, MessageLog, SMSLog
from notifications.services import notify_user


def company_from_user(user):
    return getattr(user, "company", None) if user else None


def _run_task(task, *args):
    use_async = not getattr(settings, "RUNNING_TESTS", False) and not getattr(settings, "DISABLE_CELERY", False)
    if use_async:
        try:
            task.delay(*args)  # type: ignore[attr-defined]
            return
        except Exception:
            pass
    task(*args)


def log_message(*, sender=None, receiver=None, lead=None, message_type: str, message: str, metadata=None, provider: str = ""):
    return MessageLog.objects.create(
        company=company_from_user(sender) or company_from_user(receiver),
        sender=sender,
        receiver=receiver,
        lead=lead,
        message_type=message_type,
        message=message or "",
        provider=provider or "",
        metadata=metadata or {},
    )


def log_email(*, recipient: str, subject: str = "", body: str = "", sender: str = "", company=None, metadata=None):
    return EmailLog.objects.create(
        company=company,
        sender=sender or "",
        recipient=recipient,
        subject=subject or "",
        body=body or "",
        metadata=metadata or {},
    )


def log_sms(*, phone: str, message: str = "", company=None, metadata=None):
    return SMSLog.objects.create(
        company=company,
        phone=phone,
        message=message or "",
        metadata=metadata or {},
    )


def queue_notification_event(
    *,
    users: Iterable | None = None,
    title: str,
    body: str = "",
    lead=None,
    channels: list[str] | None = None,
    phone: str = "",
    email: str = "",
    whatsapp_number: str = "",
    sender=None,
    metadata=None,
):
    from communication.tasks import (
        dispatch_in_app_notification_task,
        send_email_log_task,
        send_sms_log_task,
        send_whatsapp_message_task,
    )

    channels = channels or ["in_app"]
    metadata = metadata or {}
    users = list(users or [])
    created = {"messages": [], "emails": [], "sms": []}

    if "in_app" in channels:
        for user in users:
            try:
                _run_task(dispatch_in_app_notification_task, user.id, title, body, metadata)
            except Exception:
                notify_user(user=user, title=title, body=body, data=metadata)

    if "email" in channels and email:
        email_log = log_email(
            recipient=email,
            subject=title,
            body=body,
            sender=getattr(sender, "email", "") if sender else "",
            company=company_from_user(sender) or (company_from_user(users[0]) if users else None),
            metadata=metadata,
        )
        created["emails"].append(email_log.id)
        _run_task(send_email_log_task, email_log.id)

    if "sms" in channels and phone:
        sms_log = log_sms(
            phone=phone,
            message=body,
            company=company_from_user(sender) or (company_from_user(users[0]) if users else None),
            metadata=metadata,
        )
        created["sms"].append(sms_log.id)
        _run_task(send_sms_log_task, sms_log.id)

    if "whatsapp" in channels and whatsapp_number:
        message_log = log_message(
            sender=sender,
            receiver=users[0] if users else None,
            lead=lead,
            message_type=MessageLog.MessageType.WHATSAPP,
            message=body,
            metadata=metadata,
            provider="whatsapp",
        )
        created["messages"].append(message_log.id)
        _run_task(send_whatsapp_message_task, message_log.id, whatsapp_number)

    return created
