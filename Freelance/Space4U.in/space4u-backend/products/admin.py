import io
import random
import zipfile
import qrcode
import requests
from django.core.files.base import ContentFile
from django import forms
from django.contrib import admin, messages
from django.db.models import Sum
from django.http import HttpResponse
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.utils.html import format_html
from django.forms import formset_factory, ModelForm
from taggit.models import Tag

from .models import (
    Category,
    Product,
    Batch,
    StockMovement,
    ScrapedProduct,
    ProductImage,
    ProductVariant,
    generate_sku,
    StockAdjustmentReason,
    ProductReview,
    TrendingDeal,
)
from .forms import BatchImportForm, TrendingDealForm

# =============================================================================
# INLINES
# =============================================================================

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Preview'

class BatchInline(admin.TabularInline):
    model = Batch
    extra = 0
    readonly_fields = ('quantity_current', 'batch_code')
    fields = ('batch_code', 'variant', 'quantity_initial', 'quantity_current', 'cost_price', 'received_date')

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    readonly_fields = ('view_details_link',)
    fields = ('name', 'sku', 'price', 'discount_price', 'is_default', 'view_details_link')

    def view_details_link(self, obj):
        if obj.pk:
            url = reverse('admin:products_productvariant_change', args=[obj.pk])
            return format_html('<a href="{}">Manage Stock & Details</a>', url)
        return "Save product to manage variant stock"
    view_details_link.short_description = "Stock Management"

# =============================================================================
# MODEL ADMINS
# =============================================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'image_preview', 'name', 'category', 'has_variants', 'status')
    list_filter = ('status', 'category', 'has_variants', 'tags')
    search_fields = ('name', 'sku')
    list_editable = ('status',)
    readonly_fields = ('image_preview', 'scraped_product_link')
    actions = ['mark_as_published', 'mark_as_draft']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'status', 'tags', 'scraped_product_link')
        }),
        ("Variants", {
            'fields': ('has_variants',),
            'description': "Check this if the product comes in different types (e.g., size, color). Uncheck for single items."
        }),
        ('Single Product Details', {
            'classes': ('single-product-fields',),
            'description': "These fields apply only if 'Has Variants' is NOT checked. They will define the one and only variant.",
            'fields': ('sku', 'price', 'discount_price'),
        }),
        ('Image', {
            'fields': ('image', 'image_preview')
        }),
        ('Details', {
            'fields': ('description',),
        }),
    )

    def get_inlines(self, request, obj):
        if obj and obj.has_variants:
            return [ProductVariantInline, ProductImageInline]
        return [ProductImageInline] # No batch/variant inlines for single products here

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image Preview'

    def scraped_product_link(self, obj):
        if obj.scraped_product:
            link = reverse("admin:products_scrapedproduct_change", args=[obj.scraped_product.id])
            return format_html('<a href="{}">{}</a>', link, obj.scraped_product)
        return "N/A"
    scraped_product_link.short_description = 'Scraped Source'

    class Media:
        js = ("admin/js/product_admin.js",)

    @admin.action(description="Mark selected products as Published")
    def mark_as_published(self, request, queryset):
        updated = queryset.update(status=Product.Status.PUBLISHED)
        self.message_user(request, f"{updated} product(s) marked as published.", messages.SUCCESS)

    @admin.action(description="Mark selected products as Draft")
    def mark_as_draft(self, request, queryset):
        updated = queryset.update(status=Product.Status.DRAFT)
        self.message_user(request, f"{updated} product(s) moved to draft.", messages.SUCCESS)

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'product_link', 'price', 'total_stock', 'reserved', 'available', 'is_default')
    list_filter = ('product__category',)
    search_fields = ('sku', 'name', 'product__name')
    inlines = [BatchInline]
    
    fieldsets = (
        (None, {
            'fields': ('product', 'name', 'sku', 'is_default')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price')
        }),
        ('Attributes', {
            'fields': ('size', 'color')
        }),
        ('Stock Levels (Calculated)', {
            'fields': ('total_stock', 'reserved', 'available'),
        }),
    )
    readonly_fields = ('total_stock', 'reserved', 'available')

    def product_link(self, obj):
        url = reverse('admin:products_product_change', args=[obj.product.pk])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)

    def total_stock(self, obj): return obj.total_stock
    def reserved(self, obj): return obj.reserved
    def available(self, obj): return obj.available

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('batch_code', 'product_link', 'variant_link', 'quantity_current', 'received_date')
    list_filter = ('variant__product__category',)
    search_fields = ('batch_code', 'variant__sku', 'variant__name')
    readonly_fields = ('product_display',)
    actions = ['generate_qr_codes_for_selected']
    
    fieldsets = (
        (None, {
            'fields': ('product_display', 'variant', 'batch_code', 'quantity_initial', 'quantity_current')
        }),
        ('Pricing & Details', {
            'fields': ('cost_price', 'received_date', 'qr_code_generated')
        }),
    )
    
    def product_link(self, obj):
        if obj.variant and obj.variant.product:
            link = reverse("admin:products_product_change", args=[obj.variant.product.id])
            return format_html('<a href="{}">{}</a>', link, obj.variant.product.name)
        return "N/A"
    product_link.short_description = 'Product'
    
    def variant_link(self, obj):
        if obj.variant:
            link = reverse("admin:products_productvariant_change", args=[obj.variant.id])
            return format_html('<a href="{}">{} ({})</a>', link, obj.variant.name, obj.variant.sku)
        return "N/A"
    variant_link.short_description = 'Variant'
    
    def product_display(self, obj):
        if obj.variant and obj.variant.product:
            link = reverse("admin:products_product_change", args=[obj.variant.product.id])
            return format_html('<strong><a href="{}">{}</a></strong>', link, obj.variant.product.name)
        return "N/A"
    product_display.short_description = 'Product'
    
    @admin.action(description='Generate QR codes for selected batches')
    def generate_qr_codes_for_selected(self, request, queryset):
        in_memory_zip = io.BytesIO()
        with zipfile.ZipFile(in_memory_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for batch in queryset:
                qr_url = request.build_absolute_uri(reverse('core:qr_redirect', args=[batch.batch_code]))
                img = qrcode.make(qr_url)
                
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                zf.writestr(f'{batch.batch_code}.png', img_buffer.read())
        
        in_memory_zip.seek(0)
        queryset.update(qr_code_generated=True)
        
        response = HttpResponse(in_memory_zip.read(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="qr_codes.zip"'
        return response


@admin.register(StockAdjustmentReason)
class StockAdjustmentReasonAdmin(admin.ModelAdmin):
    list_display = ('reason',)
    search_fields = ('reason',)

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'batch_link', 'change', 'user', 'reason')
    list_filter = ('batch__variant__product', 'reason')
    search_fields = ('batch__batch_code', 'reason__reason', 'notes')
    
    def batch_link(self, obj):
        link = reverse("admin:products_batch_change", args=[obj.batch.id])
        return format_html('<a href="{}">{}</a>', link, obj.batch.batch_code)
    batch_link.short_description = 'Batch'
    
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(ScrapedProduct)
class ScrapedProductAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'name', 'source_site', 'price', 'imported', 'updated_at')
    list_filter = ('source_site', 'imported')
    search_fields = ('name', 'source_url')
    actions = ['import_selected_products']

    def image_preview(self, obj):
        if obj.image_urls:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image_urls[0])
        return "No Image"
    image_preview.short_description = 'Image Preview'

    @admin.action(description='Import selected items as new products')
    def import_selected_products(self, request, queryset):
        selected_pks = list(queryset.values_list('pk', flat=True))
        request.session['selected_scraped_products'] = selected_pks
        return redirect(reverse('admin:import-scraped-products'))

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-scraped/', self.admin_site.admin_view(self.import_view), name='import-scraped-products'),
        ]
        return custom_urls + urls

    def import_view(self, request):
        selected_pks = request.session.get('selected_scraped_products', [])
        scraped_products = ScrapedProduct.objects.filter(pk__in=selected_pks, imported=False)

        if not scraped_products:
            self.message_user(request, "No products selected or they have already been imported.", messages.WARNING)
            return redirect("admin:products_scrapedproduct_changelist")

        BatchImportFormSet = formset_factory(BatchImportForm, extra=0)

        available_categories = list(Category.objects.all())
        available_tag_names = list(Tag.objects.values_list('name', flat=True))

        def get_random_category():
            return random.choice(available_categories) if available_categories else None

        def build_random_tags(scraped_product):
            candidate_tags = []
            if isinstance(scraped_product.tags, (list, tuple)):
                candidate_tags.extend(
                    [tag for tag in scraped_product.tags if isinstance(tag, str) and tag.strip()]
                )
            candidate_tags.extend([tag for tag in available_tag_names if tag])

            # De-duplicate while keeping order
            seen = set()
            unique_candidates = []
            for tag in candidate_tags:
                if tag not in seen:
                    seen.add(tag)
                    unique_candidates.append(tag)

            if not unique_candidates:
                return []

            sample_size = min(len(unique_candidates), random.randint(1, min(3, len(unique_candidates))))
            return random.sample(unique_candidates, sample_size)

        if request.method == 'POST':
            formset = BatchImportFormSet(request.POST)
            if formset.is_valid():
                imported_count = 0
                for scraped_product, form_data in zip(scraped_products, formset.cleaned_data):
                    selected_category = form_data.get('category') or get_random_category()
                    quantity = form_data.get('quantity_initial')
                    if not quantity or quantity <= 0:
                        quantity = random.randint(1, 30)

                    tags_str = form_data.get('tags')
                    if not tags_str:
                        random_tags = build_random_tags(scraped_product)
                        tags_str = ', '.join(random_tags)

                    product = Product.objects.create(
                        name=scraped_product.name,
                        description=scraped_product.description,
                        sku=generate_sku(scraped_product.name, scraped_product.source_site),
                        price=scraped_product.price or 0.00,
                        status='DRAFT',
                        category=selected_category,
                        has_variants=False, # Scraped products are single-variant by default
                        scraped_product=scraped_product
                    )
                    
                    if tags_str:
                        product.tags.add(*[tag.strip() for tag in tags_str.split(',') if tag.strip()])

                    if scraped_product.image_urls:
                        try:
                            # Download the first image as the primary image, rest as additional images
                            import requests
                            from django.core.files.base import ContentFile
                            from .models import ProductImage

                            def fetch_image(url: str) -> ContentFile:
                                resp = requests.get(url, timeout=15)
                                resp.raise_for_status()
                                # derive a simple filename from the URL tail
                                filename = url.split('/')[-1].split('?')[0] or 'image.jpg'
                                return filename, ContentFile(resp.content)

                            urls = [u for u in (scraped_product.image_urls or []) if isinstance(u, str) and u.strip()]
                            if urls:
                                # Primary image
                                fname, fileobj = fetch_image(urls[0])
                                product.image.save(fname, fileobj, save=True)

                                # Additional images
                                for extra_url in urls[1:]:
                                    try:
                                        ename, efile = fetch_image(extra_url)
                                        pi = ProductImage(product=product)
                                        pi.image.save(ename, efile, save=True)
                                    except Exception:
                                        # Skip bad extra images; continue import
                                        continue
                        except Exception as e:
                            self.message_user(request, f"Could not download image for {product.name}: {e}", messages.WARNING)

                    if quantity and quantity > 0:
                        # The Product.save() method automatically creates a default variant. Find it.
                        default_variant = product.variants.filter(is_default=True).first()
                        if default_variant:
                            Batch.objects.create(
                                variant=default_variant, # Link batch to the variant
                                quantity_initial=quantity,
                                cost_price=form_data.get('cost_price') or 0.00,
                                received_date=form_data['received_date']
                            )
                    
                    scraped_product.imported = True
                    scraped_product.save()
                    imported_count += 1
                
                self.message_user(request, f"Successfully imported {imported_count} new products.", messages.SUCCESS)
                return redirect("admin:products_scrapedproduct_changelist")
        else:
            initial_data = []
            for scraped_product in scraped_products:
                category = get_random_category()
                random_quantity = random.randint(1, 30)
                random_tags = build_random_tags(scraped_product)

                initial_data.append({
                    'cost_price': scraped_product.price or 0.00,
                    'tags': ', '.join(random_tags),
                    'quantity_initial': random_quantity,
                    'category': category,
                })
            formset = BatchImportFormSet(initial=initial_data)

        context = self.admin_site.each_context(request)
        context.update({
            'opts': self.model._meta,
            'title': 'Import Batch Details',
            'items_with_forms': zip(scraped_products, formset),
            'formset': formset,
        })
        return render(request, 'admin/import_scraped_products.html', context)

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('product__name', 'user__username', 'title', 'body')

@admin.register(TrendingDeal)
class TrendingDealAdmin(admin.ModelAdmin):
    form = TrendingDealForm
    
    list_display = ('label', 'deal_type', 'product', 'category', 'display_order', 'is_active', 'starts_at', 'ends_at')
    list_filter = ('deal_type', 'is_active', 'category')
    search_fields = ('label', 'product__name', 'category__name')
    list_editable = ('display_order', 'is_active')
    fieldsets = (
        (None, {
            'fields': ('deal_type', 'label', 'is_active', 'display_order')
        }),
        ('Schedule', {
            'fields': ('starts_at', 'ends_at'),
            'description': 'Use these fields to control when the deal is visible. Leave blank for immediate or open-ended deals.'
        }),
        ('Target', {
            'fields': ('product', 'category'),
            'description': 'Select either a specific product OR a category. If both are selected, product takes priority.'
        }),
        ('Offer Details', {
            'fields': ('discount_percent', 'cashback_amount', 'flat_discount_amount'),
            'description': 'Fill in the relevant fields based on the deal type. Maximum discount is 60%.'
        }),
    )
    date_hierarchy = 'starts_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'category')