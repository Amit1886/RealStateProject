from rest_framework import serializers

from .models import GSTDetail, Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = "__all__"


class GSTDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = GSTDetail
        fields = "__all__"


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    gst_detail = GSTDetailSerializer(read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"
