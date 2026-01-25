from django.urls import path
from . import views
from .views import (
    sales_voucher_detail,
     )



app_name = "commerce"

urlpatterns = [
    # ------------------- Dashboard -------------------
    path("dashboard/", views.user_commerce_dashboard, name="User_dashboard"),
    path("user-dashboard/", views.user_commerce_dashboard, name="user_commerce_dashboard"),


    # ------------------- Products -------------------
    path("add-category/", views.add_category, name="add_category"),
    path("add-product/", views.add_product, name="add_product"),
    path("products/", views.product_list, name="product_list"),
    path("products/<int:id>/",views.product_detail,name="product_detail"),
    path("products/new/", views.product_create, name="product_create"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),

    # ---------------- PRODUCT MANAGEMENT ----------------
    path("product/add/", views.add_product, name="add_product"),
    path("add-payment/", views.add_payment, name="add_payment"),
    path("add-stock/", views.add_stock, name="add_stock"),


   # ------------------- Warehouses -------------------
    path("add-warehouse/", views.add_warehouse, name="add_warehouse"),
    path("warehouses/", views.warehouse_list, name="warehouse_list"),
    path("warehouses/new/", views.warehouse_create, name="warehouse_create"),
    path("warehouses/<int:pk>/edit/", views.warehouse_edit, name="warehouse_edit"),
    path("warehouses/<int:pk>/delete/", views.warehouse_delete, name="warehouse_delete"),

    # ------------------- Orders -------------------
    path("add-order/", views.add_order, name="add_order"),
    path("view-order/<int:order_id>/", views.view_order, name="view_order"),
    path("get-price/<int:pk>/", views.get_product_price, name="get_price"),
    path('download-invoice/<int:order_id>/', views.download_invoice, name='download_invoice'),
    path("orders/", views.order_list, name="order_list"),
    path('orders/sales/', views.sales_order_list, name='sales_order_list'),
    path('orders/purchase/', views.purchase_order_list, name='purchase_order_list'),
    path("orders/<int:order_id>/<str:action>/",views.order_action,name="order_action"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("sales/voucher/create/<int:order_id>/",views.sales_voucher_create,name="sales_voucher_create"),
    path("sales/voucher/<int:invoice_no>/", sales_voucher_detail, name="sales_voucher_detail"),
    path("invoices/add/", views.add_invoice, name="add_invoice"),

    # ------------------- Chat -------------------
    path("add-chat-thread/", views.add_chat_thread, name="add_chat_thread"),
    path("add-chat-message/", views.add_chat_message, name="add_chat_message"),
    path("chat/<int:thread_id>/", views.chat_room, name="chat_room"),
    path("api/chat/<int:thread_id>/messages/", views.api_chat_messages, name="api_chat_messages"),
    path("api/chat/<int:thread_id>/send/", views.api_chat_send, name="api_chat_send"),

    # ------------------- Coupons -------------------
    path("coupons/", views.coupon_list, name="coupon_list"),
    path("coupons/create/", views.coupon_create, name="coupon_create"),
    path("coupons/<int:pk>/edit/", views.coupon_edit, name="coupon_edit"),
    path("coupons/<int:pk>/delete/", views.coupon_delete, name="coupon_delete"),
    path("user-coupons/", views.user_coupon_list, name="user_coupon_list"),
    path("apply-coupon/", views.apply_coupon, name="apply_coupon"),
    path("spin-wheel/", views.spin_wheel, name="spin_wheel"),
    path("scratch-card/", views.scratch_card, name="scratch_card"),
    path("dashboard-with-coupons/", views.dashboard_with_coupons, name="dashboard_with_coupons"),

   ]
