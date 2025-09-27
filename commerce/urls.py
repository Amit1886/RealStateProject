from django.urls import path
from . import views

app_name = "commerce"

urlpatterns = [
    # ------------------- Dashboard -------------------
    path("dashboard/", views.dashboard, name="User_dashboard"),

    # ------------------- Products -------------------
    path("products/", views.product_list, name="product_list"),
    path("products/new/", views.product_create, name="product_create"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),

    # ------------------- Warehouses -------------------
    path("warehouses/", views.warehouse_list, name="warehouse_list"),
    path("warehouses/new/", views.warehouse_create, name="warehouse_create"),
    path("warehouses/<int:pk>/edit/", views.warehouse_edit, name="warehouse_edit"),
    path("warehouses/<int:pk>/delete/", views.warehouse_delete, name="warehouse_delete"),

    # ------------------- Orders -------------------
    path("orders/", views.order_list, name="order_list"),
    path("orders/new/", views.order_create_user, name="order_create_user"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/accept/", views.order_accept, name="order_accept"),
    path("orders/<int:pk>/reject/", views.order_reject, name="order_reject"),

    # ------------------- Parties -------------------
    path("party/add/", views.add_party, name="add_party"),
    path("party/", views.party_list, name="party_list"),

    # ------------------- Transactions / Invoices -------------------
    path("transaction/add/", views.add_transaction, name="add_transaction"),
    path("transaction/", views.transaction_list, name="transaction_list"),

    # ------------------- Chat -------------------
    path("chat/<int:thread_id>/", views.chat_room, name="chat_room"),
    path("api/chat/<int:thread_id>/messages/", views.api_chat_messages, name="api_chat_messages"),
    path("api/chat/<int:thread_id>/send/", views.api_chat_send, name="api_chat_send"),

    # ------------------- Party Portal (Token Protected) -------------------
    path("portal/<str:token>/", views.portal_home, name="portal_home"),
    path("portal/<str:token>/products/", views.portal_products, name="portal_products"),
    path("portal/<str:token>/order/new/", views.portal_place_order, name="portal_place_order"),
    path("portal/<str:token>/chat/", views.portal_chat_room, name="portal_chat_room"),
    path("portal/<str:token>/api/messages/", views.portal_api_messages, name="portal_api_messages"),
    path("portal/<str:token>/api/send/", views.portal_api_send, name="portal_api_send"),


]
