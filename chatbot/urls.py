from django.urls import path
from .views import chatbot_reply, flow_list, flow_builder, flow_create, flow_save

urlpatterns = [
    path("reply/", chatbot_reply, name="chatbot_reply"),
    path("flows/", flow_list, name="chatbot_flow_list"),
    path("flows/create/", flow_create, name="chatbot_flow_create"),
    path("flows/<int:flow_id>/builder/", flow_builder, name="chatbot_flow_builder"),
    path("flows/<int:flow_id>/save/", flow_save, name="chatbot_flow_save"),
]
