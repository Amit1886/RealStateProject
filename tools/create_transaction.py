import os
import django
import sys
from decimal import Decimal

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'khatapro.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from accounts.models import LedgerEntry as Transaction, UserProfile as Party

User = get_user_model()
user = User.objects.get(username='Demotest3')

print("\n" + "="*70)
print("CREATING TRANSACTION (ENTREE) FOR DEMOTEST3")
print("="*70)

# Step 1: Create a Party (Customer/Supplier) if not exists
print("\n[Step 1] Creating/Finding a Party...")
party, created = Party.objects.get_or_create(
    owner=user,
    name="Rajesh Customer",
    defaults={
        "party_type": "customer",
        "mobile": "9876543210",
        "email": "rajesh@example.com",
        "address": "123 Main Street, Delhi",
    }
)
if created:
    print("Created new party: {}".format(party.name))
else:
    print("Found existing party: {}".format(party.name))

# Step 2: Create a Transaction
print("\n[Step 2] Creating a Transaction (Entree)...")
transaction = Transaction.objects.create(
    party=party,
    txn_type="credit",  # "credit" = money received, "debit" = money paid
    txn_mode="cash",    # Payment method
    amount=Decimal("5000.00"),  # Amount in rupees
    date=timezone.now().date(),
    notes="Payment received for goods sold",
    gst_type="gst",  # GST applicable or not
)

print("Transaction Created!")
print("   Transaction ID: {}".format(transaction.id))
print("   Type: {}".format(transaction.get_txn_type_display()))  
print("   Amount: Rs {}".format(transaction.amount))
print("   Mode: {}".format(transaction.get_txn_mode_display()))
print("   Date: {}".format(transaction.date))
print("   Notes: {}".format(transaction.notes))
print("   Party: {}".format(party.name))

print("\n" + "="*60)
print("📚 HOW ENTREE (TRANSACTION) WORKS:")
print("="*60)

explanation = """
1. PARTY (पार्टी):
   - पहले एक Party बना सकते हो - कस्टमर या Supplier
   - Example: Rajesh Sharma (customer) या ABC Company (supplier)
   
2. TRANSACTION TYPES (लेन-देन के प्रकार):
   ✅ CREDIT (क्रेडिट) = तुम्हें पैसे मिले
      Example: Customer ने payment दिया = ₹5000 credit
   
   ❌ DEBIT (डेबिट) = तुम्हें पैसे देने हैं
      Example: Supplier को payment देनी है = ₹3000 debit
   
3. PAYMENT MODES (पेमेंट के तरीके):
   • Cash (नकद)
   • UPI
   • Online Transfer
   • Bank Transfer
   • Cheque

4. GST:
   • GST: 18% tax for commercial transactions
   • Non-GST: कोई tax नहीं

📌 REAL EXAMPLE:
   तुम्हारे पास एक दुकान है:
   - Customer "Rajesh" आता है और ₹5000 का सामान खरीदता है
   - वह नकद (cash) में payment देता है
   - तुम यह entry करते हो (Entree/Transaction):
     ✅ Party: Rajesh Sharma
     ✅ Type: Credit (तुम्हारे पास पैसे आये)
     ✅ Amount: ₹5000
     ✅ Mode: Cash
     
   अब तुम्हारे पास records हैं कि:
   - कب transaction हुआ?
   - कितना amount था?
   - किस party के साथ था?
   - payment कैसे हुआ?

🔗 USAGE IN SYSTEM:
   1. Dashboard में सभी transactions दिखते हैं
   2. Party Ledger में देख सकते हो कि किसी से कितना पैसा pending है
   3. Reports में सब transactions का track रहता है
   4. Financial statements बनते हैं (Profit & Loss, etc.)
"""

print(explanation)

print("\n" + "="*60)
print("✅ DONE! Transaction created successfully")
print("="*60)
print("\n📱 How to view it:")
print("   1. Go to /transactions/ page")
print("   2. You'll see all transactions")
print("   3. Click on any transaction to view details")
print("   4. Edit or delete if needed")
print()
