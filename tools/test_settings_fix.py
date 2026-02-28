import os
import django
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'khatapro.settings')
django.setup()

from django.contrib.auth import get_user_model
from core_settings.permissions import has_feature

User = get_user_model()
user = User.objects.get(username='Demotest3')

result = has_feature(user, 'settings.advanced')
print(f"has_feature(Demotest3, 'settings.advanced') = {result}")

if result:
    print("✅ Settings access FIXED - should work now!")
else:
    print("❌ Settings access still blocked")
