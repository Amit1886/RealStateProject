from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('transactions/', views.all_transactions, name='all_transactions'),
    path('cash-book/', views.cash_book, name='cash_book'),

    path('sales/', views.sales_report, name='sales_report'),
    path('purchase/', views.purchase_report, name='purchase_report'),

    path('stock-summary/', views.stock_summary, name='stock_summary'),
    path('low-stock/', views.low_stock, name='low_stock'),

    path('party-ledger/', views.party_ledger, name='party_ledger'),
    path('outstanding/', views.outstanding, name='outstanding'),

    path('profit-loss/', views.profit_loss, name='profit_loss'),
    path('day-book/', views.day_book, name='day_book'),
]
