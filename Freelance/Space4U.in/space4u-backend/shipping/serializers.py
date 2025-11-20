from rest_framework import serializers
from .models import Shipment, ShipmentTracking, Warehouse, Waybill


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = [
            'id', 'name', 'registered_name', 'email', 'phone',
            'address', 'city', 'pin', 'country',
            'return_address', 'return_pin', 'return_city',
            'return_state', 'return_country', 'is_active',
            'created_at', 'updated_at'
        ]


class WaybillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Waybill
        fields = ['id', 'number', 'is_used', 'created_at']


class ShipmentTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentTracking
        fields = [
            'id', 'status', 'status_type', 'location',
            'scan_date_time', 'instructions', 'created_at'
        ]


class ShipmentSerializer(serializers.ModelSerializer):
    waybill = WaybillSerializer(read_only=True)
    pickup_location = WarehouseSerializer(read_only=True)
    tracking_history = ShipmentTrackingSerializer(many=True, read_only=True)

    class Meta:
        model = Shipment
        fields = [
            'id', 'waybill', 'payment_mode', 'shipping_mode',
            'total_amount', 'cod_amount', 'pickup_location',
            'status', 'expected_delivery_date', 'created_at',
            'updated_at', 'tracking_history'
        ]

