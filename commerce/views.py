from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Warehouse, Order, OrderItem, ChatMessage, PartyPortal
from .forms import ProductForm, WarehouseForm, OrderForm, ChatMessageForm
from django.http import JsonResponse
from django.contrib import messages
from khataapp.models import Party, Transaction
from .forms import PartyForm, TransactionForm

# ------------------- Dashboard -------------------
def dashboard(request):
    """
    User dashboard view
    """
    return render(request, "commerce/dashboard.html")

# ------------------- Party Views -------------------
def party_list(request):
    parties = Party.objects.filter(owner=request.user)
    return render(request, "commerce/party_list.html", {"parties": parties})

def add_party(request):
    if request.method == "POST":
        form = PartyForm(request.POST, request.FILES)
        if form.is_valid():
            party = form.save(commit=False)
            party.owner = request.user
            party.save()
            messages.success(request, "Party added successfully!")
            return redirect("commerce:party_list")  # 👈 namespace use karo
    else:
        form = PartyForm()
    return render(request, "commerce/add_party.html", {"form": form})

# -------------------Transaction View  -------------------
def transaction_list(request):
    txns = Transaction.objects.filter(party__owner=request.user)
    return render(request, "commerce/transaction_list.html", {"transactions": txns})

def add_transaction(request):
    if request.method == "POST":
        party_id = request.POST.get("party")
        txn_type = request.POST.get("txn_type")
        amount = request.POST.get("amount")
        date = request.POST["date"]
        notes = request.POST.get("notes")
        party = Party.objects.get(id=party_id)
        Transaction.objects.create(
            party=party, txn_type=txn_type, amount=amount, date=date, notes=notes
        )
        # 👇 success message add karo
        messages.success(request, f"Transaction added successfully for {party.name} ({txn_type} ₹{amount})")
        return redirect("commerce:transaction_list")

    # 👇 yaha Party list bhejna jaruri hai
    parties = Party.objects.filter(owner=request.user)
    return render(request, "commerce/add_transaction.html", {"parties": parties})

# ------------------- Products -------------------
def product_list(request):
    products = Product.objects.all()
    return render(request, "commerce/products/product_list.html", {"products": products})

def product_create(request):
    form = ProductForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("commerce:product_list")
    return render(request, "commerce/products/product_form.html", {"form": form})

def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if form.is_valid():
        form.save()
        return redirect("commerce:product_list")
    return render(request, "commerce/products/product_form.html", {"form": form})

def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return redirect("commerce:product_list")

# ------------------- Warehouses -------------------
def warehouse_list(request):
    warehouses = Warehouse.objects.all()
    return render(request, "commerce/warehouses/warehouse_list.html", {"warehouses": warehouses})

def warehouse_create(request):
    form = WarehouseForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("commerce:warehouse_list")
    return render(request, "commerce/warehouses/warehouse_form.html", {"form": form})

def warehouse_edit(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    form = WarehouseForm(request.POST or None, instance=warehouse)
    if form.is_valid():
        form.save()
        return redirect("commerce:warehouse_list")
    return render(request, "commerce/warehouses/warehouse_form.html", {"form": form})

def warehouse_delete(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    warehouse.delete()
    return redirect("commerce:warehouse_list")

# ------------------- Orders -------------------
def order_list(request):
    orders = Order.objects.all()
    return render(request, "commerce/orders/order_list.html", {"orders": orders})

def order_create_user(request):
    form = OrderForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("commerce:order_list")
    return render(request, "commerce/orders/order_form.html", {"form": form})

def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    items = OrderItem.objects.filter(order=order)
    return render(request, "commerce/orders/order_detail.html", {"order": order, "items": items})

def order_accept(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order.status = "Accepted"
    order.save()
    return redirect("commerce:order_list")

def order_reject(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order.status = "Rejected"
    order.save()
    return redirect("commerce:order_list")

# ------------------- Chat -------------------
def chat_room(request, thread_id):
    messages_list = ChatMessage.objects.filter(thread_id=thread_id)
    form = ChatMessageForm(request.POST or None)
    return render(request, "commerce/chat/chat_room.html", {"messages": messages_list, "form": form})

def api_chat_messages(request, thread_id):
    messages_list = ChatMessage.objects.filter(thread_id=thread_id)
    pass  # JSON response implement kar sakte hain

def api_chat_send(request, thread_id):
    pass  # Message send API

# ------------------- Party Portal -------------------
def portal_home(request, token):
    portal = get_object_or_404(PartyPortal, token=token)
    context = {"portal": portal}
    return render(request, "commerce/portal_home.html", context)

def portal_products(request, token):
    portal = get_object_or_404(PartyPortal, token=token)
    products = Product.objects.filter(party=portal.party)
    return render(request, "commerce/portal_products.html", {"portal": portal, "products": products})

def portal_place_order(request, token):
    portal = get_object_or_404(PartyPortal, token=token)
    if request.method == "POST":
        order = Order.objects.create(party=portal.party)
        return JsonResponse({"status": "success", "order_id": order.id})
    return render(request, "commerce/portal_place_order.html", {"portal": portal})

def portal_chat_room(request, token):
    portal = get_object_or_404(PartyPortal, token=token)
    messages_list = ChatMessage.objects.filter(portal=portal).order_by("created_at")
    return render(request, "commerce/portal_chat_room.html", {"portal": portal, "messages": messages_list})

def portal_api_messages(request, token):
    portal = get_object_or_404(PartyPortal, token=token)
    messages_list = ChatMessage.objects.filter(portal=portal).order_by("created_at")
    data = [{"user": m.user.username, "text": m.text, "timestamp": m.created_at.isoformat()} for m in messages_list]
    return JsonResponse(data, safe=False)

def portal_api_send(request, token):
    if request.method == "POST":
        portal = get_object_or_404(PartyPortal, token=token)
        text = request.POST.get("text")
        chat_msg = ChatMessage.objects.create(portal=portal, text=text)
        return JsonResponse({"status": "success", "message": chat_msg.text})
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

