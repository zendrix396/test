from django.db import models
from django.conf import settings


class Warehouse(models.Model):
    name = models.CharField(max_length=255, unique=True)
    registered_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    pin = models.CharField(max_length=10)
    country = models.CharField(max_length=50, default='India')
    return_address = models.TextField()
    return_pin = models.CharField(max_length=10)
    return_city = models.CharField(max_length=100)
    return_state = models.CharField(max_length=100)
    return_country = models.CharField(max_length=50, default='India')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Warehouse"
        verbose_name_plural = "Warehouses"


class Waybill(models.Model):
    number = models.CharField(max_length=50, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.number

    class Meta:
        verbose_name = "Waybill"
        verbose_name_plural = "Waybills"


class Shipment(models.Model):
    PAYMENT_MODE_CHOICES = (
        ('Prepaid', 'Prepaid'),
        ('COD', 'Cash on Delivery'),
        ('Pickup', 'Pickup'),
        ('REPL', 'Replacement'),
    )

    SHIPPING_MODE_CHOICES = (
        ('Surface', 'Surface'),
        ('Express', 'Express'),
    )

    order = models.OneToOneField(
        'commerce.Order',
        on_delete=models.CASCADE,
        related_name='shipment'
    )
    waybill = models.OneToOneField(
        Waybill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES)
    shipping_mode = models.CharField(
        max_length=20,
        choices=SHIPPING_MODE_CHOICES,
        default='Surface'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    cod_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    pickup_location = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='shipments'
    )
    status = models.CharField(max_length=100, default='Manifested')
    expected_delivery_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Shipment for Order {self.order.id}"

    class Meta:
        verbose_name = "Shipment"
        verbose_name_plural = "Shipments"


class ShipmentTracking(models.Model):
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name='tracking_history'
    )
    status = models.CharField(max_length=255)
    status_type = models.CharField(max_length=50)
    location = models.CharField(max_length=255, blank=True)
    scan_date_time = models.DateTimeField()
    instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        waybill = self.shipment.waybill.number if self.shipment.waybill else "No waybill"
        return f"{waybill} - {self.status}"

    class Meta:
        verbose_name = "Shipment Tracking"
        verbose_name_plural = "Shipment Tracking"
        ordering = ['-scan_date_time']

