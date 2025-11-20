from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import (
    WishlistItem,
    SavedForLaterItem,
    Cart,
    CartItem,
    Order,
    OrderItem,
    ReturnRequest,
    GiftCard,
)
from products.serializers import ProductSerializer, ProductVariantSerializer


class WishlistItemSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)
    product = serializers.SerializerMethodField()

    class Meta:
        model = WishlistItem
        fields = ["id", "variant", "created_at", "product"]

    def get_product(self, obj):
        if not obj.variant or not obj.variant.product:
            return None
        
        product = obj.variant.product
        request = self.context.get("request")
        
        image_url = None
        if product.image and request:
            image_url = request.build_absolute_uri(product.image.url)

        return {
            "name": product.name,
            "sku": product.sku,
            "image": image_url
        }


class SavedForLaterItemSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)

    class Meta:
        model = SavedForLaterItem
        fields = ["id", "variant", "created_at"]


class CartItemSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)
    product = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "variant", "quantity", "added_at", "product", "subtotal"]

    def get_product(self, obj):
        product = obj.product or getattr(obj.variant, "product", None)
        if not product:
            return None

        request = self.context.get("request")

        primary_image = None
        if product.image and hasattr(product.image, 'url'):
            primary_image = request.build_absolute_uri(product.image.url) if request else product.image.url

        images = []
        if hasattr(product, "images"):
            for image_obj in product.images.all():
                if image_obj.image and hasattr(image_obj.image, 'url'):
                    image_value = request.build_absolute_uri(image_obj.image.url) if request else image_obj.image.url
                    images.append({"image": image_value})
        
        category = None
        if getattr(product, "category", None):
            category = {
                "name": product.category.name,
                "slug": product.category.slug,
            }

        try:
            tags = list(product.tags.values_list("name", flat=True))
        except Exception:
            tags = []

        return {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "image": primary_image,
            "images": images,
            "category": category,
            "tags": tags,
        }

    def get_subtotal(self, obj):
        from products.deal_utils import get_deal_for_product_or_variant
        from decimal import Decimal
        
        variant = obj.variant
        if not variant or not variant.product:
            return Decimal("0.00")
        
        # Get deal price if available
        try:
            deal, deal_price = get_deal_for_product_or_variant(variant.product, variant)
            if deal and deal_price:
                unit_price = Decimal(str(deal_price))
            else:
                unit_price = variant.discount_price or variant.price
        except Exception:
            # Fallback to regular price if deal calculation fails
            unit_price = variant.discount_price or variant.price
        
        return unit_price * obj.quantity


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    total_payable = serializers.SerializerMethodField()
    applied_coupon = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "session_key",
            "created_at",
            "updated_at",
            "items",
            "subtotal",
            "total_items",
            "discount_amount",
            "gift_wrap",
            "gift_wrap_amount",
            "total_payable",
            "applied_coupon",
        ]

    def _merch_total(self, obj):
        from products.deal_utils import get_deal_for_product_or_variant
        from decimal import Decimal
        
        total = Decimal("0.00")
        for item in obj.items.all():
            variant = item.variant
            if not variant:
                continue
            
            # Get deal price if available
            deal, deal_price = get_deal_for_product_or_variant(variant.product, variant)
            if deal and deal_price:
                unit_price = Decimal(str(deal_price))
            else:
                unit_price = variant.discount_price or variant.price
            total += unit_price * item.quantity
        return total

    def get_subtotal(self, obj):
        merchandise_total = self._merch_total(obj)
        gift_wrap_total = obj.gift_wrap_amount if obj.gift_wrap else Decimal("0.00")
        return merchandise_total + gift_wrap_total

    def get_total_items(self, obj):
        return obj.total_items

    def get_discount_amount(self, obj):
        return obj.coupon_discount_amount or Decimal("0.00")

    def get_total_payable(self, obj):
        subtotal = self.get_subtotal(obj)
        discount = self.get_discount_amount(obj)
        total = subtotal - discount
        return total if total > Decimal("0.00") else Decimal("0.00")

    def get_applied_coupon(self, obj):
        if not obj.applied_coupon:
            return None
        coupon = obj.applied_coupon
        return {
            "code": coupon.code,
            "discount_type": coupon.discount_type,
            "value": coupon.value,
        }


class OrderItemSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "variant", "quantity", "unit_price", "line_total"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    can_cancel = serializers.SerializerMethodField()
    cancel_disabled_reason = serializers.SerializerMethodField()
    shipment_info = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "session_key",
            "status",
            "order_source",
            "paid_at",
            "total_cost",
            "subtotal",
            "discount_amount",
            "wallet_applied_amount",
            "currency",
            "payment_method",
            "offline_reference",
            "full_name",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "phone",
            "email",
            "gift_wrap",
            "gift_wrap_amount",
            "items",
            "created_at",
            "updated_at",
            "can_cancel",
            "cancel_disabled_reason",
            "shipping_id",
            "courier_name",
            "tracking_number",
            "shipment_info",
        ]

    def get_can_cancel(self, obj):
        return obj.status in (obj.Status.PENDING_PAYMENT, obj.Status.PAID, obj.Status.PROCESSING)

    def get_cancel_disabled_reason(self, obj):
        if obj.status == obj.Status.SHIPPED:
            return "Order shipped; use return flow."
        if obj.payment_method == obj.PaymentMethod.COD and obj.status == obj.Status.SHIPPED:
            return "COD order shipped; cancellation disabled."
        if obj.status == obj.Status.CANCELLED:
            return "Order already cancelled."
        if obj.status == obj.Status.COMPLETED:
            return "Order completed; use return flow."
        return ""

    def get_shipment_info(self, obj):
        """Get shipment information if available"""
        try:
            shipment = obj.shipment
            return {
                'has_shipment': True,
                'status': shipment.status,
                'expected_delivery_date': shipment.expected_delivery_date.isoformat() if shipment.expected_delivery_date else None,
                'waybill_number': shipment.waybill.number if shipment.waybill else None,
                'shipping_mode': shipment.shipping_mode,
            }
        except:
            return {
                'has_shipment': False,
                'status': None,
                'expected_delivery_date': None,
                'waybill_number': None,
                'shipping_mode': None,
            }


class ReturnRequestSerializer(serializers.ModelSerializer):
    order_item_id = serializers.IntegerField()

    class Meta:
        model = ReturnRequest
        fields = ['id', 'order_item_id', 'reason', 'status', 'requested_at', 'resolved_at']
        read_only_fields = ['status', 'requested_at', 'resolved_at']

    def validate_order_item_id(self, value):
        user = self.context['request'].user
        try:
            order_item = OrderItem.objects.get(id=value, order__user=user)
        except OrderItem.DoesNotExist:
            raise serializers.ValidationError("This order item does not exist or does not belong to you.")
        
        if hasattr(order_item, 'return_request'):
            raise serializers.ValidationError("A return request for this item already exists.")
            
        return value

    def create(self, validated_data):
        order_item_id = validated_data.pop('order_item_id')
        order_item = OrderItem.objects.get(id=order_item_id)
        return ReturnRequest.objects.create(order_item=order_item, **validated_data)


class GiftCardSerializer(serializers.ModelSerializer):
    purchaser = serializers.StringRelatedField(read_only=True)
    redeemed_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = GiftCard
        fields = [
            'id',
            'code',
            'status',
            'initial_value',
            'balance',
            'currency',
            'purchaser',
            'redeemed_by',
            'recipient_email',
            'message',
            'expires_at',
            'redeemed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class GiftCardRedeemSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=20)

    def validate_code(self, value):
        normalized = value.strip().upper()
        if not normalized:
            raise serializers.ValidationError("Gift card code is required.")
        try:
            gift_card = GiftCard.objects.get(code=normalized)
        except GiftCard.DoesNotExist:
            raise serializers.ValidationError("Gift card not found.")
        if not gift_card.is_active:
            raise serializers.ValidationError("Gift card is inactive or already redeemed.")
        if gift_card.expires_at and gift_card.expires_at < timezone.now():
            raise serializers.ValidationError("Gift card has expired.")
        self.context['gift_card'] = gift_card
        return normalized


class GiftCardIssueSerializer(serializers.ModelSerializer):
    purchaser = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all(), required=False, allow_null=True)

    class Meta:
        model = GiftCard
        fields = [
            'initial_value',
            'currency',
            'purchaser',
            'recipient_email',
            'message',
            'expires_at',
        ]

    def create(self, validated_data):
        purchaser = validated_data.get('purchaser')
        request = self.context.get('request')
        if purchaser is None and request and getattr(request, "user", None) and request.user.is_authenticated:
            purchaser = request.user
            validated_data['purchaser'] = purchaser
        return GiftCard.objects.create(**validated_data)


