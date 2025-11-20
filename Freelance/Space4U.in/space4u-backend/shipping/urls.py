from django.urls import path
from . import views

app_name = "shipping"

urlpatterns = [
    path('pincode-serviceability/', views.check_pincode_serviceability, name='check_pincode_serviceability'),
    path('fetch-bulk-waybills/', views.fetch_bulk_waybills, name='fetch_bulk_waybills'),
    path('create-shipment/', views.create_shipment_view, name='create_shipment'),
    path('update-shipment/', views.update_shipment, name='update_shipment'),
    path('cancel-shipment/', views.cancel_shipment, name='cancel_shipment'),
    path('track-shipment/', views.track_shipment, name='track_shipment'),
    path('order-tracking/<int:order_id>/', views.get_order_tracking, name='get_order_tracking'),
    path('generate-shipping-label/', views.generate_shipping_label, name='generate_shipping_label'),
    path('create-pickup-request/', views.create_pickup_request, name='create_pickup_request'),
    path('create-warehouse/', views.create_warehouse, name='create_warehouse'),
    path('webhook/delhivery/', views.delhivery_webhook, name='delhivery_webhook'),
    path('webhook/shiprocket/', views.shiprocket_webhook, name='shiprocket_webhook'),
]

