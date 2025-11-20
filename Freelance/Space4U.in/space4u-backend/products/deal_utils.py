"""
Utilities for calculating deal prices and applying discounts.
"""
from decimal import Decimal
from django.conf import settings
from .models import TrendingDeal, Product, ProductVariant


def get_minimum_price_threshold():
    """Get minimum price threshold from settings (default 30%)."""
    threshold = getattr(settings, 'MINIMUM_PRICE_THRESHOLD', 30.0)
    # Convert to Decimal if it's a float/int
    return Decimal(str(threshold))


def calculate_deal_price(base_price: Decimal, deal: TrendingDeal) -> tuple[Decimal, dict]:
    """
    Calculate the final price after applying a deal.
    
    Returns:
        tuple: (final_price, deal_info)
        deal_info contains: {
            'original_price': base_price,
            'deal_price': final_price,
            'discount_amount': amount saved,
            'discount_percent': percentage off,
            'cashback_amount': cashback if applicable,
            'deal_type': deal.deal_type
        }
    """
    if not deal or not deal.is_live:
        return base_price, {}
    
    final_price = base_price
    discount_amount = Decimal('0.00')
    discount_percent = Decimal('0.00')
    cashback_amount = deal.cashback_amount or Decimal('0.00')
    
    # Apply percentage discount
    if deal.discount_percent:
        discount_percent = deal.discount_percent
        discount_amount = base_price * (discount_percent / Decimal('100.00'))
        final_price = base_price - discount_amount
    
    # Apply flat discount
    elif deal.flat_discount_amount:
        discount_amount = deal.flat_discount_amount
        final_price = base_price - discount_amount
        discount_percent = (discount_amount / base_price) * Decimal('100.00') if base_price > 0 else Decimal('0.00')
    
    # Enforce minimum price threshold
    min_threshold = get_minimum_price_threshold()
    min_price = base_price * (min_threshold / Decimal('100.00'))
    
    if final_price < min_price:
        final_price = min_price
        discount_amount = base_price - final_price
        discount_percent = (discount_amount / base_price) * Decimal('100.00') if base_price > 0 else Decimal('0.00')
    
    if final_price < 0:
        final_price = Decimal('0.00')
    
    return final_price, {
        'original_price': base_price,
        'deal_price': final_price,
        'discount_amount': discount_amount,
        'discount_percent': discount_percent,
        'cashback_amount': cashback_amount,
        'deal_type': deal.deal_type,
        'deal_id': deal.id,
        'deal_label': deal.label,
    }


def get_active_deal_for_product(product: Product) -> TrendingDeal | None:
    """Get active deal for a specific product."""
    return TrendingDeal.objects.live().filter(
        product=product,
    ).order_by('-display_order', '-created_at').first()


def get_active_deal_for_category(product: Product) -> TrendingDeal | None:
    """Get active deal for a product's category."""
    if not product.category:
        return None
    
    return TrendingDeal.objects.live().filter(
        category=product.category,
        product__isnull=True,  # Category-wide deal, not product-specific
    ).order_by('-display_order', '-created_at').first()


def get_deal_for_product_or_variant(product: Product, variant: ProductVariant = None) -> tuple[TrendingDeal | None, Decimal | None]:
    """
    Get the best deal for a product or variant.
    
    Returns:
        tuple: (deal, calculated_price)
        If no deal, returns (None, None)
    """
    # Priority: Product-specific deal > Category deal
    deal = get_active_deal_for_product(product)
    if not deal:
        deal = get_active_deal_for_category(product)
    
    if not deal:
        return None, None
    
    # Get base price
    base_price = None
    if variant:
        base_price = variant.price
    elif product.price:
        base_price = product.price
    else:
        # Get default variant price
        default_variant = product.variants.filter(is_default=True).first() or product.variants.first()
        if default_variant:
            base_price = default_variant.price
    
    if not base_price:
        return None, None
    
    calculated_price, _ = calculate_deal_price(base_price, deal)
    return deal, calculated_price

