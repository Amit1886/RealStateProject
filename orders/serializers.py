from rest_framework import serializers

from .models import Order, OrderItem, OrderReturn, POSBill


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = "__all__"


class POSBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = POSBill
        fields = "__all__"


class OrderReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReturn
        fields = "__all__"
