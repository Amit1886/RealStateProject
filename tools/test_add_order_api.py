#!/usr/bin/env python
"""
Quick test to verify Add Order page loads and has our keyboard improvements.
Run: python tools/test_add_order_api.py
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "khatapro.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()


def test_add_order_page():
    """Test that Add Order page loads with our changes."""
    client = Client()
    
    # Get or create test user
    user = User.objects.filter(username="Demotest3").first()
    if not user:
        print("⚠ Demotest3 user not found. Creating test user...")
        user = User.objects.create_user(username="test_user", password="test123")
    
    # Login
    client.login(username=user.username, password="Demo@123" if user.username == "Demotest3" else "test123")
    
    # Test page loads
    response = client.get("/commerce/add-order/")
    print(f"✓ Add Order page status: {response.status_code}")
    
    # Check for our improvements
    content = response.content.decode('utf-8', errors='ignore')
    
    checks = {
        "Sundry inline form": 'id="applySundry"' in content,
        "Keyboard F1 help":  'id="keyboardHelp"' in content,
        "Product table":     'id="orderTable"' in content,
        "Next step button":  'id="nextStep"' in content,
        "Sundry section inline": 'sundry-section-inline' in content,
    }
    
    # Also check the actual JS file for our changes
    js_file = "static/js/add_order_pc_busy.js"
    if os.path.exists(js_file):
        with open(js_file, 'r') as f:
            js_content = f.read()
            checks["Tab skip logic in JS"] = "skipAutoAdd" in js_content
            checks["Inline sundry listeners"] = "applySundryBtn.addEventListener" in js_content
    
    for check_name, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {check_name}")
    
    all_pass = all(checks.values())
    if all_pass:
        print("\n✓ All checks passed! Keyboard improvements are in place.")
    else:
        print("\n✗ Some checks failed. Review the HTML/JS changes.")
    
    return response.status_code == 200 and all_pass


if __name__ == "__main__":
    success = test_add_order_page()
    sys.exit(0 if success else 1)
