# ~/khata_pro/commerce/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
import json
import random
import string
import os
from django.contrib.auth import get_user_model

from .models import (
    Category,
    Product,
    Warehouse,
    Order,
    OrderItem,
    Invoice,
    Payment,
    Stock,
    ChatThread,
    ChatMessage,
    Coupon,
    UserCoupon,
    CouponUsage,
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

from commerce.services import build_reorder_plan, build_reorder_summary
from commerce.services.whatsapp_orders import (
    parse_whatsapp_order_message,
    create_order_from_parsed_items,
)
from chatbot.services.flow_engine import run_flow

User = get_user_model()



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
    elements.append(Paragraph(f"<b>Owner:</b> {(order.owner.email if order.owner else '-')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Placed by:</b> {order.placed_by}", styles['Normal']))
    elements.append(Paragraph(f"<b>Date:</b> {order.created_at.strftime('%d %b %Y, %I:%M %p')}", styles['Normal']))


    # ✅ Table Header
    table_data = [["Product", "Qty", "Price", "Subtotal"]]
    for item in items:
        product_name = "-"
        if getattr(item, "product", None):
            product_name = item.product.name
        elif getattr(item, "raw_name", None):
            product_name = item.raw_name
        line_total = item.line_total()
        table_data.append([
            product_name,
            f"{item.qty}",
            f"₹ {item.price:.2f}",
            f"₹ {line_total:.2f}"
        ])

    # ✅ Totals
    subtotal = order.subtotal_amount()
    discount = order.discount_amount or Decimal("0.00")
    tax = order.tax_amount or Decimal("0.00")
    sundry = order.bill_sundry_total()
    total = order.total_amount()
    table_data.append(["", "", "Subtotal:", f"₹ {subtotal:.2f}"])
    table_data.append(["", "", "Discount:", f"₹ {discount:.2f}"])
    table_data.append(["", "", "Tax:", f"₹ {tax:.2f}"])
    if sundry != Decimal("0.00"):
        table_data.append(["", "", "Bill Sundry:", f"₹ {sundry:.2f}"])
    table_data.append(["", "", "Total:", f"₹ {total:.2f}"])

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
@login_required
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


@login_required
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


@login_required
@require_GET
def get_product_stock(request, product_id):
    """
    Return per-warehouse stock for a product (used by PC Busy add-order popups).
    """
    product = get_object_or_404(Product, id=product_id)

    all_warehouses = Warehouse.objects.all().order_by("name")
    stock_map = {
        s["warehouse_id"]: (s["quantity"] or 0)
        for s in Stock.objects.filter(product_id=product.id).values("warehouse_id", "quantity")
    }
    warehouses = [
        {"id": w.id, "name": w.name, "quantity": int(stock_map.get(w.id, 0))}
        for w in all_warehouses
    ]

    total = sum((w["quantity"] or 0) for w in warehouses) if warehouses else int(product.stock or 0)

    return JsonResponse(
        {
            "product": {
                "id": product.id,
                "name": product.name,
                "unit": product.unit,
                "stock": int(product.stock or 0),
            },
            "total": total,
            "warehouses": warehouses,
        }
    )

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
                order_type_raw = (request.POST.get("order_type") or "sale").strip()
                order_type = {"sale": "SALE", "purchase": "PURCHASE"}.get(order_type_raw.lower(), order_type_raw)
                notes = request.POST.get("notes")
                bill_sundry_lines = []
                raw_bill_sundry = request.POST.get("bill_sundry_json")
                if raw_bill_sundry:
                    try:
                        parsed = json.loads(raw_bill_sundry)
                        if isinstance(parsed, list):
                            for line in parsed:
                                if not isinstance(line, dict):
                                    continue
                                name = str(line.get("name") or "").strip()
                                narration = str(line.get("narration") or "").strip()
                                rate = str(line.get("rate") or "").strip()
                                try:
                                    amount = Decimal(str(line.get("amount") or "0")).quantize(Decimal("0.01"))
                                except Exception:
                                    amount = Decimal("0.00")
                                if name or narration or rate or amount != Decimal("0.00"):
                                    bill_sundry_lines.append(
                                        {
                                            "name": name,
                                            "narration": narration,
                                            "rate": rate,
                                            "amount": str(amount),
                                        }
                                    )
                    except Exception:
                        bill_sundry_lines = []

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
                    bill_sundry=bill_sundry_lines,
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

                # Recompute totals after items are created
                order.save()

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


@login_required
def sales_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, order_type__iexact="sale")
    items = order.items.select_related("product")
    return render(
        request,
        "commerce/sales_order_detail.html",
        {
            "order": order,
            "items": items,
        },
    )


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
        method = request.POST.get("method")
        reference = request.POST.get("reference")
        note = request.POST.get("note")
        invoice_id = request.POST.get("invoice_id")
        payment_date = request.POST.get("payment_date")
        payment_proof = request.FILES.get("payment_proof")
        final_notes = request.POST.get("final_notes")

        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            messages.error(request, "❌ Invalid invoice selected.")
            return redirect("commerce:add_payment")

        # Combine notes
        combined_note = note or ""
        if final_notes:
            combined_note += "\n" + final_notes

        Payment.objects.create(
            invoice=invoice,
            amount=amount,
            method=method,
            reference=reference,
            note=combined_note,
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

# ---------------- WhatsApp Orders ----------------
PAYMENT_MODES = {
    "cash": "Cash",
    "paytm": "Paytm",
    "cod": "Cash on Delivery",
    "netbanking": "Netbanking",
}


def _wa_help_text():
    return (
        "Welcome! Quick options (reply text):\n"
        "[products] [cart] [checkout]\n"
        "You can also type:\n"
        "- category <name>\n"
        "- add <qty> <product>\n"
        "- pay cash/paytm/cod/netbanking"
    )


def _wa_categories_text(owner, party):
    categories = Category.objects.filter(owner=owner).order_by("name")
    if not categories.exists():
        categories = Category.objects.all().order_by("name")
    if not categories.exists():
        return "No categories found."

    cat_lines = "\n".join([f"- {c.name}" for c in categories])
    segment = party.customer_category or "General"
    return f"Customer segment: {segment}\nCategories:\n{cat_lines}\nQuick: [category <name>] [cart]"


def _wa_products_in_category(owner, category_name):
    category = Category.objects.filter(owner=owner, name__iexact=category_name).first()
    if not category:
        category = Category.objects.filter(name__iexact=category_name).first()
    if not category:
        return "Category not found. Type 'products' to see categories."

    products = Product.objects.filter(category=category, owner=owner).order_by("name")
    if not products.exists():
        products = Product.objects.filter(category=category).order_by("name")
    if not products.exists():
        return f"No products in {category.name}."

    lines = "\n".join([f"- {p.name} (Rs. {p.price})" for p in products])
    return f"{category.name} products:\n{lines}\nQuick: [add <qty> <product>] [cart]"


def _wa_cart_text(session):
    items = session.cart_items.select_related("product")
    if not items.exists() and not session.unmatched_items:
        return "Your cart is empty. Type 'products' to browse."

    lines = []
    total = Decimal("0.00")
    for item in items:
        line_total = item.quantity * item.unit_price
        total += line_total
        lines.append(f"- {item.product.name} x {item.quantity} = Rs. {line_total}")

    for item in session.unmatched_items:
        lines.append(f"- {item.get('name')} x {item.get('qty')} (manual review)")

    lines.append(f"Total: Rs. {total}")
    lines.append("Type 'checkout' to place order.")
    return "\n".join(lines)


def _wa_strip_verbs(text):
    lower = text.lower().strip()
    for verb in ["add ", "order ", "buy ", "need ", "want "]:
        if lower.startswith(verb):
            return text[len(verb):].strip()
    return text


@login_required
def whatsapp_order_inbox(request):
    inbox = WhatsAppOrderInbox.objects.filter(owner=request.user).select_related("party", "order")[:200]
    return render(request, "commerce/whatsapp_order_inbox.html", {"inbox": inbox})


@login_required
@require_POST
def whatsapp_order_action(request, inbox_id, action):
    inbox = get_object_or_404(WhatsAppOrderInbox, id=inbox_id, owner=request.user)
    if action == "approve":
        inbox.status = "approved"
        if inbox.order:
            inbox.order.status = "accepted"
            inbox.order.save(update_fields=["status"])
        inbox.save(update_fields=["status"])
        messages.success(request, f"WhatsApp order #{inbox.id} approved.")
    elif action == "reject":
        inbox.status = "rejected"
        if inbox.order:
            inbox.order.status = "rejected"
            inbox.order.save(update_fields=["status"])
        inbox.save(update_fields=["status"])
        messages.error(request, f"WhatsApp order #{inbox.id} rejected.")
    elif action == "manual":
        inbox.status = "manual_review"
        inbox.save(update_fields=["status"])
        messages.info(request, f"WhatsApp order #{inbox.id} moved to manual review.")
    else:
        messages.error(request, "Invalid action.")
    return redirect("commerce:whatsapp_order_inbox")


@csrf_exempt
@require_POST
def api_whatsapp_order_inbox(request):
    """
    Chatbot intake endpoint for WhatsApp messages.
    Expected JSON:
    {
      "mobile": "9999999999",
      "message": "1 atta, 2 milk",
      "owner_id": 1,
      "customer_name": "Ravi",
      "address": "..."
    }
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    mobile = (payload.get("mobile") or "").strip()
    message = (payload.get("message") or "").strip()
    owner_id = payload.get("owner_id")
    customer_name = (payload.get("customer_name") or "").strip()
    address = (payload.get("address") or "").strip()

    if not mobile or not message:
        return JsonResponse({"error": "mobile and message are required"}, status=400)

    party = Party.objects.filter(whatsapp_number=mobile).first() or Party.objects.filter(mobile=mobile).first()
    owner = party.owner if party else None

    if not owner and owner_id:
        owner = User.objects.filter(id=owner_id).first()

    if not owner and request.user.is_authenticated:
        owner = request.user

    if not owner:
        return JsonResponse({"error": "Unable to determine owner for this message"}, status=400)

    if not party:
        party = Party.objects.create(
            owner=owner,
            name=customer_name or f"WhatsApp Customer {mobile[-4:]}",
            mobile=mobile,
            whatsapp_number=mobile,
            address=address or "",
            party_type="customer",
        )

    session, created = WhatsAppSession.objects.get_or_create(
        owner=owner,
        mobile_number=mobile,
        defaults={"party": party},
    )
    if not session.party:
        session.party = party
        session.save(update_fields=["party"])

    text = message.strip()
    text_lower = text.lower()

    if text_lower in ["hi", "hello", "start", "menu", "help"]:
        return JsonResponse({"reply": _wa_help_text()})

    if text_lower in ["products", "product list", "catalog", "list"]:
        if session.state != "browsing":
            session.state = "browsing"
            session.save(update_fields=["state"])
        return JsonResponse({"reply": _wa_categories_text(owner, party)})

    if text_lower.startswith("category "):
        if session.state != "browsing":
            session.state = "browsing"
            session.save(update_fields=["state"])
        category_name = text[9:].strip()
        return JsonResponse({"reply": _wa_products_in_category(owner, category_name)})

    if text_lower in ["cart", "my cart", "basket"]:
        return JsonResponse({"reply": _wa_cart_text(session)})

    if text_lower in ["checkout", "place order", "submit", "order submit"]:
        if not session.cart_items.exists() and not session.unmatched_items:
            return JsonResponse({"reply": "Your cart is empty. Add items first."})
        session.state = "awaiting_payment"
        session.save(update_fields=["state"])
        return JsonResponse({
            "reply": "Select payment mode: cash, paytm, cod, netbanking"
        })

    if text_lower in PAYMENT_MODES:
        if session.state != "awaiting_payment":
            return JsonResponse({"reply": "Type 'checkout' to select payment mode."})

        session.selected_payment_mode = text_lower
        session.save(update_fields=["selected_payment_mode"])

        # Create order only on submit/payment selection
        order = Order.objects.create(
            owner=owner,
            party=party,
            order_type="SALE",
            status="pending",
            notes=f"WhatsApp order from {mobile}",
            order_source="WhatsApp",
        )

        for item in session.cart_items.select_related("product"):
            OrderItem.objects.create(
                order=order,
                product=item.product,
                qty=item.quantity,
                price=item.unit_price,
            )

        for item in session.unmatched_items:
            OrderItem.objects.create(
                order=order,
                product=None,
                qty=item.get("qty", 1),
                price=Decimal("0.00"),
                raw_name=item.get("name", "Unknown"),
            )

        invoice = Invoice.objects.create(order=order)
        Payment.objects.create(
            invoice=invoice,
            amount=order.total_amount(),
            method=PAYMENT_MODES[text_lower],
            note="WhatsApp payment selection",
        )

        inbox_status = "new" if not session.unmatched_items else "manual_review"
        WhatsAppOrderInbox.objects.create(
            owner=owner,
            party=party,
            mobile_number=mobile,
            customer_name=party.name,
            raw_message=message,
            parsed_items=[
                {
                    "raw_name": item.product.name,
                    "quantity": item.quantity,
                    "matched": True,
                    "product_id": item.product.id,
                    "confidence": 1.0,
                    "status": "matched",
                }
                for item in session.cart_items.select_related("product")
            ] + [
                {
                    "raw_name": item.get("name", "Unknown"),
                    "quantity": item.get("qty", 1),
                    "matched": False,
                    "product_id": None,
                    "confidence": 0.0,
                    "status": "manual_review",
                }
                for item in session.unmatched_items
            ],
            status=inbox_status,
            order=order,
        )

        session.cart_items.all().delete()
        session.unmatched_items = []
        session.state = "completed"
        session.save(update_fields=["unmatched_items", "state"])

        return JsonResponse({
            "reply": f"Order #{order.id} placed. Total Rs. {order.total_amount()}. Payment: {PAYMENT_MODES[text_lower]}."
        })

    # Remove item
    if text_lower.startswith("remove "):
        if session.state != "browsing":
            session.state = "browsing"
            session.save(update_fields=["state"])
        remove_text = _wa_strip_verbs(text)
        products = Product.objects.filter(owner=owner)
        if not products.exists():
            products = Product.objects.all()
        parsed = parse_whatsapp_order_message(remove_text, products)
        if parsed and parsed[0].matched_product:
            WhatsAppCartItem.objects.filter(session=session, product=parsed[0].matched_product).delete()
            return JsonResponse({"reply": "Removed item. Type 'cart' to view."})
        return JsonResponse({"reply": "Product not found in cart."})

    if text_lower in ["clear cart", "clear", "empty cart"]:
        if session.state != "browsing":
            session.state = "browsing"
            session.save(update_fields=["state"])
        session.cart_items.all().delete()
        session.unmatched_items = []
        session.save(update_fields=["unmatched_items"])
        return JsonResponse({"reply": "Cart cleared."})

    # Default: try to add items
    if session.state != "browsing":
        session.state = "browsing"
        session.save(update_fields=["state"])
    cleaned = _wa_strip_verbs(text)
    products = Product.objects.filter(owner=owner)
    if not products.exists():
        products = Product.objects.all()
    parsed_items = parse_whatsapp_order_message(cleaned, products)

    added = []
    unmatched = []
    for item in parsed_items:
        if item.matched_product:
            cart_item, _ = WhatsAppCartItem.objects.get_or_create(
                session=session,
                product=item.matched_product,
                defaults={"quantity": 0, "unit_price": item.matched_product.price},
            )
            cart_item.quantity += item.quantity
            cart_item.unit_price = item.matched_product.price
            cart_item.save(update_fields=["quantity", "unit_price"])
            added.append(f"{item.matched_product.name} x {item.quantity}")
        else:
            unmatched.append({"name": item.raw_name, "qty": item.quantity})

    if unmatched:
        session.unmatched_items = (session.unmatched_items or []) + unmatched
        session.save(update_fields=["unmatched_items"])

    if added or unmatched:
        reply_bits = []
        if added:
            reply_bits.append("Added: " + ", ".join(added))
        if unmatched:
            reply_bits.append("Manual review: " + ", ".join([f"{u['name']} x {u['qty']}" for u in unmatched]))
        reply_bits.append("Type 'cart' to review or 'checkout' to place order.")
        return JsonResponse({"reply": "\n".join(reply_bits)})

    flow_reply = run_flow(message)
    if flow_reply:
        return JsonResponse({"reply": flow_reply})

    return JsonResponse({"reply": "Sorry, I could not understand. Type 'help' for options."})


@require_GET
def api_orders_live_feed(request):
    owner_id = request.GET.get("owner_id")
    owner = None
    if request.user.is_authenticated:
        owner = request.user
    if not owner and owner_id:
        owner = User.objects.filter(id=owner_id).first()

    if not owner:
        return JsonResponse({"error": "owner not resolved"}, status=400)

    today = timezone.now().date()
    orders = (
        Order.objects.filter(owner=owner, order_source__iexact="whatsapp")
        .select_related("party")
        .order_by("-created_at")[:10]
    )
    total_today = Order.objects.filter(
        owner=owner,
        order_source__iexact="whatsapp",
        created_at__date=today,
    )

    total_today_count = total_today.count()
    total_sales_today = sum([o.total_amount() for o in total_today])

    data = {
        "total_orders_today": total_today_count,
        "total_sales_today": float(total_sales_today),
        "latest_orders": [
            {
                "id": o.id,
                "order_no": f"#{o.id}",
                "customer_name": o.party.name if o.party else "Unknown",
                "mobile": o.party.mobile if o.party else "",
                "total": float(o.total_amount()),
                "created_at": o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for o in orders
        ],
    }
    return JsonResponse(data)

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


# ---------------- AI Reorder Planner ----------------
def _parse_budget(request, default=None):
    if default is None:
        from commerce.models import CommerceAISettings
        settings_obj = CommerceAISettings.objects.first() or CommerceAISettings.objects.create()
        default = settings_obj.default_budget
    raw = request.GET.get("budget") or request.POST.get("budget")
    if raw is None:
        return default
    try:
        return Decimal(str(raw))
    except Exception:
        return default


@login_required
@require_GET
def ai_reorder_plan_view(request):
    budget = _parse_budget(request, default=Decimal("50000"))
    from commerce.models import CommerceAISettings
    settings_obj = CommerceAISettings.objects.first() or CommerceAISettings.objects.create()
    target_days = request.GET.get("target_days", settings_obj.default_target_days)
    plan = build_reorder_plan(
        user=request.user,
        budget=budget,
        target_stock_days=target_days,
    )
    context = {
        "plan": plan,
        "budget": budget,
        "target_days": target_days,
    }
    return render(request, "commerce/reorder_plan.html", context)


@login_required
@require_GET
def supplier_po_view(request):
    budget = _parse_budget(request, default=Decimal("50000"))
    from commerce.models import CommerceAISettings
    settings_obj = CommerceAISettings.objects.first() or CommerceAISettings.objects.create()
    target_days = request.GET.get("target_days", settings_obj.default_target_days)
    plan = build_reorder_plan(
        user=request.user,
        budget=budget,
        target_stock_days=target_days,
    )
    return render(request, "commerce/supplier_po.html", {"plan": plan, "budget": budget, "target_days": target_days})


@login_required
@require_GET
def api_ai_reorder_plan(request):
    budget = _parse_budget(request, default=Decimal("50000"))
    from commerce.models import CommerceAISettings
    settings_obj = CommerceAISettings.objects.first() or CommerceAISettings.objects.create()
    target_days = request.GET.get("target_days", settings_obj.default_target_days)
    plan = build_reorder_plan(
        user=request.user,
        budget=budget,
        target_stock_days=target_days,
    )
    return JsonResponse(plan, safe=False)


@login_required
@require_GET
def api_dashboard_reorder_summary(request):
    budget = _parse_budget(request, default=Decimal("50000"))
    from commerce.models import CommerceAISettings
    settings_obj = CommerceAISettings.objects.first() or CommerceAISettings.objects.create()
    target_days = request.GET.get("target_days", settings_obj.default_target_days)
    summary = build_reorder_summary(
        user=request.user,
        budget=budget,
        target_stock_days=target_days,
    )
    return JsonResponse(summary, safe=False)


@require_GET
def api_dashboard_reorder_summary_health(request):
    return JsonResponse({"status": "ok", "service": "dashboard_reorder_summary"})


@require_GET
def api_ai_reorder_plan_health(request):
    return JsonResponse({"status": "ok", "service": "ai_reorder_plan"})


@login_required
@require_POST
def api_ai_generate_po(request):
    budget = _parse_budget(request, default=Decimal("50000"))
    from commerce.models import CommerceAISettings
    settings_obj = CommerceAISettings.objects.first() or CommerceAISettings.objects.create()
    target_days = request.GET.get("target_days", settings_obj.default_target_days)
    plan = build_reorder_plan(
        user=request.user,
        budget=budget,
        target_stock_days=target_days,
    )

    created_orders = []
    supplier_groups = plan.get("supplier_groups", {})

    for group in supplier_groups.values():
        supplier_id = group.get("supplier_id")
        if not supplier_id:
            continue

        items = [i for i in group.get("items", []) if i.get("qty", 0) > 0]
        if not items:
            continue

        order = Order.objects.create(
            owner=request.user,
            party_id=supplier_id,
            order_type="PURCHASE",
            status="pending",
            notes="AI reorder planner auto-generated PO",
        )

        for item in items:
            product = Product.objects.filter(sku=item.get("sku")).first()
            if not product:
                product = Product.objects.filter(name=item.get("product")).first()
            if not product:
                continue

            OrderItem.objects.create(
                order=order,
                product=product,
                qty=item.get("qty", 0),
                price=item.get("unit_cost", 0),
            )

        created_orders.append(order.id)

    return JsonResponse(
        {
            "success": True,
            "created_orders": created_orders,
            "message": "Purchase orders created" if created_orders else "No purchase orders created",
        }
    )
