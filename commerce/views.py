# ~/khata_pro/commerce/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json
import random
import string
import os

from .models import (
    Product, Warehouse, Order,                     # OrderItem removed because unused
    Payment, Stock, Invoice,ChatThread, ChatMessage, OrderItem, Category, SalesVoucher, SalesVoucherItem,
    Coupon, UserCoupon, CouponUsage
)
from khataapp.models import UserProfile
from django.db import transaction
from .forms import WarehouseForm
from .forms import OrderForm, OrderItemFormSet
from decimal import Decimal
from khataapp.models import Party
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image



def generate_unique_sku():
    """Generate a unique SKU code"""
    while True:
        sku = 'SKU' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Product.objects.filter(sku=sku).exists():
            return sku

@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = OrderItem.objects.filter(order=order)

    # Create a buffer for PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=20, leftMargin=20,
                            topMargin=20, bottomMargin=20)

    elements = []
    styles = getSampleStyleSheet()

    # ✅ Logo and Company Header
    company_name = "KhataPro Commerce"
    tagline = "Smart Accounting & Inventory System"
    logo_path = "/home/Khataapp/myproject/khatapro/static/images/logo.png"  # Change if needed

    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=60, height=60))
    elements.append(Paragraph(f"<b style='font-size:18px;color:#004aad'>{company_name}</b>", styles['Title']))
    elements.append(Paragraph(f"<font color='#0073e6'>{tagline}</font>", styles['Normal']))
    elements.append(Spacer(1, 12))

    # ✅ Blue Header Bar
    data = [[f"<b>INVOICE #{order.id}</b>", f"<b>Date:</b> {order.created_at.strftime('%d-%m-%Y')}"]]
    table = Table(data, colWidths=[250, 250])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0073e6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    # ✅ Party Details
    elements.append(Paragraph(f"<b>Order ID:</b> {order.id}", styles['Normal']))
    elements.append(Paragraph(f"<b>Owner:</b> {order.owner.email}", styles['Normal']))
    elements.append(Paragraph(f"<b>Placed by:</b> {order.placed_by}", styles['Normal']))
    elements.append(Paragraph(f"<b>Date:</b> {order.created_at.strftime('%d %b %Y, %I:%M %p')}", styles['Normal']))


    # ✅ Table Header
    table_data = [["Product", "Qty", "Price", "Subtotal"]]
    for item in items:
        table_data.append([
            item.product.name,
            f"{item.qty}",
            f"₹ {item.price:.2f}",
            f"₹ {item.subtotal:.2f}"
        ])

    # ✅ Add total row
    table_data.append(["", "", "Total:", f"₹ {order.total_amount():.2f}"])

    # ✅ Create item table
    t = Table(table_data, colWidths=[200, 80, 100, 120])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#004aad")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('BACKGROUND', (0, 1), (-1, -2), colors.whitesmoke),
        ('BACKGROUND', (-2, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # ✅ Footer Message
    elements.append(Paragraph(
        "<b>Thank you for your business!</b><br/>This is a computer-generated invoice.",
        styles['Normal']
    ))

    # Build the PDF
    doc.build(elements)

    # Return as response
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{order.id}.pdf"'
    response.write(pdf)
    return response

# ---------------- Utility ----------------
def is_paid_user(user):
    """Check if the user's plan allows Commerce access"""
    try:
        profile = UserProfile.objects.get(user=user)
        if profile.plan and profile.plan.name.lower() in ["basic", "premium", "pro"]:
            return True
        if hasattr(profile, "has_feature") and profile.has_feature("allow_commerce"):
            return True
    except Exception:
        pass
    return False


# ---------------- Dashboard ----------------
@login_required
def user_commerce_dashboard(request):
    """Commerce dashboard inside user account area"""
    if not is_paid_user(request.user):
        messages.error(request, "🚫 You do not have access to Commerce features.")
        return redirect("/accounts/dashboard/")

    context = {
        "products": Product.objects.filter(owner=request.user),
        "orders": Order.objects.filter(owner=request.user),
        "warehouses": Warehouse.objects.filter(owner=request.user) if hasattr(Warehouse, "owner") else Warehouse.objects.all(),
        "invoices": Invoice.objects.filter(owner=request.user) if hasattr(Invoice, "owner") else Invoice.objects.all(),
        "stocks": Stock.objects.all(),
        "payments": Payment.objects.all(),
        "threads": ChatThread.objects.all(),
        "is_paid": True
    }
    return render(request, "commerce/user_commerce_dashboard.html", context)


# ---------------- Product ----------------
def add_category(request):
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")

        if Category.objects.filter(name=name).exists():
            messages.error(request, "Category already exists!")
        else:
            Category.objects.create(
                name=name, description=description, owner=request.user
            )
            messages.success(request, "Category added successfully!")
            return redirect("commerce:add_category")

    categories = Category.objects.filter(owner=request.user)
    return render(request, "commerce/add_category.html", {"categories": categories})


def add_product(request):
    categories = Category.objects.filter(owner=request.user)
    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")
        stock = request.POST.get("stock")
        description = request.POST.get("description")
        category_id = request.POST.get("category")
        sku = request.POST.get("sku")
        unit = request.POST.get("unit")
        hsn_code = request.POST.get("hsn_code")
        gst_rate = request.POST.get("gst_rate")

        category = Category.objects.get(id=category_id) if category_id else None

        Product.objects.create(
            name=name,
            price=price,
            stock=stock,
            description=description,
            category=category,
            sku=sku,
            unit=unit,
            hsn_code=hsn_code,
            gst_rate=gst_rate,
            owner=request.user,
        )
        messages.success(request, "Product added successfully!")
        return redirect("commerce:product_list")

    return render(request, "commerce/add_product.html", {"categories": categories})


@login_required
def product_list(request):
    products = Product.objects.select_related("category").all()
    return render(request, "commerce/product_list.html", {
        "products": products
    })

@login_required
def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    return render(
        request,
        "commerce/product_detail.html",
        {"product": product}
    )


def product_create(request):
    """Add new product"""
    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")
        description = request.POST.get("description")
        stock = request.POST.get("stock")

        if not name or not price:
            messages.error(request, "Please fill all required fields.")
            return redirect("commerce:product_create")

        # Save product
        Product.objects.create(
            name=name,
            price=price,
            description=description or "",
            stock=stock or 0,
        )
        messages.success(request, f"✅ Product '{name}' added successfully!")
        return redirect("commerce:product_list")

    return render(request, "commerce/add_product.html")

def product_edit(request, pk):
    """Edit existing product"""
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        product.name = request.POST.get("name")
        product.price = request.POST.get("price")
        product.stock = request.POST.get("stock")
        product.description = request.POST.get("description")

        if not product.name or not product.price:
            messages.error(request, "Please fill all required fields.")
            return redirect("commerce:product_edit", pk=pk)

        product.save()
        messages.success(request, f"✅ Product '{product.name}' updated successfully!")
        return redirect("commerce:product_list")

    return render(request, "commerce/edit_product.html", {"product": product})

def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        product.delete()
        messages.success(request, "✅ Product deleted successfully.")
        return redirect("commerce:product_list")  # adjust as per your list view name

    return render(request, "commerce/product_confirm_delete.html", {"product": product})

def get_product_price(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        return JsonResponse({"price": str(product.price)})
    except Product.DoesNotExist:
        return JsonResponse({"price": "0.00"})

# ---------------- Warehouse ----------------
@login_required
def add_warehouse(request):
    if request.method == "POST":
        Warehouse.objects.create(
            name=request.POST.get("name"),
            location=request.POST.get("location"),
            capacity=request.POST.get("capacity", 0)
        )
        messages.success(request, "🏢 Warehouse added successfully!")
        return redirect("accounts:dashboard")
    return render(request, "commerce/add_warehouse.html")

def warehouse_create(request):
    if request.method == "POST":
        form = WarehouseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("commerce:warehouse_list")
    else:
        form = WarehouseForm()
    return render(request, "commerce/warehouse_form.html", {"form": form, "title": "Add New Warehouse"})


def warehouse_edit(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    if request.method == "POST":
        form = WarehouseForm(request.POST, instance=warehouse)
        if form.is_valid():
            form.save()
            return redirect("commerce:warehouse_list")
    else:
        form = WarehouseForm(instance=warehouse)
    return render(request, "commerce/warehouse_form.html", {"form": form, "title": "Edit Warehouse"})


def warehouse_list(request):
    warehouses = Warehouse.objects.all()
    return render(request, "commerce/warehouse_list.html", {"warehouses": warehouses})

def warehouse_delete(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    if request.method == "POST":
        warehouse.delete()
        messages.success(request, "✅ Warehouse deleted successfully!")
        return redirect("commerce:warehouse_list")  # make sure this name exists in urls.py
    return render(request, "commerce/warehouse_confirm_delete.html", {"warehouse": warehouse})


# ---------------- Stock ----------------
@login_required
def add_stock(request):
    products = Product.objects.all()
    warehouses = Warehouse.objects.all()

    if request.method == "POST":
        product_id = request.POST.get("product")
        warehouse_id = request.POST.get("warehouse")
        qty = request.POST.get("quantity")

        # ✅ Validate inputs
        if not (product_id and warehouse_id and qty):
            messages.error(request, "Please select product, warehouse, and quantity.")
            return render(request, "commerce/add_stock.html", {"products": products, "warehouses": warehouses})

        try:
            product = get_object_or_404(Product, id=product_id)
        except:
            messages.error(request, "Invalid product selected.")
            return redirect("commerce:add_stock")

        warehouse = Warehouse.objects.filter(id=warehouse_id).first()
        if not warehouse:
            messages.error(request, "Invalid warehouse selected.")
            return redirect("commerce:add_stock")


        try:
            qty = int(qty)
            if qty <= 0:
                messages.error(request, "Quantity must be greater than zero.")
                return redirect("commerce:add_stock")

        except ValueError:
            messages.error(request, "Invalid quantity value.")
            return redirect("commerce:add_stock")


        # ✅ Create Stock record
        Stock.objects.create(
            product=product,
            warehouse=warehouse,
            quantity=qty
        )

        messages.success(request, f"📦 {qty} units of {product.name} added to {warehouse.name} successfully!")
        return redirect("commerce:add_stock")


    # ✅ GET request → render form
    return render(request, "commerce/add_stock.html", {"products": products, "warehouses": warehouses})


# ---------------- Add Order ----------------
@login_required
def add_order(request):
    if request.method == "POST":
        try:
            with transaction.atomic():

                # Basic fields
                party_id = request.POST.get("party")
                order_type = request.POST.get("order_type") or "sale"
                notes = request.POST.get("notes")

                if not party_id:
                    messages.error(request, "Please select a party.")
                    return redirect("commerce:add_order")

                # Create Order
                order = Order.objects.create(
                    owner=request.user,
                    party_id=party_id,
                    order_type=order_type,
                    status="pending",
                    notes=notes,
                )

                # Lists
                products = request.POST.getlist("product[]")
                qtys = request.POST.getlist("qty[]")
                prices = request.POST.getlist("price[]")

                # Validate at least one valid row
                valid_items = False

                for p, q, r in zip(products, qtys, prices):
                    if p and q and r and float(q) > 0:
                        valid_items = True
                        OrderItem.objects.create(
                            order=order,
                            product_id=p,
                            qty=q,
                            price=r,
                        )

                if not valid_items:
                    messages.error(request, "Order must contain at least one item.")
                    order.delete()
                    return redirect("commerce:add_order")

                messages.success(request, f"Order #{order.id} created successfully")

                # Auto-send notifications
                party = order.party
                if party.email:
                    # Send email
                    pass  # Implement email sending
                if party.whatsapp_number:
                    # Send WhatsApp
                    pass  # Implement WhatsApp sending
                if party.mobile:
                    # Send SMS
                    pass  # Implement SMS sending

                # Redirect to order list
                return redirect("commerce:order_list")

        except Exception as e:
            messages.error(request, f"Error while saving order: {e}")
            return redirect("commerce:add_order")

    # GET REQUEST
    parties = Party.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")
    return render(
        request,
        "commerce/add_order.html",
        {"parties": parties, "products": products},
    )


@login_required
def sales_order_list(request):
    orders = (
        Order.objects
        .filter(order_type__iexact="sale")
        .select_related("party")
        .prefetch_related("items")
        .order_by("-created_at")
    )
    return render(
        request,
        "commerce/sales_order_list.html",
        {"orders": orders, "page_title": "Sales Orders"},
    )


@login_required
def purchase_order_list(request):
    orders = (
        Order.objects
        .filter(order_type__iexact="purchase")
        .select_related("party")
        .prefetch_related("items")
        .order_by("-created_at")
    )
    return render(
        request,
        "commerce/purchase_order_list.html",
        {"orders": orders, "page_title": "Purchase Orders"},
    )


# ---------------- Order List (User Side) ----------------
@login_required
def order_list(request):
    orders = (
        Order.objects
        .select_related("party")
        .prefetch_related("items")
        .order_by("-created_at")
    )
    return render(request, "commerce/order_list.html", {"orders": orders})

# ---------------- Order View (User Side) ----------------
@login_required
def view_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    return render(
        request,
        "commerce/view_order.html",
        {
            "order": order
        }
    )

# ---------------- Order Details (User Side) ----------------
@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, "commerce/order_detail.html", {"order": order})


# ---------------- Order Action (User Side) ----------------
@login_required
def order_action(request, order_id, action):
    order = get_object_or_404(Order, id=order_id)

    valid_actions = ["accept", "reject", "cancel"]
    if action not in valid_actions:
        messages.error(request, "Invalid action.")
        return redirect("commerce:order_list")

    # Accept Logic
    if action == "accept":
        order.status = "accepted"
        order.save()
        messages.success(request, f"Order #{order.id} accepted")

        # Accept ke baad automatic Voucher Page
        return redirect("commerce:sales_voucher_create", order_id=order.id)

    # Reject Logic
    if action == "reject":
        order.status = "rejected"
        order.save()
        messages.error(request, f"Order #{order.id} rejected")

    # Cancel Logic
    if action == "cancel":
        order.status = "cancelled"
        order.save()
        messages.warning(request, f"Order #{order.id} cancelled")

    return redirect("commerce:order_list")

# ---------------- Sales Voucher ----------------
@login_required
@transaction.atomic
def sales_voucher_create(request, order_id):
    """
    Create sales voucher using order_id.
    After save → redirect to Order List page.
    """
    order = get_object_or_404(Order, id=order_id)
    products = Product.objects.all()
    parties = Party.objects.all()

    if request.method == "POST":
        party_id = request.POST.get("party")
        is_gst = request.POST.get("is_gst") == "on"

        party = get_object_or_404(Party, id=party_id)

        # Create voucher
        voucher = SalesVoucher.objects.create(
            party=party,
            order=order,
            is_gst=is_gst,
            total_amount=0
        )

        # Item details
        product_ids = request.POST.getlist("product[]")
        qty_list = request.POST.getlist("qty[]")
        rate_list = request.POST.getlist("rate[]")
        gst_list = request.POST.getlist("gst_rate[]")

        total_amount = 0

        for i in range(len(product_ids)):
            if not product_ids[i]:
                continue

            product = get_object_or_404(Product, id=product_ids[i])
            qty = float(qty_list[i])
            rate = float(rate_list[i])
            gst_rate = float(gst_list[i])

            item_amount = qty * rate
            gst_amount = (item_amount * gst_rate) / 100 if is_gst else 0
            final_amount = item_amount + gst_amount
            total_amount += final_amount

            SalesVoucherItem.objects.create(
                voucher=voucher,
                product=product,
                qty=qty,
                rate=rate,
                gst_rate=gst_rate
            )

        # Update total amount
        voucher.total_amount = total_amount
        voucher.save()

        messages.success(
            request,
            f"Sales Voucher #{voucher.invoice_no} created successfully."
        )

        # Redirect to ORDER LIST
        return redirect("commerce:order_list")

    return render(
        request,
        "commerce/sales_voucher_create.html",
        {
            "order": order,
            "products": products,
            "parties": parties,
        }
    )


@login_required
def sales_voucher_detail(request, invoice_no):
    """
    Voucher detail with print and download options.
    """
    voucher = get_object_or_404(SalesVoucher, invoice_no=invoice_no)

    context = {
        "voucher": voucher,
        "print_url": f"/commerce/sales/voucher/{invoice_no}/print/",
        "download_url": f"/commerce/sales/voucher/{invoice_no}/download/",
    }

    return render(request, "commerce/sales_voucher_detail.html", context)


# ---------------- Invoice ----------------
@login_required
def add_invoice(request):
    """Create invoice for a selected order."""
    orders = Order.objects.all()

    if request.method == "POST":
        order_id = request.POST.get("order")

        if not order_id:
            messages.error(request, "⚠️ Please select an order.")
            return render(request, "commerce/add_invoice.html", {"orders": orders})

        order = get_object_or_404(Order, id=order_id)

        # Prevent duplicate invoice creation for same order
        if hasattr(order, "invoice"):
            messages.warning(request, "⚠️ Invoice already exists for this order.")
            return redirect("accounts:dashboard")

        try:
            Invoice.objects.create(order=order)
            messages.success(request, "🧾 Invoice created successfully!")
            return redirect("accounts:dashboard")

        except Exception as e:
            messages.error(request, f"❌ Error creating invoice: {str(e)}")

    return render(request, "commerce/add_invoice.html", {"orders": orders})


# ---------------- Payment ----------------
@login_required
def add_payment(request):
    if request.method == "POST":
        amount = request.POST.get("amount")
        mode = request.POST.get("mode")
        reference = request.POST.get("reference")
        note = request.POST.get("note")
        invoice_id = request.POST.get("invoice_id")

        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            messages.error(request, "❌ Invalid invoice selected.")
            return redirect("add_payment")

        Payment.objects.create(
            invoice=invoice,
            amount=amount,
            method=mode,
            reference=reference,
            note=note,
        )
        messages.success(request, "💰 Payment added successfully!")
        return redirect("accounts:dashboard")

    invoices = Invoice.objects.all()
    return render(request, "commerce/add_payment.html", {"invoices": invoices})


# ---------------- Chat ----------------
@login_required
def add_chat_thread(request):
    if request.method == "POST":
        party_id = request.POST.get("party")
        party = get_object_or_404(Party, id=party_id)
        ChatThread.objects.create(party=party)
        messages.success(request, "💬 Chat thread created!")
        return redirect("accounts:dashboard")

    parties = Party.objects.all()
    return render(request, "commerce/add_chat_thread.html", {"parties": parties})


@login_required
def add_chat_message(request):
    if request.method == "POST":
        thread_id = request.POST.get("thread")
        text = request.POST.get("text")
        thread = get_object_or_404(ChatThread, id=thread_id)
        ChatMessage.objects.create(thread=thread, message=text, sender=request.user)
        messages.success(request, "📨 Message sent successfully!")
        return redirect("accounts:dashboard")

    threads = ChatThread.objects.all()
    return render(request, "commerce/add_chat_message.html", {"threads": threads})

def chat_room(request, thread_id):
    """Show all messages of a specific chat thread."""
    thread = get_object_or_404(ChatThread, id=thread_id)
    messages = ChatMessage.objects.filter(thread=thread).order_by("timestamp")
    return render(request, "commerce/chat_room.html", {
        "thread": thread,
        "messages": messages,
    })

def api_chat_messages(request, thread_id):
    try:
        thread = ChatThread.objects.get(id=thread_id)
        messages = thread.messages.all().values(
            "id", "sent_by", "text", "attachment", "created_at", "is_read"
        )
        return JsonResponse(list(messages), safe=False)
    except ChatThread.DoesNotExist:
        return JsonResponse({"error": "Chat thread not found"}, status=404)


# ---------------- APIs ----------------
@csrf_exempt
@login_required
def api_chat_send(request, thread_id):
    if request.method == "POST":
        thread = get_object_or_404(ChatThread, id=thread_id)
        data = json.loads(request.body.decode("utf-8"))
        message = data.get("message", "").strip()
        if not message:
            return JsonResponse({"error": "Empty message"}, status=400)

        msg = ChatMessage.objects.create(
            thread=thread,
            sender=request.user,
            message=message,
            timestamp=timezone.now()
        )
        return JsonResponse({
            "id": msg.id,
            "sender": msg.sender.username,
            "message": msg.message,
            "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return JsonResponse({"error": "Only POST method allowed"}, status=405)


# ---------------- Coupons ----------------
@login_required
def coupon_list(request):
    """Admin view to list all coupons"""
    coupons = Coupon.objects.all().order_by("-created_at")
    return render(request, "commerce/coupon_list.html", {"coupons": coupons})

@login_required
def coupon_create(request):
    """Admin view to create new coupon"""
    if request.method == "POST":
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon created successfully!")
            return redirect("commerce:coupon_list")
    else:
        form = CouponForm()
    return render(request, "commerce/coupon_form.html", {"form": form, "title": "Create Coupon"})

@login_required
def coupon_edit(request, pk):
    """Admin view to edit coupon"""
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == "POST":
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon updated successfully!")
            return redirect("commerce:coupon_list")
    else:
        form = CouponForm(instance=coupon)
    return render(request, "commerce/coupon_form.html", {"form": form, "title": "Edit Coupon"})

@login_required
def coupon_delete(request, pk):
    """Admin view to delete coupon"""
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == "POST":
        coupon.delete()
        messages.success(request, "Coupon deleted successfully!")
        return redirect("commerce:coupon_list")
    return render(request, "commerce/coupon_confirm_delete.html", {"coupon": coupon})

@login_required
def user_coupon_list(request):
    """User view to list their coupons"""
    user_coupons = UserCoupon.objects.filter(user=request.user).select_related('coupon')
    return render(request, "commerce/user_coupon_list.html", {"user_coupons": user_coupons})

@login_required
def apply_coupon(request):
    """Apply a coupon to an order or cart"""
    if request.method == "POST":
        code = request.POST.get("code")
        # Implement coupon application logic here
        messages.success(request, f"Coupon {code} applied successfully!")
        return redirect("commerce:user_coupon_list")
    return render(request, "commerce/apply_coupon.html")

@login_required
def spin_wheel(request):
    """Spin the wheel to win a coupon"""
    if request.method == "POST":
        # Simple random win logic
        win = random.choice([True, False])
        if win:
            # Assign a random coupon
            coupon = Coupon.objects.filter(is_active=True).order_by('?').first()
            if coupon:
                UserCoupon.objects.get_or_create(user=request.user, coupon=coupon)
                messages.success(request, f"Congratulations! You won {coupon.title}")
            else:
                messages.info(request, "No coupons available right now.")
        else:
            messages.info(request, "Better luck next time!")
        return redirect("commerce:spin_wheel")
    return render(request, "commerce/spin_wheel.html")

@login_required
def scratch_card(request):
    """Scratch card to win a coupon"""
    if request.method == "POST":
        # Simple random win logic
        win = random.choice([True, False])
        if win:
            coupon = Coupon.objects.filter(is_active=True).order_by('?').first()
            if coupon:
                UserCoupon.objects.get_or_create(user=request.user, coupon=coupon)
                messages.success(request, f"Congratulations! You won {coupon.title}")
            else:
                messages.info(request, "No coupons available right now.")
        else:
            messages.info(request, "Better luck next time!")
        return redirect("commerce:scratch_card")
    return render(request, "commerce/scratch_card.html")

@login_required
def dashboard_with_coupons(request):
    """Dashboard showing coupons and user info"""
    user_coupons = UserCoupon.objects.filter(user=request.user).select_related('coupon')
    available_coupons = Coupon.objects.filter(is_active=True)
    context = {
        "user_coupons": user_coupons,
        "available_coupons": available_coupons,
    }
    return render(request, "commerce/dashboard_with_coupons.html", context)
