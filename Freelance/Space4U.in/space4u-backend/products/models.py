import uuid
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from taggit.managers import TaggableManager
import time

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PUBLISHED = 'PUBLISHED', 'Published'
        ARCHIVED = 'ARCHIVED', 'Archived'

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # These fields are deprecated and will be moved to ProductVariant.
    # Made nullable to allow for a gradual migration.
    sku = models.CharField(max_length=100, unique=True, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Optional: If set, this becomes the sale price.")
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    
    has_variants = models.BooleanField(default=False, help_text="Check if this product has multiple variants like size or color.")
    tags = TaggableManager(blank=True)

    # Link back to the source scraped product
    scraped_product = models.OneToOneField('ScrapedProduct', on_delete=models.SET_NULL, null=True, blank=True, related_name='imported_product')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def average_rating(self):
        agg = self.reviews.aggregate(avg=models.Avg('rating'))
        return agg.get('avg') or 0

    def save(self, *args, **kwargs):
        # The SKU and price on the Product model itself are deprecated.
        # We use them to create/update the default variant for non-variant products.
        super().save(*args, **kwargs)

        if not self.has_variants:
            # This product is managed as a single entity.
            # Ensure there is exactly one variant that mirrors the product's details.
            default_variant, created = self.variants.get_or_create(
                is_default=True,
                defaults={
                    'name': self.name,
                    'sku': self.sku or f"SKU-{self.id}", # Ensure SKU exists
                    'price': self.price or 0,
                    'discount_price': self.discount_price,
                }
            )
            
            if not created:
                # If the default variant already existed, update it from the product's fields.
                # This keeps the variant synced if the main product's deprecated fields are edited.
                update_fields = {}
                if default_variant.sku != self.sku:
                    update_fields['sku'] = self.sku
                if default_variant.price != self.price:
                    update_fields['price'] = self.price or 0
                if default_variant.discount_price != self.discount_price:
                    update_fields['discount_price'] = self.discount_price
                
                if update_fields:
                    for key, value in update_fields.items():
                        setattr(default_variant, key, value)
                    default_variant.save(update_fields=update_fields.keys())
            
            # Ensure no other variants exist for a single-variant product.
            self.variants.exclude(pk=default_variant.pk).delete()


    def __str__(self):
        return f"{self.name} ({self.sku or 'no-sku'})"

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=255, help_text="e.g., Large, Blue")
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reserved_quantity = models.PositiveIntegerField(default=0)
    
    # Example attributes
    size = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)

    is_default = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('product', 'size', 'color')

    def __str__(self):
        return f"{self.product.name} - {self.name} ({self.sku})"
    
    @property
    def stock(self):
        """Return available stock: total_stock - reserved."""
        return max(self.total_stock - self.reserved_quantity, 0)

    @property
    def total_stock(self):
        """Physical count in warehouse across batches (variant-first, legacy product batches included)."""
        total = 0
        for batch in self.batches.all():
            if batch.quantity_current is not None:
                total += batch.quantity_current
        for batch in self.product.batches.filter(variant__isnull=True):
            if batch.quantity_current is not None:
                total += batch.quantity_current
        return total

    @property
    def reserved(self):
        return self.reserved_quantity

    @property
    def available(self):
        return self.stock


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='product_reviews')
    user_name = models.CharField(max_length=255, blank=True, help_text="Required for guest reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    image = models.ImageField(upload_to='review_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "user")
        ordering = ['-created_at']

    def __str__(self):
        return f"Review {self.rating} for {self.product_id} by {self.user_id}"

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/additional/')

    def __str__(self):
        return f"Image for {self.product.name}"

class Batch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, related_name='batches', on_delete=models.CASCADE, null=True, blank=True) # DEPRECATED
    variant = models.ForeignKey(ProductVariant, related_name='batches', on_delete=models.CASCADE, null=True, blank=True)
    batch_code = models.CharField(max_length=100, unique=True, blank=True)
    quantity_initial = models.PositiveIntegerField()
    quantity_current = models.PositiveIntegerField()
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Cost per item in this batch")
    received_date = models.DateField()
    qr_code_generated = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        
        # if this is a new batch, set current quantity to initial
        if is_new:
            self.quantity_current = self.quantity_initial

        if not self.batch_code:
            # this logic is slightly changed to be more robust
            timestamp_str = timezone.now().strftime('%Y%m%d-%H%M%S')

            sku_part = "UNKNOWN"
            if self.variant:
                sku_part = self.variant.sku
            elif self.product:
                sku_part = self.product.sku

            self.batch_code = f"BATCH-{sku_part}-{timestamp_str}"
        
        super().save(*args, **kwargs)

        # if it was a new batch, create the initial stock-in record
        if is_new:
            StockMovement.objects.create(
                batch=self,
                change=self.quantity_initial,
                notes="Initial batch creation"
            )

    def __str__(self):
        name = ""
        if self.variant:
            name = self.variant.product.name
        elif self.product:
            name = self.product.name
        return f"Batch for {name} - {self.batch_code}"

class StockAdjustmentReason(models.Model):
    reason = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.reason

class StockMovement(models.Model):
    batch = models.ForeignKey(Batch, related_name='movements', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey('commerce.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='related_stock_movements')
    change = models.IntegerField(help_text="Positive for stock-in, negative for stock-out/sale")
    reason = models.ForeignKey(StockAdjustmentReason, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=255, blank=True, help_text="Legacy reason or additional details.")

    def __str__(self):
        return f"{self.change} items for {self.batch.batch_code} at {self.timestamp}"

# new model to hold raw scraped data
class ScrapedProduct(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image_urls = models.JSONField(default=list)
    tags = models.JSONField(default=list)
    
    source_site = models.CharField(max_length=100)
    source_url = models.URLField(max_length=1024, unique=True)
    
    imported = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} from {self.source_site}"

def generate_sku(name, source_site):
    """Generates a more meaningful SKU."""
    name_slug = slugify(name)[:50]
    source_slug = slugify(source_site)[:10]
    base_sku = f"{source_slug.upper()}-{name_slug.upper()}"
    
    # Ensure uniqueness
    sku = base_sku
    counter = 1
    while Product.objects.filter(sku=sku).exists():
        sku = f"{base_sku}-{counter}"
        counter += 1
    return sku


class TrendingDealQuerySet(models.QuerySet):
    def live(self, reference_time=None):
        reference_time = reference_time or timezone.now()
        return self.filter(
            is_active=True
        ).filter(
            Q(starts_at__lte=reference_time) | Q(starts_at__isnull=True),
            Q(ends_at__gte=reference_time) | Q(ends_at__isnull=True),
        )


class TrendingDeal(models.Model):
    """Model for trending deals and offers that appear in the hero deals section."""
    
    class DealType(models.TextChoices):
        PERCENT_OFF = 'PERCENT_OFF', 'Percentage Off'
        CASHBACK = 'CASHBACK', 'Cashback'
        BUY_ONE_GET_ONE = 'BOGO', 'Buy 1 Get 1'
        FLAT_DISCOUNT = 'FLAT_DISCOUNT', 'Flat Discount'
        NEW = 'NEW', 'New Arrival'
        FLASH = 'FLASH', 'Flash Sale'
        DROP = 'DROP', 'New Drop'
    
    deal_type = models.CharField(max_length=20, choices=DealType.choices, default=DealType.NEW)
    label = models.CharField(max_length=100, help_text="Display label like 'NEW • Madara LED Box at ₹699'")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='trending_deals', help_text="Link to specific product")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='trending_deals', help_text="Link to category if deal applies to entire category")
    
    # Offer details
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Percentage discount (e.g., 20.00 for 20%)")
    cashback_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Cashback amount")
    flat_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Flat discount amount")
    
    # Display order and status
    display_order = models.PositiveIntegerField(default=0, help_text="Order in which deals appear (lower numbers first)")
    is_active = models.BooleanField(default=True, help_text="Whether this deal is currently active")
    starts_at = models.DateTimeField(null=True, blank=True, help_text="Go-live datetime for this deal. Leave blank to activate immediately.")
    ends_at = models.DateTimeField(null=True, blank=True, help_text="Optional end datetime. Leave blank for open-ended deals.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TrendingDealQuerySet.as_manager()
    
    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = "Trending Deal"
        verbose_name_plural = "Trending Deals"
    
    def __str__(self):
        return f"{self.get_deal_type_display()} - {self.label}"
    
    def get_target_url(self):
        """Returns the URL to navigate to when deal is clicked."""
        if self.product:
            return f"/shop/{self.product.sku}"
        elif self.category:
            from django.utils.text import slugify
            slug = slugify(self.category.name)
            return f"/shop?category={slug}"
        return "/shop"

    @property
    def is_live(self):
        now = timezone.now()
        if self.starts_at and self.starts_at > now:
            return False
        if self.ends_at and self.ends_at < now:
            return False
        return self.is_active