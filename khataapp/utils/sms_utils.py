import requests

API_KEY = "YOUR_SMS_API_KEY"   # <-- यहां अपना actual API key डालो
SENDER_ID = "YOUR_SENDER_ID"   # <-- Sender ID

def send_sms(to, message):
    """
    to: string without '+', e.g. 9199xxxxxxx
    message: string text message
    Example API: Fast2SMS or any SMS provider
    """
    url = "https://www.fast2sms.com/dev/bulkV2"
    payload = {
        'sender_id': SENDER_ID,
        'message': message,
        'route': 'v3',
        'numbers': to
    }
    headers = {
        'authorization': API_KEY
    }
    resp = requests.post(url, data=payload, headers=headers)
    return resp.status_code, resp.text