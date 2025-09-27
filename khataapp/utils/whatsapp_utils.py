# khataapp/utils/whatsapp_utils.py
import requests

INSTANCE_ID = 'instance136750'   # <-- apna actual
TOKEN = 'opqr2t6es4k43x9o'       # <-- apna actual

def send_whatsapp_message(to, message):
    """
    UltraMsg docs: https://docs.ultramsg.com/
    to: string without '+'; e.g. 9199xxxxxxx
    """
    url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
    payload = {"to": to, "body": message}
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {TOKEN}",
    }
    resp = requests.post(url, data=payload, headers=headers, timeout=20)
    return resp.status_code, resp.text
