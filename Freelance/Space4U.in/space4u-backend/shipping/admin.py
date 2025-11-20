from django.contrib import admin
from .models import Warehouse, Waybill, Shipment, ShipmentTracking


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'pin', 'is_active', 'created_at')
    list_filter = ('is_active', 'country', 'city')
    search_fields = ('name', 'city', 'pin')


@admin.register(Waybill)
class WaybillAdmin(admin.ModelAdmin):
    list_display = ('number', 'is_used', 'created_at')
    list_filter = ('is_used',)
    search_fields = ('number',)


class ShipmentTrackingInline(admin.TabularInline):
    model = ShipmentTracking
    extra = 0
    readonly_fields = ('status', 'status_type', 'location', 'scan_date_time', 'instructions', 'created_at')
    can_delete = False


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ('order', 'waybill', 'status', 'payment_mode', 'shipping_mode', 'expected_delivery_date', 'created_at')
    list_filter = ('status', 'payment_mode', 'shipping_mode', 'pickup_location')
    search_fields = ('order__id', 'waybill__number')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ShipmentTrackingInline]


@admin.register(ShipmentTracking)
class ShipmentTrackingAdmin(admin.ModelAdmin):
    list_display = ('shipment', 'status', 'status_type', 'location', 'scan_date_time')
    list_filter = ('status_type', 'scan_date_time')
    search_fields = ('shipment__order__id', 'status', 'location')
    readonly_fields = ('created_at',)

