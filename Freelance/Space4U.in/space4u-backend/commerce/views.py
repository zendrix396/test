from django.db import transaction, IntegrityError
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import (
    WishlistItem,
    SavedForLaterItem,
    RecentlyViewedItem,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Coupon,
    UserCouponUsage,
    ReturnRequest,
    GiftWrapSetting,
    GiftCard,
)
from users.models import CustomUser
from products.models import Product, Batch, ProductVariant, ProductImage
from .serializers import (
    WishlistItemSerializer,
    SavedForLaterItemSerializer,
    CartItemSerializer,
    CartSerializer,
    OrderSerializer,
    ReturnRequestSerializer,
    GiftCardSerializer,
    GiftCardRedeemSerializer,
    GiftCardIssueSerializer,
)
from django.conf import settings
from decouple import config
import razorpay
import hmac
import hashlib
import json
import secrets
from decimal import Decimal
from django.utils import timezone
from shipping.services import create_shipment as create_shipping_label
import logging
from .services import process_order_success, render_invoice_latex, generate_invoice_pdf, cancel_order
from django.http import HttpResponse, Http404
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer, OpenApiExample
from rest_framework import serializers


logger = logging.getLogger(__name__)

class ApplyCouponView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="Apply a coupon to an order",
        request=inline_serializer(
            name='ApplyCouponRequest',
            fields={
                'order_id': serializers.IntegerField(),
                'coupon_code': serializers.CharField(),
            }
        ),
        responses={200: OrderSerializer}
    )
    @transaction.atomic
    def post(self, request):
        order_id = request.data.get("order_id")
        coupon_code = request.data.get("coupon_code")

        if not order_id or not coupon_code:
            return Response({"detail": "order_id and coupon_code are required."}, status=status.HTTP_400_BAD_REQUEST)

        order = resolve_order_for_request(order_id, request)
        
        if order.status != Order.Status.PENDING_PAYMENT:
            return Response({"detail": "Coupons can only be applied to orders pending payment."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            coupon = Coupon.objects.get(code__iexact=coupon_code, is_active=True)
        except Coupon.DoesNotExist:
            return Response({"detail": "Invalid or inactive coupon code."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate coupon
        now = timezone.now()
        if not (coupon.valid_from <= now <= coupon.valid_to):
            return Response({"detail": "Coupon is not valid at this time."}, status=status.HTTP_400_BAD_REQUEST)

        if coupon.times_used >= coupon.usage_limit:
            return Response({"detail": "Coupon has reached its usage limit."}, status=status.HTTP_400_BAD_REQUEST)
        
        if order.user:
            user_usage, _ = UserCouponUsage.objects.get_or_create(user=order.user, coupon=coupon)
        if user_usage.times_used >= coupon.limit_per_user:
            return Response({"detail": "You have reached the usage limit for this coupon."}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate discount
        if order.applied_coupon:
             # Revert previous coupon if any
            order.total_cost += order.discount_amount
            order.discount_amount = Decimal("0.00")

        discount_amount = Decimal("0.00")
        if coupon.discount_type == Coupon.DiscountType.PERCENTAGE:
            discount_amount = order.total_cost * (coupon.value / Decimal("100.00"))
        elif coupon.discount_type == Coupon.DiscountType.FIXED_AMOUNT:
            discount_amount = coupon.value
        
        # Ensure discount doesn't exceed total cost
        discount_amount = min(discount_amount, order.total_cost)

        order.applied_coupon = coupon
        order.discount_amount = discount_amount
        order.total_cost -= discount_amount
        order.save(update_fields=["applied_coupon", "discount_amount", "total_cost"])

        return Response(OrderSerializer(order).data)


class WishlistView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = [JWTAuthentication]

    def _get_context(self, request):
        user = request.user if request.user and request.user.is_authenticated else None
        session_key = CartView.get_request_session_key(request)
        cookie_needed = False

        if not user and not session_key:
            session_key = secrets.token_urlsafe(24)
            cookie_needed = True

        return user, session_key, cookie_needed

    def _attach_cookie(self, response, session_key, cookie_needed):
        if cookie_needed and session_key:
            CartView()._set_cart_cookie(response, session_key)

    def _serialize(self, request, user, session_key):
        if user:
            items = WishlistItem.objects.filter(user=user).select_related("variant__product")
        else:
            items = WishlistItem.objects.filter(session_key=session_key).select_related("variant__product")
        serializer = WishlistItemSerializer(items, many=True, context={'request': request})
        return serializer.data

    @extend_schema(summary="Get wishlist", responses={200: WishlistItemSerializer(many=True)})
    def get(self, request):
        user, session_key, cookie_needed = self._get_context(request)
        data = {"items": self._serialize(request, user, session_key)}
        response = Response(data)
        self._attach_cookie(response, session_key, cookie_needed)
        return response

    @extend_schema(
        summary="Add item to wishlist",
        request=inline_serializer(
            name='AddToWishlistRequest',
            fields={'variant_id': serializers.IntegerField()}
        ),
        responses={200: WishlistItemSerializer(many=True)}
    )
    def post(self, request):
        variant_id = request.data.get("variant_id")
        if not variant_id:
            return Response({"detail": "variant_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        variant = get_object_or_404(ProductVariant, id=variant_id)
        user, session_key, cookie_needed = self._get_context(request)

        if user:
            item, created = WishlistItem.objects.get_or_create(user=user, variant=variant)
        else:
            item, created = WishlistItem.objects.get_or_create(session_key=session_key, variant=variant)

        data = {"items": self._serialize(request, user, session_key)}
        response = Response(data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)
        self._attach_cookie(response, session_key, cookie_needed)
        return response

    @extend_schema(
        summary="Remove item from wishlist",
        request=inline_serializer(
            name='RemoveFromWishlistRequest',
            fields={'variant_id': serializers.IntegerField()}
        ),
        responses={200: WishlistItemSerializer(many=True)}
    )
    def delete(self, request):
        variant_id = request.data.get("variant_id")
        if not variant_id:
            return Response({"detail": "variant_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        user, session_key, cookie_needed = self._get_context(request)
        filters = {"variant_id": variant_id}
        if user:
            filters["user"] = user
        else:
            filters["session_key"] = session_key

        WishlistItem.objects.filter(**filters).delete()
        data = {"items": self._serialize(request, user, session_key)}
        response = Response(data, status=status.HTTP_200_OK)
        self._attach_cookie(response, session_key, cookie_needed)
        return response


class SavedForLaterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Get saved for later items", responses={200: SavedForLaterItemSerializer(many=True)})
    def get(self, request):
        items = SavedForLaterItem.objects.filter(user=request.user).select_related("variant__product")
        return Response(SavedForLaterItemSerializer(items, many=True).data)

    @extend_schema(
        summary="Add item to saved for later",
        request=inline_serializer(
            name='AddToSavedForLaterRequest',
            fields={'variant_id': serializers.IntegerField()}
        ),
        responses={201: SavedForLaterItemSerializer}
    )
    def post(self, request):
        variant_id = request.data.get("variant_id")
        if not variant_id:
            return Response({"detail": "variant_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        variant = get_object_or_404(ProductVariant, id=variant_id)
        item, created = SavedForLaterItem.objects.get_or_create(user=request.user, variant=variant)

        if not created:
            return Response({"detail": "Already saved."}, status=status.HTTP_200_OK)
        return Response(SavedForLaterItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Remove item from saved for later",
        request=inline_serializer(
            name='RemoveFromSavedForLaterRequest',
            fields={'variant_id': serializers.IntegerField()}
        ),
        responses={204: OpenApiResponse(description="Item removed from saved for later.")}
    )
    def delete(self, request):
        variant_id = request.data.get("variant_id")
        if not variant_id:
            return Response({"detail": "variant_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        SavedForLaterItem.objects.filter(user=request.user, variant_id=variant_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecentlyViewedView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = [JWTAuthentication]

    RECENTLY_VIEWED_COOKIE_NAME = "s4u_recently_viewed"
    RECENTLY_VIEWED_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

    @staticmethod
    def _generate_session_key():
        return secrets.token_urlsafe(24)

    @staticmethod
    def get_request_session_key(request):
        cookie_key = request.COOKIES.get(RecentlyViewedView.RECENTLY_VIEWED_COOKIE_NAME)
        header_key = request.headers.get("X-Recently-Viewed-Session")
        return header_key or cookie_key

    def _resolve_context(self, request):
        """Resolve user or session key for recently viewed items."""
        user = request.user if request.user.is_authenticated else None
        session_key = self.get_request_session_key(request)
        cookie_needs_update = False

        if not session_key:
            session_key = self._generate_session_key()
            cookie_needs_update = True

        return user, session_key, cookie_needs_update

    def _set_cookie(self, response, session_key, cookie_needs_update):
        """Set cookie for recently viewed session."""
        if cookie_needs_update and session_key:
            response.set_cookie(
                self.RECENTLY_VIEWED_COOKIE_NAME,
                session_key,
                max_age=self.RECENTLY_VIEWED_COOKIE_MAX_AGE,
                httponly=False,
                secure=getattr(settings, "SESSION_COOKIE_SECURE", False),
                samesite=getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax"),
            )

    @extend_schema(summary="Get recently viewed items")
    def get(self, request):
        user, session_key, cookie_needs_update = self._resolve_context(request)
        
        # Merge anonymous views into user account when logging in
        if user:
            # Transfer anonymous views to user account
            anonymous_items = RecentlyViewedItem.objects.filter(
                session_key=session_key, user__isnull=True
            )
            for item in anonymous_items:
                RecentlyViewedItem.objects.update_or_create(
                    user=user, variant=item.variant, defaults={"viewed_at": item.viewed_at}
                )
            anonymous_items.delete()

        # Get recently viewed items
        if user:
            items = (
                RecentlyViewedItem.objects
                    .filter(user=user)
                .select_related("variant__product")
                .order_by("-viewed_at")[:20]
            )
        else:
            items = (
                RecentlyViewedItem.objects
                .filter(session_key=session_key)
                .select_related("variant__product")
                .order_by("-viewed_at")[:20]
            )

        # re-use CartItemSerializer-like payload to return variant details only
        data = [
            {
                "variant": CartItemSerializer(instance=None).fields['variant'].to_representation(i.variant),
                "viewed_at": i.viewed_at,
            }
            for i in items
        ]
        
        response = Response(data)
        self._set_cookie(response, session_key, cookie_needs_update)
        return response

    @extend_schema(
        summary="Add/update a recently viewed variant",
        request=inline_serializer(
            name='RecentlyViewedUpsert',
            fields={
                'variant_id': serializers.IntegerField(required=False),
                'product_sku': serializers.CharField(required=False),
            }
        ),
    )
    def post(self, request):
        variant_id = request.data.get("variant_id")
        product_sku = request.data.get("product_sku")

        variant = None
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id)
        elif product_sku:
            product = get_object_or_404(Product, sku=product_sku)
            variant = product.variants.filter(is_default=True).first() or product.variants.first()
            if not variant:
                return Response({"detail": "No variant available for this product."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"detail": "variant_id or product_sku is required."}, status=status.HTTP_400_BAD_REQUEST)

        user, session_key, cookie_needs_update = self._resolve_context(request)
        
        # Merge anonymous views into user account when logging in
        if user:
            # Transfer anonymous views to user account
            anonymous_items = RecentlyViewedItem.objects.filter(
                session_key=session_key, user__isnull=True
            )
            for item in anonymous_items:
                try:
                    RecentlyViewedItem.objects.update_or_create(
                        user=user, variant=item.variant, defaults={"viewed_at": item.viewed_at}
                    )
                except Exception as e:
                    # Ignore database locked errors for tracking
                    pass
            try:
                anonymous_items.delete()
            except Exception as e:
                # Ignore database locked errors for tracking
                pass

        # Create or update recently viewed item with retry logic
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                if user:
                    RecentlyViewedItem.objects.update_or_create(
                        user=user, variant=variant, defaults={}
                    )
                else:
                    RecentlyViewedItem.objects.update_or_create(
                        session_key=session_key, variant=variant, defaults={}
                    )
                break  # Success, exit loop
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    # On final retry failure, just log and continue
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to track recently viewed after {max_retries} attempts: {e}")
                    break
                import time
                time.sleep(0.1 * retry_count)  # Exponential backoff

        response = Response(status=status.HTTP_204_NO_CONTENT)
        self._set_cookie(response, session_key, cookie_needs_update)
        return response


class CartView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = [JWTAuthentication]

    CART_COOKIE_NAME = "s4u_cart"
    CART_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

    @classmethod
    def get_request_session_key(cls, request):
        return request.headers.get("X-Cart-Session") or request.COOKIES.get(cls.CART_COOKIE_NAME)

    def _generate_session_key(self):
        return secrets.token_urlsafe(24)

    def _merge_carts(self, source: Cart, target: Cart):
        """Merge items and metadata from a guest cart into a user's cart."""
        for item in source.items.all():
            dest_item, created = CartItem.objects.get_or_create(
                cart=target,
                variant=item.variant,
                defaults={"quantity": item.quantity},
            )
            if not created:
                dest_item.quantity += item.quantity
                dest_item.save(update_fields=["quantity"])

        changed = False
        if source.applied_coupon and not target.applied_coupon:
            target.applied_coupon = source.applied_coupon
            target.coupon_discount_amount = source.coupon_discount_amount
            changed = True
        if source.gift_wrap and not target.gift_wrap:
            target.gift_wrap = True
            target.gift_wrap_amount = source.gift_wrap_amount
            changed = True

        if changed:
            target.save(update_fields=["applied_coupon", "coupon_discount_amount", "gift_wrap", "gift_wrap_amount"])

        source.delete()

    def _resolve_cart(self, request):
        user = request.user if request.user.is_authenticated else None
        cookie_key = request.COOKIES.get(self.CART_COOKIE_NAME)
        header_key = request.headers.get("X-Cart-Session")
        session_key = header_key or cookie_key
        cookie_needs_update = False

        if user:
            cart, _ = Cart.objects.get_or_create(user=user)
            if session_key and cart.session_key != session_key:
                session_cart = (
                    Cart.objects.filter(session_key=session_key)
                    .exclude(id=cart.id)
                    .first()
                )
                if session_cart:
                    self._merge_carts(session_cart, cart)
            if not cart.session_key:
                cart.session_key = session_key or self._generate_session_key()
                cart.save(update_fields=["session_key"])
            session_key = cart.session_key
            if cookie_key != session_key:
                cookie_needs_update = True
        else:
            cart = None
            if session_key:
                cart = Cart.objects.filter(session_key=session_key).first()
            if not cart:
                session_key = session_key or self._generate_session_key()
                cart = Cart.objects.create(session_key=session_key)
                cookie_needs_update = True
            elif cookie_key != session_key:
                cookie_needs_update = True

        return cart, session_key, cookie_needs_update

    def _with_item_prefetch(self):
        return Cart.objects.prefetch_related(
            "items__variant__product",
            "items__variant__product__images",
            "items__variant__product__tags",
            "items__variant__product__category",
        )

    def _set_cart_cookie(self, response: Response, session_key: str):
        if not session_key:
            return
        response.set_cookie(
            self.CART_COOKIE_NAME,
            session_key,
            max_age=self.CART_COOKIE_MAX_AGE,
            httponly=False,
            secure=getattr(settings, "SESSION_COOKIE_SECURE", False),
            samesite=getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax"),
        )

    def _recalculate_totals(self, cart: Cart):
        from products.deal_utils import get_deal_for_product_or_variant, calculate_deal_price
        from decimal import Decimal
        
        merchandise_total = Decimal("0.00")
        for item in cart.items.select_related("variant", "variant__product").all():
            variant = item.variant
            if not variant:
                continue
            
            # Get deal price if available
            deal, deal_price = get_deal_for_product_or_variant(variant.product, variant)
            if deal and deal_price:
                unit_price = deal_price
            else:
                unit_price = variant.discount_price or variant.price
            merchandise_total += Decimal(str(unit_price)) * item.quantity

        gift_wrap_amount = Decimal("0.00")
        if cart.gift_wrap:
            setting = GiftWrapSetting.objects.first()
            if setting and setting.is_enabled and setting.price > 0:
                gift_wrap_amount = setting.price
            else:
                cart.gift_wrap = False
        cart.gift_wrap_amount = gift_wrap_amount

        discount = Decimal("0.00")
        if cart.applied_coupon:
            coupon = cart.applied_coupon
            now = timezone.now()
            if not coupon.is_active or not (coupon.valid_from <= now <= coupon.valid_to):
                cart.applied_coupon = None
            else:
                base_amount = merchandise_total + gift_wrap_amount
                if coupon.discount_type == Coupon.DiscountType.PERCENTAGE:
                    discount = base_amount * (coupon.value / Decimal("100.00"))
                else:
                    discount = coupon.value
                if discount > base_amount:
                    discount = base_amount
        if discount < Decimal("0.00"):
            discount = Decimal("0.00")
        cart.coupon_discount_amount = discount.quantize(Decimal("0.01"))

        cart.save(update_fields=[
            "gift_wrap",
            "gift_wrap_amount",
            "applied_coupon",
            "coupon_discount_amount",
            "updated_at",
        ])

    def _payload_cart_response(self, request, cart: Cart):
        serializer = CartSerializer(cart, context={'request': request})
        return {
            "status": "success",
            "cart": serializer.data,
        }

    @extend_schema(summary="Get current cart", responses={200: CartSerializer})
    def get(self, request):
        cart, session_key, cookie_needed = self._resolve_cart(request)
        cart = self._with_item_prefetch().get(id=cart.id)
        self._recalculate_totals(cart)
        cart.refresh_from_db()
        cart = self._with_item_prefetch().get(id=cart.id)

        response = Response(self._payload_cart_response(request, cart))
        if cookie_needed:
            self._set_cart_cookie(response, session_key)
        return response

    @extend_schema(
        summary="Add or increment a cart item",
        request=inline_serializer(
            name="AddToCartRequest",
            fields={
                "variant_id": serializers.IntegerField(),
                "quantity": serializers.IntegerField(default=1),
            },
        ),
        responses={200: CartSerializer, 201: CartSerializer},
    )
    @transaction.atomic
    def post(self, request):
        variant_id = request.data.get("variant_id")
        if not variant_id:
            return Response({"detail": "variant_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        qty = int(request.data.get("quantity", 1))
        if qty <= 0:
            return Response({"detail": "Quantity must be positive."}, status=status.HTTP_400_BAD_REQUEST)
        
        variant = get_object_or_404(ProductVariant, id=variant_id)
        cart, session_key, cookie_needed = self._resolve_cart(request)

        existing_qty = (
            CartItem.objects.filter(cart=cart, variant=variant)
            .values_list("quantity", flat=True)
            .first()
            or 0
        )
        total_available = variant.stock
        if existing_qty + qty > total_available:
            return Response({"detail": "Insufficient stock."}, status=status.HTTP_400_BAD_REQUEST)

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={"quantity": qty},
        )
        if not created:
            item.quantity += qty
            item.save(update_fields=["quantity"])

        cart = self._with_item_prefetch().get(id=cart.id)
        self._recalculate_totals(cart)
        cart.refresh_from_db()
        cart = self._with_item_prefetch().get(id=cart.id)
        
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        message = "Item added to cart." if created else "Cart updated."
        payload = self._payload_cart_response(request, cart)
        payload["message"] = message

        response = Response(payload, status=status_code)
        if cookie_needed:
            self._set_cart_cookie(response, session_key)
        return response

    @extend_schema(
        summary="Set cart item quantity",
        request=inline_serializer(
            name="SetCartItemQuantityRequest",
            fields={
                "variant_id": serializers.IntegerField(),
                "quantity": serializers.IntegerField(),
            },
        ),
        responses={200: CartSerializer},
    )
    @transaction.atomic
    def patch(self, request):
        variant_id = request.data.get("variant_id")
        if not variant_id:
            return Response({"detail": "variant_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        qty = int(request.data.get("quantity", 1))
        if qty < 0:
            return Response({"detail": "Quantity cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
            
        cart, session_key, cookie_needed = self._resolve_cart(request)
        item = get_object_or_404(CartItem, cart=cart, variant_id=variant_id)
        
        if qty == 0:
            item.delete()
        else:
            total_available = item.variant.stock
            if qty > total_available:
                return Response({"detail": "Insufficient stock."}, status=status.HTTP_400_BAD_REQUEST)
            item.quantity = qty
            item.save(update_fields=["quantity"])
        
        cart = self._with_item_prefetch().get(id=cart.id)
        self._recalculate_totals(cart)
        cart.refresh_from_db()
        cart = self._with_item_prefetch().get(id=cart.id)
        
        payload = self._payload_cart_response(request, cart)
        payload["message"] = "Cart updated successfully."
        response = Response(payload)
        if cookie_needed:
            self._set_cart_cookie(response, session_key)
        return response

    @extend_schema(
        summary="Remove an item from cart",
        request=inline_serializer(
            name="RemoveFromCartRequest",
            fields={"variant_id": serializers.IntegerField()},
        ),
        responses={200: CartSerializer},
    )
    @transaction.atomic
    def delete(self, request):
        variant_id = request.data.get("variant_id")
        if not variant_id:
            return Response({"detail": "variant_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        cart, session_key, cookie_needed = self._resolve_cart(request)
        CartItem.objects.filter(cart=cart, variant_id=variant_id).delete()
        
        cart = self._with_item_prefetch().get(id=cart.id)
        self._recalculate_totals(cart)
        cart.refresh_from_db()
        cart = self._with_item_prefetch().get(id=cart.id)

        payload = self._payload_cart_response(request, cart)
        payload["message"] = "Item removed from cart."
        response = Response(payload)
        if cookie_needed:
            self._set_cart_cookie(response, session_key)
        return response


class CartGiftWrapView(CartView):
    @extend_schema(
        summary="Enable or disable gift wrap for the current cart",
        request=inline_serializer(
            name="CartGiftWrapRequest",
            fields={"gift_wrap": serializers.BooleanField()},
        ),
        responses={200: CartSerializer},
    )
    @transaction.atomic
    def patch(self, request):
        gift_wrap = request.data.get("gift_wrap")
        if gift_wrap is None:
            return Response({"detail": "gift_wrap is required."}, status=status.HTTP_400_BAD_REQUEST)

        cart, session_key, cookie_needed = self._resolve_cart(request)
        cart.gift_wrap = bool(gift_wrap)
        cart.save(update_fields=["gift_wrap"])

        cart = Cart.objects.prefetch_related("items__variant__product").get(id=cart.id)
        self._recalculate_totals(cart)
        cart = Cart.objects.prefetch_related("items__variant__product").get(id=cart.id)

        payload = self._payload_cart_response(request, cart)
        payload["message"] = "Gift wrap preference updated."
        response = Response(payload)
        if cookie_needed:
            self._set_cart_cookie(response, session_key)
        return response


class CartCouponView(CartView):
    @extend_schema(
        summary="Apply a coupon code to the cart",
        request=inline_serializer(
            name="CartApplyCouponRequest",
            fields={"coupon_code": serializers.CharField()},
        ),
        responses={200: CartSerializer},
    )
    @transaction.atomic
    def post(self, request):
        coupon_code = request.data.get("coupon_code")
        if not coupon_code:
            return Response({"detail": "coupon_code is required."}, status=status.HTTP_400_BAD_REQUEST)

        cart, session_key, cookie_needed = self._resolve_cart(request)

        try:
            coupon = Coupon.objects.get(code__iexact=coupon_code.strip(), is_active=True)
        except Coupon.DoesNotExist:
            return Response({"detail": "Invalid or inactive coupon code."}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        if not (coupon.valid_from <= now <= coupon.valid_to):
            return Response({"detail": "Coupon is not valid at this time."}, status=status.HTTP_400_BAD_REQUEST)
        if coupon.usage_limit and coupon.times_used >= coupon.usage_limit:
            return Response({"detail": "Coupon usage limit reached."}, status=status.HTTP_400_BAD_REQUEST)

        cart.applied_coupon = coupon
        cart.coupon_discount_amount = Decimal("0.00")
        cart.save(update_fields=["applied_coupon", "coupon_discount_amount"])

        cart = Cart.objects.prefetch_related("items__variant__product").get(id=cart.id)
        self._recalculate_totals(cart)
        cart = Cart.objects.prefetch_related("items__variant__product").get(id=cart.id)

        payload = self._payload_cart_response(request, cart)
        payload["message"] = "Coupon applied successfully."
        response = Response(payload)
        if cookie_needed:
            self._set_cart_cookie(response, session_key)
        return response

    @extend_schema(summary="Remove coupon from cart", responses={200: CartSerializer})
    @transaction.atomic
    def delete(self, request):
        cart, session_key, cookie_needed = self._resolve_cart(request)
        if not cart.applied_coupon:
            return Response({"detail": "No coupon applied."}, status=status.HTTP_400_BAD_REQUEST)

        cart.applied_coupon = None
        cart.coupon_discount_amount = Decimal("0.00")
        cart.save(update_fields=["applied_coupon", "coupon_discount_amount"])

        cart = Cart.objects.prefetch_related("items__variant__product").get(id=cart.id)
        self._recalculate_totals(cart)
        cart = Cart.objects.prefetch_related("items__variant__product").get(id=cart.id)

        payload = self._payload_cart_response(request, cart)
        payload["message"] = "Coupon removed from cart."
        response = Response(payload)
        if cookie_needed:
            self._set_cart_cookie(response, session_key)
        return response


def resolve_order_for_request(order_id, request):
    """Return an order matching either the authenticated user or the cart session."""
    user = request.user if request.user.is_authenticated else None
    if user:
        try:
            return Order.objects.get(id=order_id, user=user)
        except Order.DoesNotExist:
            pass

    session_key = CartView.get_request_session_key(request)
    if session_key:
        try:
            return Order.objects.get(id=order_id, session_key=session_key)
        except Order.DoesNotExist:
            pass

    raise Http404("Order not found for this user or session.")


def clear_cart_for_order(order: Order):
    cart = None
    if order.user_id:
        cart = Cart.objects.filter(user=order.user).first()
    elif order.session_key:
        cart = Cart.objects.filter(session_key=order.session_key).first()

    if not cart:
        return

    CartItem.objects.filter(cart=cart).delete()
    cart.applied_coupon = None
    cart.coupon_discount_amount = Decimal("0.00")
    cart.gift_wrap = False
    cart.gift_wrap_amount = Decimal("0.00")
    cart.save(update_fields=[
        "applied_coupon",
        "coupon_discount_amount",
        "gift_wrap",
        "gift_wrap_amount",
        "updated_at",
    ])


class CreatePreliminaryOrderView(APIView):
    permission_classes = [permissions.AllowAny]  # Allow guest checkout
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="Create a preliminary order from the cart",
        description="Creates an order in PENDING_PAYMENT status using the current cart session. Supports both authenticated and guest users.",
        responses={201: OrderSerializer},
    )
    @transaction.atomic
    def post(self, request):
        logger.info(
            "[CreatePreliminaryOrder] principal=%s payload_keys=%s",
            getattr(request.user, "id", None) if request.user.is_authenticated else "guest",
            list(request.data.keys()),
        )

        required_fields = ["full_name", "address_line1", "city", "postal_code", "email"]
        for field_name in required_fields:
            if not request.data.get(field_name):
                return Response({"detail": f"{field_name} is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Handle both authenticated and guest users
        user = request.user if request.user.is_authenticated else None
        session_key = CartView.get_request_session_key(request)
        
        if user:
            cart, _ = Cart.objects.get_or_create(user=user)
        else:
            # Guest checkout - get or create cart by session
            if not session_key:
                session_key = secrets.token_urlsafe(24)
            cart, _ = Cart.objects.get_or_create(session_key=session_key, defaults={'user': None})
        
        cart = Cart.objects.prefetch_related("items__variant__product").get(id=cart.id)
        CartView()._recalculate_totals(cart)
        cart = Cart.objects.prefetch_related("items__variant__product").get(id=cart.id)

        cart_items = list(cart.items.all())
        if not cart_items:
            return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        # inventory validation snapshot
        for item in cart_items:
            total_available = item.variant.stock
            if item.quantity > total_available:
                return Response({"detail": f"Insufficient stock for {item.variant.sku}."}, status=status.HTTP_400_BAD_REQUEST)

        payment_method = request.data.get("payment_method", Order.PaymentMethod.RAZORPAY)
        if payment_method not in Order.PaymentMethod.values:
            payment_method = Order.PaymentMethod.RAZORPAY

        email = request.data.get("email", "")
        full_name = request.data.get("full_name", "")
        phone = request.data.get("phone", "")
        
        # For guest checkout, create anonymous user
        order_user = user
        if not user:
            # Generate username from name for guest users
            from django.utils.text import slugify
            base_username = slugify(full_name.lower().replace(' ', '_'))[:20] or "guest"
            # Ensure unique username
            username = base_username
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            # Create anonymous guest user
            # Use create() instead of create_user() to allow no password
            order_user = CustomUser.objects.create(
                username=username,
                email=email or f"{username}@guest.space4u.in",
                is_active=True,
            )
            # Set unusable password for security
            order_user.set_unusable_password()
            order_user.save()
            # Mark as guest user (we can add a field later if needed)
            logger.info(f"[CreatePreliminaryOrder] Created guest user: {username}")

        # Save address for logged in users
        if user and user.is_authenticated:
            from users.models import UserAddress
            save_address = request.data.get("save_address", False)
            if save_address:
                UserAddress.objects.create(
                    user=user,
                    is_default=not UserAddress.objects.filter(user=user, is_default=True).exists(),
                    full_name=full_name,
                    phone=phone,
                    email=email,
                    address_line1=request.data.get("address_line1"),
                    address_line2=request.data.get("address_line2", ""),
                    city=request.data.get("city"),
                    state=request.data.get("state", ""),
                    postal_code=request.data.get("postal_code"),
                    country=request.data.get("country", "India"),
                )

        order = Order.objects.create(
            user=order_user,
            session_key=session_key if not user else '',
            status=Order.Status.PENDING_PAYMENT,
            full_name=full_name,
            address_line1=request.data.get("address_line1"),
            address_line2=request.data.get("address_line2", ""),
            city=request.data.get("city"),
            state=request.data.get("state", ""),
            postal_code=request.data.get("postal_code"),
            country=request.data.get("country", "India"),
            phone=phone,
            email=email,
            payment_method=payment_method,
            gift_wrap=cart.gift_wrap,
            gift_wrap_amount=cart.gift_wrap_amount,
            applied_coupon=cart.applied_coupon,
            discount_amount=cart.coupon_discount_amount,
        )

        from products.deal_utils import get_deal_for_product_or_variant

        merchandise_total = Decimal("0.00")
        for item in cart_items:
            variant = item.variant
            # Get deal price if available
            deal, deal_price = get_deal_for_product_or_variant(variant.product, variant)
            if deal and deal_price:
                unit_price = deal_price
            else:
                unit_price = variant.discount_price or variant.price
            line_total = Decimal(str(unit_price)) * item.quantity
            OrderItem.objects.create(
                order=order,
                product=item.variant.product,
                variant=item.variant,
                quantity=item.quantity,
                unit_price=unit_price,
                line_total=line_total,
            )
            merchandise_total += line_total

        total_cost = merchandise_total + (cart.gift_wrap_amount if cart.gift_wrap else Decimal("0.00")) - cart.coupon_discount_amount
        if total_cost < Decimal("0.00"):
            total_cost = Decimal("0.00")

        order.total_cost = total_cost
        order.save(update_fields=[
            "total_cost",
            "gift_wrap",
            "gift_wrap_amount",
            "applied_coupon",
            "discount_amount",
            "email",
        ])

        # Send order confirmation email
        try:
            from users.services import send_order_confirmation_email
            send_order_confirmation_email(order)
        except Exception as e:
            logger.error(f"Failed to send order confirmation email for order {order.id}: {e}")
            print(f"Failed to send order confirmation email for order {order.id}: {e}")

        response_data = OrderSerializer(order).data
        response = Response(response_data, status=status.HTTP_201_CREATED)
        
        # Set session cookie for guest users
        if not user and session_key:
            CartView()._set_cart_cookie(response, session_key)
        
        return response


class CreateRazorpayOrderView(APIView):
    permission_classes = [permissions.AllowAny]  # Allow guest checkout
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="Create a Razorpay order for payment",
        request=inline_serializer(
            name='CreateRazorpayOrderRequest',
            fields={
                'order_id': serializers.IntegerField(),
                'payment_method': serializers.CharField(required=False, default='RAZORPAY'),
                'apply_wallet': serializers.BooleanField(required=False, default=False),
            }
        ),
    )
    def post(self, request):
        logger.info("[CreatePayment] user=%s payload=%s", getattr(request.user, 'id', None), dict(request.data))
        print("[CreatePayment]", getattr(request.user, 'id', None), dict(request.data))
        order_id = request.data.get("order_id")
        if not order_id:
            return Response({"detail": "order_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        order = resolve_order_for_request(order_id, request)
        if order.status != Order.Status.PENDING_PAYMENT:
            return Response({"detail": "Order not pending payment"}, status=status.HTTP_400_BAD_REQUEST)

        # support COD flow
        if request.data.get("payment_method") == "COD":
            order.payment_method = Order.PaymentMethod.COD
            order.status = Order.Status.PAID  # treat as confirmed; settlement happens on delivery
            order.paid_at = timezone.now()
            order.save(update_fields=["payment_method", "status", "paid_at"])
            process_order_success(order)
            clear_cart_for_order(order)
            logger.info("[CreatePayment] COD confirmed order_id=%s", order.id)
            print("[CreatePayment] COD confirmed", order.id)
            return Response({
                "order_id": order.id,
                "payment_method": order.payment_method,
                "amount": int(order.total_cost * 100),
                "currency": order.currency,
                "message": "COD order created successfully.",
            })

        # The amount due is now the final total_cost which includes discounts
        amount_due = order.total_cost
        
        # apply wallet if requested
        wallet_apply = request.data.get("apply_wallet", False)
        if wallet_apply and getattr(request.user, "is_authenticated", False) and hasattr(request.user, "wallet_balance"):
            wallet_to_apply = min(request.user.wallet_balance, amount_due)
            order.wallet_applied_amount = wallet_to_apply
            amount_due = amount_due - wallet_to_apply

        # Handle zero-amount (wallet-only or fully discounted) orders
        if amount_due <= 0:
            order.status = Order.Status.PAID
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at", "wallet_applied_amount"])
            process_order_success(order)
            clear_cart_for_order(order)
            return Response({
                "order_id": order.id,
                "razorpay_order_id": None,
                "amount": 0,
                "currency": order.currency,
                "key": config("RAZORPAY_KEY_ID"),
                "message": "Order paid in full with wallet/discounts.",
            })

        # Razorpay expects amount in paise
        amount_paise = int(amount_due * 100)

        logger.info("[CreatePayment] creating Razorpay order order_id=%s amount_paise=%s", order.id, amount_paise)
        print("[CreatePayment] creating rp order", order.id, amount_paise)
        client = razorpay.Client(auth=(config("RAZORPAY_KEY_ID"), config("RAZORPAY_KEY_SECRET")))
        rp_order = client.order.create({
            "amount": amount_paise,
            "currency": order.currency,
            "receipt": f"order_{order.id}",
            "payment_capture": 1,
        })

        order.razorpay_order_id = rp_order.get("id", "")
        order.save(update_fields=["razorpay_order_id", "wallet_applied_amount"])
        logger.info("[CreatePayment] rp_order_id=%s for order_id=%s", order.razorpay_order_id, order.id)
        print("[CreatePayment] rp_order_id", order.razorpay_order_id)

        return Response({
            "order_id": order.id,
            "razorpay_order_id": order.razorpay_order_id,
            "amount": amount_paise,
            "currency": order.currency,
            "key": config("RAZORPAY_KEY_ID"),
        })


class RazorpayWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Handle Razorpay webhooks",
        description="This endpoint is called by Razorpay to notify about payment events. It should not be called by frontend clients. It verifies the signature and processes payment success or failure.",
        request=inline_serializer(
            name='RazorpayWebhookPayload',
            fields={
                'event': serializers.CharField(),
                'payload': serializers.JSONField()
            }
        ),
        responses={
            200: OpenApiResponse(description="Webhook processed successfully"),
            400: OpenApiResponse(description="Invalid signature or missing data")
        }
    )
    @transaction.atomic
    def post(self, request):
        logger.info("[Webhook] headers_keys=%s", list(request.headers.keys()))
        print("[Webhook] headers received")
        # Verify signature
        webhook_secret = config("RAZORPAY_WEBHOOK_SECRET")
        received_sig = request.headers.get("X-Razorpay-Signature")
        body = request.body
        computed_sig = hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(received_sig or "", computed_sig):
            logger.warning("[Webhook] invalid signature received=%s computed=%s", received_sig, computed_sig)
            print("[Webhook] invalid signature")
            return Response({"detail": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        payload = json.loads(body.decode("utf-8"))
        event = payload.get("event")
        payload_entity = payload.get("payload", {})
        payment_entity = (payload_entity.get("payment") or {}).get("entity") or {}
        rp_order_id = payment_entity.get("order_id")

        if not rp_order_id:
            logger.warning("[Webhook] missing order reference in payload")
            print("[Webhook] missing order reference")
            return Response({"detail": "Missing order reference"}, status=status.HTTP_400_BAD_REQUEST)

        order = get_object_or_404(Order, razorpay_order_id=rp_order_id)

        if event == "payment.captured":
            logger.info("[Webhook] payment.captured order_id=%s", order.id)
            print("[Webhook] payment.captured", order.id)
            order.razorpay_payment_id = payment_entity.get("id", "")
            order.status = Order.Status.PAID
            order.paid_at = timezone.now()
            order.save(update_fields=["razorpay_payment_id", "status", "paid_at"])
            process_order_success(order)
            logger.info("[Webhook] processed order_id=%s", order.id)
            print("[Webhook] processed", order.id)

        elif event in ("payment.failed", "payment.captured.failed"):
            logger.warning("[Webhook] payment failed order_id=%s", order.id)
            print("[Webhook] payment failed", order.id)
            # Revert coupon usage if payment fails
            if order.applied_coupon:
                order.total_cost += order.discount_amount
                order.discount_amount = Decimal("0.00")
                order.applied_coupon = None
                logger.info("[Webhook] coupon reverted order_id=%s", order.id)
                print("[Webhook] coupon reverted", order.id)

            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status", "total_cost", "discount_amount", "applied_coupon"])

        elif event == "refund.processed":
            logger.info("[Webhook] refund.processed")
            print("[Webhook] refund processed")
            # Update OrderRefund status if exists
            refund_entity = payload_entity.get("refund", {})
            rp_refund_id = refund_entity.get("id")
            if rp_refund_id:
                from .models import OrderRefund
                try:
                    rf = OrderRefund.objects.get(transaction_id=rp_refund_id)
                    rf.status = rf.Status.COMPLETED
                    rf.save(update_fields=["status"])
                    logger.info(f"[Webhook] updated OrderRefund {rf.id} to COMPLETED")
                except OrderRefund.DoesNotExist:
                    logger.warning(f"[Webhook] OrderRefund not found for Razorpay refund ID {rp_refund_id}")

        return Response({"status": "ok"})

class ReturnRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Create a return request", responses={201: ReturnRequestSerializer})
    def post(self, request):
        serializer = ReturnRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ReturnRequestListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="List user's return requests", responses={200: ReturnRequestSerializer(many=True)})
    def get(self, request):
        return_requests = ReturnRequest.objects.filter(order_item__order__user=request.user)
        serializer = ReturnRequestSerializer(return_requests, many=True)
        return Response(serializer.data)


class InvoiceTexView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get LaTeX source for an invoice",
        description="A helper/debug endpoint that returns the raw LaTeX source code for an invoice.",
        responses={
            200: OpenApiResponse(
                description="LaTeX source for the invoice.",
                examples=[
                    OpenApiExample(
                        'Invoice LaTeX Example',
                        value={'latex': '\\documentclass{article}...'}
                    )
                ]
            )
        }
    )
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        latex_source = render_invoice_latex(order)
        return Response({"latex": latex_source})


class InvoicePDFView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get PDF invoice for an order",
        description="Generates and returns a full PDF invoice for a completed order.",
        responses={
            200: OpenApiResponse(
                description="PDF invoice file.",
                response=bytes,
                examples=[
                    OpenApiExample(
                        'Invoice PDF Example',
                        value=b'%PDF-1.5...',
                        media_type='application/pdf'
                    )
                ]
            )
        }
    )
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        try:
            pdf_content = generate_invoice_pdf(order)
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
            return response
        except Exception as e:
            logger.error(f"Failed to generate invoice PDF for order {order.id}: {e}")
            return Response({"detail": "Could not generate invoice PDF."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InternalInvoicePDFView(APIView):
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        summary="Get PDF invoice for any order (Internal/Admin)",
        description="Staff-only endpoint to generate invoices for any order, including offline orders.",
        responses={
            200: OpenApiResponse(
                description="PDF invoice file.",
                response=bytes,
            )
        }
    )
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        try:
            pdf_content = generate_invoice_pdf(order)
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
            return response
        except Exception as e:
            logger.error(f"Failed to generate internal invoice PDF for order {order.id}: {e}")
            return Response({"detail": "Could not generate invoice PDF."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GiftCardListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="List gift cards",
        description="Retrieve gift cards associated with the authenticated user. Staff members can view all gift cards.",
        responses={200: GiftCardSerializer(many=True)},
    )
    def get(self, request):
        queryset = GiftCard.objects.select_related("purchaser", "redeemed_by")
        if not request.user.is_staff:
            queryset = queryset.filter(Q(purchaser=request.user) | Q(redeemed_by=request.user))
        serializer = GiftCardSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)


class GiftCardIssueView(APIView):
    permission_classes = [permissions.IsAdminUser]
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="Issue a new gift card",
        request=GiftCardIssueSerializer,
        responses={201: GiftCardSerializer},
    )
    def post(self, request):
        serializer = GiftCardIssueSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        gift_card = serializer.save()
        output = GiftCardSerializer(gift_card, context={"request": request}).data
        return Response(output, status=status.HTTP_201_CREATED)


class GiftCardRedeemView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="Redeem a gift card",
        request=GiftCardRedeemSerializer,
        responses={200: OpenApiResponse(description="Gift card redeemed successfully.")},
    )
    def post(self, request):
        serializer = GiftCardRedeemSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        gift_card = serializer.context.get("gift_card")
        if gift_card is None:
            return Response({"detail": "Gift card could not be validated."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            credited_amount = gift_card.redeem_to_wallet(request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        gift_card.refresh_from_db()

        response_payload = {
            "detail": "Gift card redeemed successfully.",
            "gift_card": GiftCardSerializer(gift_card, context={"request": request}).data,
            "amount_credited": str(credited_amount),
            "wallet_balance": str(request.user.wallet_balance),
        }
        return Response(response_payload, status=status.HTTP_200_OK)


class VerifyRazorpayPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="Verify Razorpay payment from client",
        description="Verifies the Razorpay payment using the signature returned by Checkout and updates order to PAID.",
        request=inline_serializer(
            name='VerifyRazorpayPaymentRequest',
            fields={
                'order_id': serializers.IntegerField(),
                'razorpay_order_id': serializers.CharField(),
                'razorpay_payment_id': serializers.CharField(),
                'razorpay_signature': serializers.CharField(),
            }
        ),
        responses={200: OpenApiResponse(description="Payment verified and order updated")}
    )
    @transaction.atomic
    def post(self, request):
        order_id = request.data.get("order_id")
        rp_order_id = request.data.get("razorpay_order_id")
        rp_payment_id = request.data.get("razorpay_payment_id")
        rp_signature = request.data.get("razorpay_signature")

        logger.info("[Verify] user=%s payload=%s", getattr(request.user, 'id', None), dict(request.data))
        print("[Verify]", getattr(request.user, 'id', None), dict(request.data))

        if not (order_id and rp_order_id and rp_payment_id and rp_signature):
            return Response({"detail": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

        order = resolve_order_for_request(order_id, request)
        if order.razorpay_order_id != rp_order_id:
            return Response({"detail": "Order mismatch."}, status=status.HTTP_400_BAD_REQUEST)

        data = f"{rp_order_id}|{rp_payment_id}".encode()
        secret = config("RAZORPAY_KEY_SECRET").encode()
        expected = hmac.new(secret, data, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, rp_signature):
            logger.warning("[Verify] invalid signature for order_id=%s", order_id)
            return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

        order.razorpay_payment_id = rp_payment_id
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.save(update_fields=["razorpay_payment_id", "status", "paid_at"])
        process_order_success(order)
        clear_cart_for_order(order)
        
        # Calculate cashback for response
        from products.deal_utils import get_deal_for_product_or_variant
        total_cashback = Decimal("0.00")
        for item in order.items.select_related("variant", "variant__product").all():
            variant = item.variant
            if not variant:
                continue
            deal, _ = get_deal_for_product_or_variant(variant.product, variant)
            if deal and deal.cashback_amount and deal.cashback_amount > 0:
                total_cashback += deal.cashback_amount * item.quantity
        
        logger.info("[Verify] order_id=%s verified and processed", order.id)
        print("[Verify] processed", order.id)
        
        response_data = {
            "status": "verified",
            "order_id": order.id,
            "cashback_amount": str(total_cashback) if total_cashback > 0 else None,
        }
        return Response(response_data)


class CancelOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="Cancel an order",
        description="Cancels an order if allowed. Releases reservations and creates refund if prepaid and not shipped.",
        request=inline_serializer(
            name='CancelOrderRequest',
            fields={'order_id': serializers.IntegerField()},
        ),
        responses={200: OpenApiResponse(description="Order cancelled or not allowed")}
    )
    def post(self, request):
        order_id = request.data.get("order_id")
        if not order_id:
            return Response({"detail": "order_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        order = resolve_order_for_request(order_id, request)

        # Disallow cancellation after shipment
        if order.status == Order.Status.SHIPPED:
            return Response({"detail": "Order has been shipped and cannot be cancelled."}, status=status.HTTP_400_BAD_REQUEST)

        # For COD and shipped case, front-end should hide; backend enforces above
        # For other statuses, allow cancel
        if order.status in (Order.Status.PENDING_PAYMENT, Order.Status.PAID, Order.Status.PROCESSING):
            cancel_order(order)
            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status"])
            
            # Send cancellation email notification
            try:
                from users.services import send_shipping_update_email
                send_shipping_update_email(order)
            except Exception as e:
                logger.error(f"Failed to send cancellation email for order {order.id}: {e}")
                print(f"Failed to send cancellation email for order {order.id}: {e}")
            
            return Response({"status": "cancelled", "order_id": order.id})

        return Response({"detail": "Order cannot be cancelled in its current status."}, status=status.HTTP_400_BAD_REQUEST)

class OrderDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="Get order details",
        description="Retrieves detailed information about a specific order including shipment tracking.",
        responses={200: OrderSerializer}
    )
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data)


class OrderListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @extend_schema(summary="List user's orders", responses={200: OrderSerializer(many=True)})
    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by("-created_at")
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data)
