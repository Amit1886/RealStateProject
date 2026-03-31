import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings

from .models import SMSProviderSettings

logger = logging.getLogger(__name__)


def _get_google_credentials() -> tuple[str, str]:
    provider = SMSProviderSettings.objects.filter(
        provider=SMSProviderSettings.Provider.GOOGLE, is_active=True
    ).first()

    api_key = (getattr(provider, "api_key", "") or "").strip() or (getattr(settings, "GOOGLE_SMS_API_KEY", "") or "").strip()
    sender_id = (getattr(provider, "sender_id", "") or "").strip() or (getattr(settings, "GOOGLE_SMS_SENDER_ID", "") or "").strip()
    return api_key, sender_id


def send_google_sms(mobile: str, text_message: str, image_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Send SMS via a Google Verified SMS / RCS gateway.

    Notes:
    - Google Verified SMS is typically accessed through partner gateways.
    - This implementation supports an override endpoint via settings.GOOGLE_SMS_API_URL.
    """
    mobile = (mobile or "").strip()
    text_message = (text_message or "").strip()

    api_key, sender_id = _get_google_credentials()
    if not api_key or not sender_id:
        return {
            "ok": False,
            "status": "not_configured",
            "error": "Missing GOOGLE_SMS_API_KEY/GOOGLE_SMS_SENDER_ID (or active SMSProviderSettings).",
        }

    api_url = (getattr(settings, "GOOGLE_SMS_API_URL", "") or "").strip()
    if not api_url:
        # Default to a placeholder endpoint; most deployments should override this.
        api_url = "https://verifiedsms.googleapis.com/v1/messages:send"

    payload: Dict[str, Any] = {
        "to": mobile,
        "sender_id": sender_id,
        "message": text_message,
    }
    if image_url:
        payload["image_url"] = image_url

    headers = {
        "Content-Type": "application/json",
        # Support common API-key header conventions.
        "X-API-KEY": api_key,
        "Authorization": f"Bearer {api_key}",
    }

    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=10)
        content_type = (resp.headers.get("content-type") or "").lower()
        if "application/json" in content_type:
            body: Any = resp.json()
        else:
            body = resp.text
        return {
            "ok": resp.ok,
            "status_code": resp.status_code,
            "response": body,
        }
    except Exception as exc:
        logger.exception("Google SMS send failed")
        return {
            "ok": False,
            "status": "exception",
            "error": str(exc),
        }
