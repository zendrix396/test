import secrets
import string

from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, Q


class GiftWrapSetting(models.Model):
    is_enabled = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Gift Wrap Setting"
        verbose_name_plural = "Gift Wrap Settings"

    def __str__(self):
        amount = f"₹{self.price}" if self.price is not None else "₹0"
        return f"Gift wrap {'enabled' if self.is_enabled else 'disabled'} ({amount})"


class Coupon(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', 'Percentage'
        FIXED_AMOUNT = 'FIXED_AMOUNT', 'Fixed Amount'

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    value = models.DecimalField(max_digits=10, decimal_places=2, help_text="The discount value, either as a percentage or a fixed amount.")
    
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    usage_limit = models.PositiveIntegerField(default=1, help_text="Total number of times this coupon can be used.")
    limit_per_user = models.PositiveIntegerField(default=1, help_text="How many times a single user can use this coupon.")
    
    times_used = models.PositiveIntegerField(default=0, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

class UserCouponUsage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coupon_usages")
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="user_usages")
    times_used = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'coupon')

    def __str__(self):
        return f"{self.user} used {self.coupon.code} {self.times_used} time(s)"


class WishlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="wishlisted_by",
    )  # DEPRECATED
    variant = models.ForeignKey(
        "products.ProductVariant",
        on_delete=models.CASCADE,
        related_name="wishlisted_by",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(user__isnull=False) | Q(session_key__isnull=False),
                name="wishlist_user_or_session",
            ),
            models.UniqueConstraint(
                fields=["user", "variant"],
                condition=Q(user__isnull=False),
                name="wishlist_unique_user_variant",
            ),
            models.UniqueConstraint(
                fields=["session_key", "variant"],
                condition=Q(session_key__isnull=False),
                name="wishlist_unique_session_variant",
            ),
        ]

    def __str__(self):
        owner = self.user_id or self.session_key or "guest"
        return f"wishlist:{owner} -> Variant: {self.variant_id}"


class SavedForLaterItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_for_later_items")
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.CASCADE, related_name="saved_for_later_by", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "variant")

    def __str__(self):
        return f"SaveForLater(user={self.user_id}, variant={self.variant_id})"


class RecentlyViewedItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="recently_viewed_items",
        null=True,
        blank=True
    )
    session_key = models.CharField(max_length=64, blank=True, null=True, help_text="Session key for anonymous users")
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.CASCADE, related_name="recently_viewed_by")
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "variant"), ("session_key", "variant")]
        ordering = ["-viewed_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(user__isnull=False) | Q(session_key__isnull=False),
                name="recently_viewed_user_or_session",
            )
        ]

    def __str__(self):
        identifier = self.user_id or self.session_key or "unknown"
        return f"RecentlyViewed({identifier}, variant={self.variant_id})"


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    applied_coupon = models.ForeignKey(
        "commerce.Coupon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
    )
    coupon_discount_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    gift_wrap = models.BooleanField(default=False)
    gift_wrap_amount = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(user__isnull=False) | Q(session_key__isnull=False),
                name="cart_user_or_session",
            )
        ]

    def __str__(self):
        identifier = self.user_id or self.session_key or "guest"
        return f"Cart({identifier})"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, null=True, blank=True) # DEPRECATED
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "variant")

    def __str__(self):
        return f"CartItem(cart={self.cart_id}, variant={self.variant_id}, qty={self.quantity})"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"
        PROCESSING = "PROCESSING", "Processing"
        PAID = "PAID", "Paid"
        SHIPPED = "SHIPPED", "Shipped"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    class PaymentMethod(models.TextChoices):
        RAZORPAY = "RAZORPAY", "Razorpay"
        COD = "COD", "Cash on Delivery"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"

    class Source(models.TextChoices):
        ONLINE = "ONLINE", "Online"
        OFFLINE = "OFFLINE", "Offline / Point of Sale"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=64, blank=True, null=True)
    order_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Unique order number in format ORD-XXXX-XXXX (auto-generated)"
    )
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING_PAYMENT)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    order_source = models.CharField(max_length=20, choices=Source.choices, default=Source.ONLINE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders_created",
        help_text="Staff user that created this order manually."
    )
    
    # Coupon related fields
    applied_coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    wallet_applied_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="INR")
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.RAZORPAY)
    razorpay_order_id = models.CharField(max_length=128, blank=True)
    razorpay_payment_id = models.CharField(max_length=128, blank=True)
    razorpay_signature = models.CharField(max_length=256, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipping_label_required = models.BooleanField(
        default=True,
        help_text="Uncheck to skip automatic shipment creation (useful for offline pickup orders)."
    )
    offline_reference = models.CharField(
        max_length=128,
        blank=True,
        help_text="Reference number for offline invoices or POS systems."
    )
    management_notes = models.TextField(blank=True)

    # Shipping info
    full_name = models.CharField(max_length=255)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="India")
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    gift_wrap = models.BooleanField(default=False)
    gift_wrap_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))

    # Shipping partner details
    shipping_id = models.CharField(max_length=128, blank=True)
    courier_name = models.CharField(max_length=128, blank=True)
    tracking_number = models.CharField(max_length=128, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def subtotal(self):
        return self.items.aggregate(total=Sum('line_total'))['total'] or Decimal("0.00")

    def recalculate_totals(self, *, save=False):
        subtotal = self.subtotal
        adjustments = Decimal("0.00")
        if self.gift_wrap_amount:
            adjustments += self.gift_wrap_amount
        if self.discount_amount:
            adjustments -= self.discount_amount
        if self.wallet_applied_amount:
            adjustments -= self.wallet_applied_amount
        total = subtotal + adjustments
        if total < Decimal("0.00"):
            total = Decimal("0.00")
        total = total.quantize(Decimal("0.01"))
        if self.total_cost != total:
            self.total_cost = total
            if save:
                self.save(update_fields=["total_cost"])
        return self.total_cost

    def generate_order_number(self):
        """Generate a secure order number in format ORD-XXXX-XXXX"""
        if self.order_number:
            return self.order_number
        
        # Generate 8 random alphanumeric characters (4-4 format)
        chars = string.ascii_uppercase + string.digits
        part1 = ''.join(secrets.choice(chars) for _ in range(4))
        part2 = ''.join(secrets.choice(chars) for _ in range(4))
        order_num = f"ORD-{part1}-{part2}"
        
        # Ensure uniqueness
        while Order.objects.filter(order_number=order_num).exists():
            part1 = ''.join(secrets.choice(chars) for _ in range(4))
            part2 = ''.join(secrets.choice(chars) for _ in range(4))
            order_num = f"ORD-{part1}-{part2}"
        
        return order_num

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if self.order_source == self.Source.OFFLINE:
            if not self.payment_method or self.payment_method == self.PaymentMethod.RAZORPAY:
                self.payment_method = self.PaymentMethod.COD
        # Generate order number if it doesn't exist
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order({self.id}) [{self.get_order_source_display()}] for user {self.user_id or 'guest'}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, null=True, blank=True) # DEPRECATED
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        if self.unit_price is None:
            price_candidate = Decimal("0.00")
            if self.variant and (self.variant.discount_price or self.variant.price):
                price_candidate = self.variant.discount_price or self.variant.price or Decimal("0.00")
            elif self.product and (self.product.discount_price or self.product.price):
                price_candidate = self.product.discount_price or self.product.price or Decimal("0.00")
            self.unit_price = price_candidate
        self.unit_price = Decimal(str(self.unit_price))
        self.quantity = int(self.quantity or 0)
        self.line_total = (self.unit_price * Decimal(str(self.quantity))).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)
        if self.order_id:
            self.order.recalculate_totals(save=True)

    def delete(self, *args, **kwargs):
        order = self.order
        order_id = order.id if order else None
        super().delete(*args, **kwargs)
        if order_id:
            order.recalculate_totals(save=True)

    def __str__(self):
        return f"OrderItem(order={self.order_id}, variant={self.variant_id}, qty={self.quantity})"


# Create your models here.
class ReturnRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        PROCESSED = 'PROCESSED', 'Processed'

    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name="return_request")
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Return request for {self.order_item_id} with status {self.status}"

class Refund(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'

    return_request = models.OneToOneField(ReturnRequest, on_delete=models.CASCADE, related_name="refund")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=255, blank=True, help_text="Transaction ID from the payment gateway")
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Refund for {self.return_request_id} of amount {self.amount}"


class RefundConfig(models.Model):
    enabled = models.BooleanField(default=True)
    cancelled_before_shipment_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("100.00"))
    returned_after_shipment_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("100.00"))

    def __str__(self):
        return f"RefundConfig(enabled={self.enabled})"


class OrderRefund(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="refunds")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=255, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OrderRefund(order={self.order_id}, amount={self.amount}, status={self.status})"


def generate_giftcard_code(length: int = 12) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class GiftCard(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        REDEEMED = "REDEEMED", "Redeemed"
        EXPIRED = "EXPIRED", "Expired"
        DISABLED = "DISABLED", "Disabled"

    code = models.CharField(max_length=20, unique=True, db_index=True)
    purchaser = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="giftcards_purchased",
    )
    redeemed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="giftcards_redeemed",
    )
    initial_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="INR")
    recipient_email = models.EmailField(blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    expires_at = models.DateTimeField(null=True, blank=True)
    redeemed_at = models.DateTimeField(null=True, blank=True)

    shipping_label_required = models.BooleanField(
        default=False,
        help_text="Placeholder for parity with order fulfilment; gift cards do not require shipping."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Gift Card"
        verbose_name_plural = "Gift Cards"

    def __str__(self):
        return f"GiftCard({self.code})"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new and (self.balance is None or self.balance == Decimal("0.00")):
            self.balance = self.initial_value
        if not self.code:
            for _ in range(10):
                candidate = generate_giftcard_code()
                if not GiftCard.objects.filter(code=candidate).exists():
                    self.code = candidate
                    break
        if self.expires_at and self.expires_at <= timezone.now():
            self.status = self.Status.EXPIRED
        super().save(*args, **kwargs)
        if is_new:
            GiftCardTransaction.objects.create(
                gift_card=self,
                user=self.purchaser,
                change_amount=self.initial_value,
                transaction_type=GiftCardTransaction.TransactionType.ISSUE,
                notes="Gift card issued",
            )

    @property
    def is_active(self) -> bool:
        if self.status != self.Status.ACTIVE:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return self.balance > Decimal("0.00")

    def redeem_to_wallet(self, user, *, note: str = "") -> Decimal:
        from users.models import WalletTransaction

        if not user or not user.is_authenticated:
            raise ValueError("Authenticated user required to redeem a gift card.")

        with transaction.atomic():
            giftcard = GiftCard.objects.select_for_update().get(pk=self.pk)
            if not giftcard.is_active:
                raise ValueError("Gift card is not active or has already been redeemed.")
            redeem_amount = giftcard.balance
            if redeem_amount <= Decimal("0.00"):
                raise ValueError("Gift card has zero balance.")

            giftcard.balance = Decimal("0.00")
            giftcard.status = GiftCard.Status.REDEEMED
            giftcard.redeemed_by = user
            giftcard.redeemed_at = timezone.now()
            giftcard.save(
                update_fields=["balance", "status", "redeemed_by", "redeemed_at", "updated_at"]
            )

            GiftCardTransaction.objects.create(
                gift_card=giftcard,
                user=user,
                change_amount=-redeem_amount,
                transaction_type=GiftCardTransaction.TransactionType.REDEEM,
                notes=note or "Wallet credit via gift card redemption",
            )

            user.wallet_balance = (user.wallet_balance or Decimal("0.00")) + redeem_amount
            user.save(update_fields=["wallet_balance"])

            WalletTransaction.objects.create(
                user=user,
                amount=redeem_amount,
                kind=WalletTransaction.Kind.CREDIT,
                reference=f"giftcard:{giftcard.code}",
            )

            return redeem_amount


class GiftCardTransaction(models.Model):
    class TransactionType(models.TextChoices):
        ISSUE = "ISSUE", "Issued"
        REDEEM = "REDEEM", "Redeemed"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    gift_card = models.ForeignKey(GiftCard, on_delete=models.CASCADE, related_name="transactions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="giftcard_transactions",
    )
    change_amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Gift Card Transaction"
        verbose_name_plural = "Gift Card Transactions"

    def save(self, *args, **kwargs):
        if self.gift_card:
            self.balance_after = self.gift_card.balance
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type} {self.change_amount} on {self.gift_card.code}"


class CurrencyExchangeRate(models.Model):
    """
    Model to store exchange rates for different currencies relative to base currency (INR).
    """
    currency_code = models.CharField(max_length=3, unique=True, help_text="ISO 4217 currency code (e.g., USD, EUR)")
    rate_to_inr = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        help_text="Exchange rate: 1 unit of this currency = this many INR"
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['currency_code']
        verbose_name = "Currency Exchange Rate"
        verbose_name_plural = "Currency Exchange Rates"

    def __str__(self):
        return f"{self.currency_code}: {self.rate_to_inr} INR"
