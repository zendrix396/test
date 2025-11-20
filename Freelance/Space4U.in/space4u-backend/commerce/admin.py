from django.contrib import admin
from .models import (
    WishlistItem,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Coupon,
    UserCouponUsage,
    ReturnRequest,
    Refund,
    RefundConfig,
    OrderRefund,
    SavedForLaterItem,
    RecentlyViewedItem,
    GiftWrapSetting,
    GiftCard,
    GiftCardTransaction,
    CurrencyExchangeRate,
)
from django.utils import timezone
from .services import process_order_success, ship_order, cancel_order
from users.models import LoyaltyConfig, LoyaltyTransaction, Badge, UserBadge
from decimal import Decimal
from django.http import HttpResponse
from commerce.services import generate_invoice_pdf
import zipfile
from io import BytesIO

# Action function to generate invoices
def admin_generate_invoices(modeladmin, request, queryset):
    """
    Admin action to generate PDF invoices for selected orders.
    - If one order is selected, returns a single PDF.
    - If multiple orders are selected, returns a ZIP file with all PDFs.
    """
    if len(queryset) == 1:
        # Single order download
        order = queryset[0]
        try:
            pdf_content = generate_invoice_pdf(order)
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
            return response
        except Exception as e:
            modeladmin.message_user(request, f"Error generating invoice for order {order.id}: {e}", level='error')
            return
    else:
        # Multiple orders download as ZIP
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for order in queryset:
                try:
                    pdf_content = generate_invoice_pdf(order)
                    zip_file.writestr(f"invoice_{order.id}.pdf", pdf_content)
                except Exception as e:
                    modeladmin.message_user(request, f"Error generating invoice for order {order.id}: {e}", level='warning')

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="invoices.zip"'
        return response

admin_generate_invoices.short_description = "Generate Invoice(s)"


class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "value", "is_active", "valid_from", "valid_to", "usage_limit", "times_used")
    list_filter = ("is_active", "discount_type")
    search_fields = ("code",)

class UserCouponUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "coupon", "times_used")
    search_fields = ("user__username", "coupon__code")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ('variant', 'quantity', 'unit_price', 'line_total')
    extra = 0
    show_change_link = True

    def get_readonly_fields(self, request, obj=None):
        if obj is None or (obj and obj.order_source == Order.Source.OFFLINE):
            return ('line_total',)
        return ('variant', 'quantity', 'unit_price', 'line_total')

    def get_extra(self, request, obj=None, **kwargs):
        if obj is None or (obj and obj.order_source == Order.Source.OFFLINE):
            return 1
        return 0

    def has_add_permission(self, request, obj=None):
        if obj is None:
            return True
        return obj.order_source == Order.Source.OFFLINE

    def has_change_permission(self, request, obj=None):
        if obj and obj.order_source != Order.Source.OFFLINE:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.order_source != Order.Source.OFFLINE:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order_number',
        'user',
        'session_key',
        'order_source',
        'created_by',
        'status',
        'payment_method',
        'shipping_label_required',
        'total_cost',
        'created_at',
    )
    list_filter = ('status', 'payment_method', 'order_source', 'shipping_label_required')
    search_fields = ('user__username', 'id', 'order_number', 'offline_reference', 'courier_name', 'tracking_number')
    readonly_fields = ()
    inlines = [OrderItemInline]
    fieldsets = (
        ("Order Source & Assignment", {
            "fields": (
                'order_source',
                'user',
                'created_by',
                'status',
                'payment_method',
                'currency',
                'shipping_label_required',
                'offline_reference',
                'management_notes',
                'paid_at',
            )
        }),
        ("Financials & Adjustments", {
            "fields": (
                'total_cost',
                'discount_amount',
                'wallet_applied_amount',
                'gift_wrap',
                'gift_wrap_amount',
                'applied_coupon',
            )
        }),
        ("Customer Contact", {
            "fields": ('full_name', 'email', 'phone')
        }),
        ("Shipping Address & Tracking", {
            "fields": (
                'address_line1',
                'address_line2',
                'city',
                'state',
                'postal_code',
                'country',
                'shipping_id',
                'courier_name',
                'tracking_number',
            )
        }),
        ("Session & Gateway Metadata", {
            "classes": ('collapse',),
            "fields": (
                'session_key',
                'razorpay_order_id',
                'razorpay_payment_id',
                'razorpay_signature',
                'created_at',
                'updated_at',
            )
        }),
    )
    autocomplete_fields = ('user', 'applied_coupon')
    date_hierarchy = 'created_at'
    actions = [admin_generate_invoices]

    base_readonly_fields = (
        'created_by',
        'total_cost',
        'razorpay_order_id',
        'razorpay_payment_id',
        'razorpay_signature',
        'created_at',
        'updated_at',
    )
    online_only_readonly = ('user', 'session_key')

    def get_changeform_initial_data(self, request):
        data = super().get_changeform_initial_data(request)
        data.setdefault('order_source', Order.Source.OFFLINE)
        data.setdefault('payment_method', Order.PaymentMethod.COD)
        data.setdefault('shipping_label_required', False)
        return data

    def get_readonly_fields(self, request, obj=None):
        fields = list(self.base_readonly_fields)
        if obj and obj.order_source != Order.Source.OFFLINE:
            fields.extend(self.online_only_readonly)
        return fields

    def save_model(self, request, obj, form, change):
        print(f"[ADMIN] OrderAdmin.save_model called for order {obj.id}, change={change}, status={obj.status}")
        original_status = None
        if change and obj.pk:
            try:
                original_status = Order.objects.get(pk=obj.pk).status
                print(f"[ADMIN] Original status: {original_status}, new status: {obj.status}")
            except Order.DoesNotExist:
                print(f"[ADMIN] Order {obj.pk} does not exist (should not happen)")
                pass
            
            # Process order if status changes to PROCESSING (reserve stock)
            if obj.status == Order.Status.PROCESSING and original_status != Order.Status.PROCESSING:
                print(f"[ADMIN] Calling process_order_success for order {obj.id}")
                process_order_success(obj)
            
            # Ship: remove reservations and decrement stock when status moves to SHIPPED
            if obj.status == Order.Status.SHIPPED and original_status and original_status != Order.Status.SHIPPED:
                print(f"[ADMIN] Calling ship_order for order {obj.id}")
                ship_order(obj)
            
            # Send personalized email for ALL status changes (except when order is first created)
            # This ensures users get notified of every status update with personalized messages
            if original_status and original_status != obj.status:
                try:
                    from users.services import send_shipping_update_email
                    send_shipping_update_email(obj)
                except Exception as e:
                    print(f"Failed to send status update email for order {obj.id}: {e}")

            # Award loyalty points if status changes to COMPLETED
            if obj.status == Order.Status.COMPLETED and original_status and original_status != Order.Status.COMPLETED:
                self.award_loyalty_points(obj)

            # If moving away from COMPLETED, revoke previously awarded points
            if original_status == Order.Status.COMPLETED and obj.status != Order.Status.COMPLETED:
                self.revoke_loyalty_points(obj)

            # If cancelled before shipment, release reservations and create refund as applicable
            if obj.status == Order.Status.CANCELLED and original_status != Order.Status.CANCELLED:
                # Do not attempt to reverse shipped stock here
                if original_status in (Order.Status.PROCESSING, Order.Status.PAID, Order.Status.PENDING_PAYMENT):
                    cancel_order(obj)
                # Email will be sent by the status change handler below

        if not change and request.user.is_authenticated:
            if not obj.created_by and request.user.is_staff:
                obj.created_by = request.user

        super().save_model(request, obj, form, change)
        obj.recalculate_totals(save=True)

    def award_loyalty_points(self, order):
        if not order.user:
            return
        try:
            config = LoyaltyConfig.objects.get(enabled=True)
            if not config:
                return
        except LoyaltyConfig.DoesNotExist:
            return

        paid_amount = order.total_cost - order.wallet_applied_amount
        if paid_amount <= 0:
            return

        # Idempotency: do not award twice for the same order
        existing = LoyaltyTransaction.objects.filter(user=order.user, reason__icontains=f"order #{order.id}", points__gt=0).exists()
        if existing:
            return

        points_to_award = int(paid_amount * Decimal(str(config.points_per_currency)))

        if points_to_award > 0:
            user = order.user
            user.loyalty_points += points_to_award
            user.save(update_fields=["loyalty_points"])

            LoyaltyTransaction.objects.create(
                user=user,
                points=points_to_award,
                reason=f"Points awarded for order #{order.id}"
            )

            # Update tier based on new total and award badge if tier changes
            old_tier = user.loyalty_tier
            if user.loyalty_points >= 2000:
                user.loyalty_tier = 'MEGAFAN'
            elif user.loyalty_points >= 500:
                user.loyalty_tier = 'SUPERFAN'
            else:
                user.loyalty_tier = 'FAN'
            if user.loyalty_tier != old_tier:
                user.save(update_fields=["loyalty_tier"])
                badge_name = f"{user.loyalty_tier.title()}"
                badge, _ = Badge.objects.get_or_create(name=badge_name, defaults={"description": f"Reached {badge_name}"})
                UserBadge.objects.get_or_create(user=user, badge=badge)
                # Send loyalty tier update email
                try:
                    from users.services import send_loyalty_tier_update_email
                    send_loyalty_tier_update_email(user, old_tier, user.loyalty_tier)
                except Exception as e:
                    print(f"Failed to send loyalty tier email to {user.email}: {e}")

    def revoke_loyalty_points(self, order):
        if not order.user:
            return
        # Find any loyalty transactions we created for this order and roll them back
        from users.models import LoyaltyTransaction
        txns = LoyaltyTransaction.objects.filter(user=order.user, reason__icontains=f"order #{order.id}")
        total_awarded = sum(t.points for t in txns if t.points > 0)
        if total_awarded > 0:
            user = order.user
            user.loyalty_points = max(user.loyalty_points - total_awarded, 0)
            user.save(update_fields=["loyalty_points"])
            LoyaltyTransaction.objects.create(
                user=user,
                points=-total_awarded,
                reason=f"Reversal for order #{order.id}"
            )
            # Recompute tier
            old_tier = user.loyalty_tier
            if user.loyalty_points >= 2000:
                user.loyalty_tier = 'MEGAFAN'
            elif user.loyalty_points >= 500:
                user.loyalty_tier = 'SUPERFAN'
            else:
                user.loyalty_tier = 'FAN'
            if user.loyalty_tier != old_tier:
                user.save(update_fields=["loyalty_tier"])
                # Send loyalty tier update email
                try:
                    from users.services import send_loyalty_tier_update_email
                    send_loyalty_tier_update_email(user, old_tier, user.loyalty_tier)
                except Exception as e:
                    print(f"Failed to send loyalty tier email to {user.email}: {e}")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('get_product',)
    fields = ('get_product', 'variant', 'quantity')

    def get_product(self, obj):
        if obj.variant:
            return obj.variant.product
        return "—"
    get_product.short_description = 'Product'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_key', 'total_items_display', 'gift_wrap', 'updated_at')
    search_fields = ('session_key', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CartItemInline]

    def total_items_display(self, obj):
        return obj.total_items

    total_items_display.short_description = "Items"


admin.site.register(WishlistItem)
admin.site.register(SavedForLaterItem)
admin.site.register(RecentlyViewedItem)
admin.site.register(OrderItem)
admin.site.register(Coupon, CouponAdmin)
admin.site.register(UserCouponUsage, UserCouponUsageAdmin)
admin.site.register(RefundConfig)
admin.site.register(OrderRefund)
admin.site.register(GiftWrapSetting)


@admin.register(CurrencyExchangeRate)
class CurrencyExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('currency_code', 'rate_to_inr', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('currency_code',)
    list_editable = ('is_active',)


class GiftCardTransactionInline(admin.TabularInline):
    model = GiftCardTransaction
    extra = 0
    readonly_fields = ('transaction_type', 'change_amount', 'balance_after', 'user', 'notes', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(GiftCard)
class GiftCardAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'status',
        'initial_value',
        'balance',
        'currency',
        'purchaser',
        'redeemed_by',
        'expires_at',
        'redeemed_at',
        'created_at',
    )
    list_filter = ('status', 'currency', 'expires_at')
    search_fields = ('code', 'purchaser__username', 'redeemed_by__username', 'recipient_email')
    readonly_fields = ('balance', 'status', 'redeemed_by', 'redeemed_at', 'created_at', 'updated_at')
    inlines = [GiftCardTransactionInline]

    fieldsets = (
        ('Gift Card Details', {
            'fields': ('code', 'status', 'initial_value', 'balance', 'currency', 'expires_at')
        }),
        ('Participants', {
            'fields': ('purchaser', 'recipient_email', 'redeemed_by', 'redeemed_at')
        }),
        ('Messaging', {
            'fields': ('message',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is None:
            readonly.append('code')
        return readonly


@admin.register(GiftCardTransaction)
class GiftCardTransactionAdmin(admin.ModelAdmin):
    list_display = ('gift_card', 'transaction_type', 'change_amount', 'balance_after', 'user', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('gift_card__code', 'user__username', 'notes')
    readonly_fields = ('gift_card', 'transaction_type', 'change_amount', 'balance_after', 'user', 'notes', 'created_at')

    def has_add_permission(self, request):
        return False


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ("order_item", "status", "requested_at")

    def save_model(self, request, obj, form, change):
        original_status = None
        if obj.pk:
            original_status = type(obj).objects.get(pk=obj.pk).status
        super().save_model(request, obj, form, change)
        if original_status != obj.status and obj.status == obj.Status.PROCESSED:
            # Create refund based on config
            from .models import Refund, RefundConfig
            cfg = RefundConfig.objects.first()
            if cfg and cfg.enabled:
                percent = cfg.returned_after_shipment_percent
                order = obj.order_item.order
                base_amount = order.total_cost - order.wallet_applied_amount
                if base_amount > 0:
                    amount = (base_amount * (Decimal(str(percent)) / Decimal("100"))).quantize(Decimal("0.01"))
                    Refund.objects.create(return_request=obj, amount=amount)
