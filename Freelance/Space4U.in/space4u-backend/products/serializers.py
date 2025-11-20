from rest_framework import serializers
from decimal import Decimal
from .models import Product, ProductImage, Category, ProductVariant, ProductReview, TrendingDeal
from .deal_utils import get_deal_for_product_or_variant, calculate_deal_price
from commerce.currency_utils import convert_currency, get_currency_symbol

class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['image']

    def get_image(self, obj):
        request = self.context.get('request')
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name', 'slug']

class ProductVariantSerializer(serializers.ModelSerializer):
    stock = serializers.IntegerField(read_only=True)
    deal_price = serializers.SerializerMethodField()
    deal_info = serializers.SerializerMethodField()
    cashback_amount = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    currency_symbol = serializers.SerializerMethodField()
    converted_price = serializers.SerializerMethodField()
    converted_discount_price = serializers.SerializerMethodField()
    converted_deal_price = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'name', 'sku', 'price', 'discount_price', 
            'size', 'color', 'stock', 'is_default',
            'deal_price', 'deal_info', 'cashback_amount',
            'currency', 'currency_symbol', 'converted_price',
            'converted_discount_price', 'converted_deal_price'
        ]
    
    def _get_request_currency(self):
        """Get currency from request context."""
        request = self.context.get('request')
        if request and hasattr(request, 'currency'):
            return request.currency
        return 'INR'
    
    def _convert_price(self, price_inr):
        """Convert price from INR to request currency."""
        if not price_inr:
            return None
        currency = self._get_request_currency()
        if currency == 'INR':
            return float(price_inr)
        converted = convert_currency(Decimal(str(price_inr)), 'INR', currency)
        return float(converted)
    
    def get_currency(self, obj):
        return self._get_request_currency()
    
    def get_currency_symbol(self, obj):
        return get_currency_symbol(self._get_request_currency())
    
    def get_converted_price(self, obj):
        return self._convert_price(obj.price)
    
    def get_converted_discount_price(self, obj):
        return self._convert_price(obj.discount_price)
    
    def get_converted_deal_price(self, obj):
        deal_price = self.get_deal_price(obj)
        if deal_price:
            return self._convert_price(Decimal(deal_price))
        return None
    
    def get_deal_price(self, obj) -> str | None:
        """Get price after applying active deals."""
        try:
            if not obj.product:
                return None
            deal, calculated_price = get_deal_for_product_or_variant(obj.product, obj)
            if deal and calculated_price:
                return str(calculated_price)
        except Exception:
            # Gracefully handle any errors in deal calculation
            pass
        return None
    
    def get_deal_info(self, obj) -> dict | None:
        """Get deal information for this variant."""
        try:
            if not obj.product:
                return None
            deal, calculated_price = get_deal_for_product_or_variant(obj.product, obj)
            if deal and calculated_price:
                base_price = Decimal(str(obj.price))
                _, deal_info = calculate_deal_price(base_price, deal)
                return {
                    'deal_id': deal_info.get('deal_id'),
                    'deal_type': deal_info.get('deal_type'),
                    'deal_label': deal_info.get('deal_label'),
                    'discount_percent': float(deal_info.get('discount_percent', 0)),
                    'discount_amount': str(deal_info.get('discount_amount', 0)),
                }
        except Exception:
            # Gracefully handle any errors in deal calculation
            pass
        return None
    
    def get_cashback_amount(self, obj) -> str | None:
        """Get cashback amount for this variant."""
        try:
            if not obj.product:
                return None
            deal, _ = get_deal_for_product_or_variant(obj.product, obj)
            if deal and deal.cashback_amount:
                return str(deal.cashback_amount)
        except Exception:
            # Gracefully handle any errors in deal calculation
            pass
        return None

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    tags = serializers.StringRelatedField(many=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    image = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True)
    deal_price = serializers.SerializerMethodField()
    deal_info = serializers.SerializerMethodField()
    cashback_amount = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    currency_symbol = serializers.SerializerMethodField()
    converted_price = serializers.SerializerMethodField()
    converted_discount_price = serializers.SerializerMethodField()
    converted_deal_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'sku', 'price', 'discount_price',
            'category', 'tags', 'image', 'images', 'variants', 'average_rating',
            'deal_price', 'deal_info', 'cashback_amount',
            'currency', 'currency_symbol', 'converted_price',
            'converted_discount_price', 'converted_deal_price'
        ]
    
    def _get_request_currency(self):
        """Get currency from request context."""
        request = self.context.get('request')
        if request and hasattr(request, 'currency'):
            return request.currency
        return 'INR'

    def _convert_price(self, price_inr):
        """Convert price from INR to request currency."""
        if not price_inr:
            return None
        currency = self._get_request_currency()
        if currency == 'INR':
            return float(price_inr)
        converted = convert_currency(Decimal(str(price_inr)), 'INR', currency)
        return float(converted) if converted is not None else None

    def get_currency(self, obj):
        return self._get_request_currency()

    def get_currency_symbol(self, obj):
        return get_currency_symbol(self._get_request_currency())

    def get_converted_price(self, obj):
        return self._convert_price(obj.price)

    def get_converted_discount_price(self, obj):
        return self._convert_price(obj.discount_price)

    def get_converted_deal_price(self, obj):
        deal_price = self.get_deal_price(obj)
        if deal_price:
            return self._convert_price(Decimal(deal_price))
        return None

    def get_image(self, obj):
        request = self.context.get('request')
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None
    
    def get_deal_price(self, obj) -> str | None:
        """Get price after applying active deals (for product-level pricing)."""
        try:
            if obj.has_variants:
                return None  # Use variant deal prices instead
            deal, calculated_price = get_deal_for_product_or_variant(obj)
            if deal and calculated_price:
                return str(calculated_price)
        except Exception:
            # Gracefully handle any errors in deal calculation
            pass
        return None
    
    def get_deal_info(self, obj) -> dict | None:
        """Get deal information for this product."""
        try:
            if obj.has_variants:
                return None  # Use variant deal info instead
            deal, calculated_price = get_deal_for_product_or_variant(obj)
            if deal and calculated_price:
                base_price = Decimal(str(obj.price or 0))
                if base_price > 0:
                    _, deal_info = calculate_deal_price(base_price, deal)
                    return {
                        'deal_id': deal_info.get('deal_id'),
                        'deal_type': deal_info.get('deal_type'),
                        'deal_label': deal_info.get('deal_label'),
                        'discount_percent': float(deal_info.get('discount_percent', 0)),
                        'discount_amount': str(deal_info.get('discount_amount', 0)),
                    }
        except Exception:
            # Gracefully handle any errors in deal calculation
            pass
        return None
    
    def get_cashback_amount(self, obj) -> str | None:
        """Get cashback amount for this product."""
        try:
            deal, _ = get_deal_for_product_or_variant(obj)
            if deal and deal.cashback_amount:
                return str(deal.cashback_amount)
        except Exception:
            # Gracefully handle any errors in deal calculation
            pass
        return None


class ProductReviewSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = ProductReview
        fields = ['id', 'product', 'user', 'user_name', 'rating', 'title', 'body', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and representation.get('image'):
            representation['image'] = request.build_absolute_uri(instance.image.url)
        return representation


class TrendingDealSerializer(serializers.ModelSerializer):
    target_url = serializers.SerializerMethodField()
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    is_live = serializers.BooleanField(read_only=True)

    class Meta:
        model = TrendingDeal
        fields = [
            'id', 'deal_type', 'label', 'product_sku', 'category_slug',
            'discount_percent', 'cashback_amount', 'flat_discount_amount',
            'target_url', 'display_order', 'starts_at', 'ends_at', 'is_live'
        ]

    def get_target_url(self, obj) -> str | None:
        return obj.get_target_url()
