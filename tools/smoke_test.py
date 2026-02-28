import os
import django
import sys
import json

# Ensure project root is on sys.path so Django settings package can be imported
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'khatapro.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from products.models import Category, Product

User = get_user_model()

username = 'Demotest3'

user = User.objects.filter(username=username).first()
if not user:
    print(f"User {username} not found!")
    sys.exit(1)
print(f"Using user: {user.username}")

# create minimal category and product
cat, _ = Category.objects.get_or_create(name='TestCat', slug='testcat')
prod, _ = Product.objects.get_or_create(
    sku='TESTSKU1',
    defaults={
        'name': 'Test Product 1',
        'category': cat,
        'barcode': '000111222333',
        'gst_percent': 0,
        'mrp': '100.00',
        'b2b_price': '80.00',
        'b2c_price': '90.00',
        'wholesale_price': '70.00',
        'is_active': True,
    }
)
print(f"Product: {prod.sku} (id={prod.id})")

# Use DRF's APIClient with forced authentication
client = APIClient()
client.force_authenticate(user=user)

# Test quick_place
payload = {
    'items': [
        {'product_id': prod.id, 'qty': 1}
    ],
    'channel': 'pos',
}

print("\n-- quick_place test --")
resp = client.post(
    '/api/v1/orders/orders/quick_place/',
    payload,
    format='json'
)
print('status:', resp.status_code)
if resp.status_code in [200, 201]:
    print('response:', resp.data)
else:
    print('error:', resp.data if hasattr(resp, 'data') else resp.content[:500])

# test printers endpoint
print('\n-- printer test --')
print('posting to /api/v1/printers/print/')
pr = client.post(
    '/api/v1/printers/print/',
    {'items':[{'product_id': prod.id, 'qty':1}], 'total':100},
    format='json'
)
print('printer status:', pr.status_code)
if pr.status_code in [200, 201]:
    print('printer response:', pr.data)
else:
    print('printer error:', pr.data if hasattr(pr, 'data') else pr.content[:500])

print("\nDone!")

