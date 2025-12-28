from django.urls import path
from . import views

app_name = "khataapp"

urlpatterns = [
    path("party/add/", views.add_party, name="add_party"),
    path("party/list/", views.party_list, name="party_list"),
    path('party/view/<int:party_id>/', views.party_view, name='party_view'),
    path("party/edit/<int:party_id>/", views.edit_party, name="edit_party"),
    path("party/delete/<int:party_id>/", views.delete_party, name="delete_party"),
    path("credit-report/", views.credit_report_view, name="credit_report"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/update-plan/", views.update_plan, name="update_plan"),
    path("my-credits/", views.my_credits, name="my_credits"),
    path("transaction/add/", views.add_transaction, name="add_transaction"),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/edit/<int:id>/',views.transaction_edit,name='transaction_edit'),
    path('transactions/view/<int:id>/', views.transaction_view, name='transaction_view'),
    path("transactions/delete/<int:id>/",views.transaction_delete,name="transaction_delete"),
]
