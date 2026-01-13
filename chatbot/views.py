from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ChatFAQ, ChatMessage
import json
import openai
from django.conf import settings

openai.api_key = settings.OPENAI_API_KEY


@csrf_exempt
def chatbot_reply(request):
    data = json.loads(request.body)
    user_msg = data.get("message","").lower()

    # 1️⃣ Create message entry
    chat = ChatMessage.objects.create(user_message=user_msg)

    # 2️⃣ Admin reply check
    if chat.admin_reply:
        chat.is_replied_by_admin = True
        chat.bot_reply = chat.admin_reply
        chat.save()
        return JsonResponse({"reply": chat.bot_reply})

    # 3️⃣ FAQ match
    for faq in ChatFAQ.objects.all():
        if faq.keyword.lower() in user_msg:
            chat.bot_reply = faq.answer
            chat.save()
            return JsonResponse({"reply": faq.answer})

    # 4️⃣ Default AI-style fallback
    smart_reply = (
        "Thanks for your message 🙏\n"
        "Our team will get back to you shortly.\n"
        "You can also contact us on WhatsApp 📞"
    )

    chat.bot_reply = smart_reply
    chat.save()
    return JsonResponse({"reply": smart_reply})


def get_ai_reply(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
              {"role":"system","content":"You are a polite Indian business assistant."},
              {"role":"user","content":message}
            ]
        )
        return response.choices[0].message.content
    except:
        return "Our executive will reply shortly 🙏"
