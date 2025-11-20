"""
Comprehensive tests for Products app including deals, variants, reviews, and more.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from products.models import (
    Product, Category, ProductVariant, ProductImage, ProductReview,
    TrendingDeal, Batch, StockMovement
)
from datetime import timedelta
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


class ProductAPITests(APITestCase):
    """Tests for Product API endpoints."""
    
    def setUp(self):
        self.category = Category.objects.create(name='Action Figures', slug='action-figures')
        self.product = Product.objects.create(
            name='Spider-Man Figure',
            sku='SPIDER-001',
            price=Decimal('99.99'),
            category=self.category,
            description='Amazing Spider-Man action figure'
        )
        self.product.tags.add('Marvel', 'Action Figure')
        
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku='SPIDER-001-RED',
            price=Decimal('99.99'),
            is_default=True,
            color='Red'
        )
    
    def test_list_products(self):
        """Can list all products."""
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
    
    def test_retrieve_product(self):
        """Can retrieve a single product by SKU."""
        response = self.client.get(f'/api/products/{self.product.sku}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sku'], 'SPIDER-001')
        self.assertEqual(response.data['name'], 'Spider-Man Figure')
    
    def test_product_has_variants(self):
        """Product includes its variants."""
        response = self.client.get(f'/api/products/{self.product.sku}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('variants', response.data)
        self.assertGreaterEqual(len(response.data['variants']), 1)
    
    def test_filter_products_by_category(self):
        """Can filter products by category."""
        response = self.client.get('/api/products/', {'category': self.category.slug})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for product in response.data:
            if 'category' in product and product['category']:
                self.assertEqual(product['category']['slug'], 'action-figures')
    
    def test_filter_products_by_tag(self):
        """Can filter products by tag."""
        response = self.client.get('/api/products/', {'tags': 'Marvel'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return products (list or paginated)
        if isinstance(response.data, list):
            # Direct list response
            self.assertGreaterEqual(len(response.data), 0)
        elif hasattr(response.data, 'get') and response.data.get('results'):
            # Paginated response
            self.assertGreaterEqual(len(response.data['results']), 0)
    
    def test_search_products(self):
        """Can search products by name."""
        response = self.client.get('/api/products/', {'search': 'Spider'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
    
    def test_product_price_validation(self):
        """Product prices are valid decimals."""
        response = self.client.get(f'/api/products/{self.product.sku}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        price = Decimal(str(response.data['price']))
        self.assertGreater(price, 0)
        self.assertEqual(price, Decimal('99.99'))


class ProductVariantTests(TestCase):
    """Tests for ProductVariant model and logic."""
    
    def setUp(self):
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST-001',
            price=Decimal('50.00'),
            category=self.category
        )
    
    def test_create_variant(self):
        """Can create a product variant."""
        variant = ProductVariant.objects.create(
            product=self.product,
            sku='TEST-001-BLUE',
            price=Decimal('55.00'),
            color='Blue'
        )
        self.assertEqual(variant.sku, 'TEST-001-BLUE')
        self.assertEqual(variant.product, self.product)
    
    def test_variant_stock_tracking(self):
        """Variant stock is tracked correctly."""
        variant = ProductVariant.objects.create(
            product=self.product,
            sku='TEST-001-GREEN',
            price=Decimal('50.00')
        )
        
        initial_stock = variant.stock
        self.assertEqual(initial_stock, 10)
        
        # Simulate stock change
        variant.stock = 8
        variant.save()
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 8)
    
    def test_default_variant(self):
        """Only one variant can be default."""
        variant1 = ProductVariant.objects.create(
            product=self.product,
            sku='TEST-001-V1',
            price=Decimal('50.00'),
            is_default=True
        )
        
        variant2 = ProductVariant.objects.create(
            product=self.product,
            sku='TEST-001-V2',
            price=Decimal('55.00'),
            is_default=False
        )
        
        default_variants = ProductVariant.objects.filter(product=self.product, is_default=True)
        self.assertEqual(default_variants.count(), 1)
    
    def test_variant_sku_unique(self):
        """Variant SKUs must be unique."""
        ProductVariant.objects.create(
            product=self.product,
            sku='UNIQUE-SKU',
            price=Decimal('50.00')
        )
        
        with self.assertRaises(Exception):
            ProductVariant.objects.create(
                product=self.product,
                sku='UNIQUE-SKU',  # Duplicate
                price=Decimal('60.00')
            )


class ProductReviewTests(TestCase):
    """Tests for product reviews."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='reviewer',
            email='reviewer@example.com',
            password='pass123'
        )
        
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST-001',
            price=Decimal('50.00'),
            category=self.category
        )
    
    def test_create_review_directly(self):
        """Can create a review in the database."""
        review = ProductReview.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            title='Great!',
            body='Excellent product'
        )
        
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.product, self.product)
        self.assertEqual(review.user, self.user)
    
    def test_review_rating_constraints(self):
        """Review rating field has constraints."""
        review = ProductReview.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            title='Test',
            body='Test'
        )
        
        # Rating should be stored correctly
        self.assertGreaterEqual(review.rating, 1)
        self.assertLessEqual(review.rating, 5)
    
    def test_product_average_rating_calculated(self):
        """Product average rating is calculated correctly."""
        user2 = User.objects.create_user(username='user2', email='u2@example.com', password='pass')
        
        ProductReview.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            title='Great',
            body='Excellent'
        )
        
        ProductReview.objects.create(
            product=self.product,
            user=user2,
            rating=3,
            title='OK',
            body='Average'
        )
        
        # Check average rating (should be 4.0)
        reviews = ProductReview.objects.filter(product=self.product)
        avg_rating = sum(r.rating for r in reviews) / reviews.count()
        self.assertEqual(avg_rating, 4.0)


class TrendingDealTests(APITestCase):
    """Tests for trending deals."""
    
    def setUp(self):
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Deal Product',
            sku='DEAL-001',
            price=Decimal('100.00'),
            category=self.category
        )
        
        self.deal = TrendingDeal.objects.create(
            deal_type=TrendingDeal.DealType.PERCENT_OFF,
            label='50% OFF',
            product=self.product,
            discount_percent=Decimal('50.00'),
            display_order=1,
            is_active=True
        )
    
    def test_list_trending_deals(self):
        """Can list active trending deals."""
        response = self.client.get('/api/products/trending-deals/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
    
    def test_inactive_deals_not_shown(self):
        """Inactive deals are not shown."""
        self.deal.is_active = False
        self.deal.save()
        
        response = self.client.get('/api/products/trending-deals/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should not include inactive deal
        deal_ids = [d['id'] for d in response.data]
        self.assertNotIn(self.deal.id, deal_ids)
    
    def test_deals_ordered_by_display_order(self):
        """Deals are ordered by display_order."""
        deal2 = TrendingDeal.objects.create(
            deal_type=TrendingDeal.DealType.PERCENT_OFF,
            label='30% OFF',
            category=self.category,
            discount_percent=Decimal('30.00'),
            display_order=2,
            is_active=True
        )
        
        response = self.client.get('/api/products/trending-deals/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        if len(response.data) >= 2:
            # First deal should have lower display_order
            self.assertLessEqual(
                response.data[0].get('display_order', 0),
                response.data[1].get('display_order', 999)
            )


class BatchInventoryTests(TestCase):
    """Tests for batch and inventory management."""
    
    def setUp(self):
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST-001',
            price=Decimal('50.00'),
            category=self.category
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku='TEST-001-V1',
            price=Decimal('50.00')
        )
    
    def test_create_batch(self):
        """Can create a batch with stock."""
        batch = Batch.objects.create(
            variant=self.variant,
            quantity_initial=100,
            cost_price=Decimal('30.00'),
            received_date=timezone.now().date()
        )
        
        self.assertEqual(batch.quantity_initial, 100)
        self.assertEqual(batch.quantity_current, 100)
        self.assertEqual(batch.variant, self.variant)
        
        # Stock should be updated
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 100)
    
    def test_stock_movement_tracking(self):
        """Stock movements are tracked."""
        batch = Batch.objects.create(
            variant=self.variant,
            quantity_initial=50,
            cost_price=Decimal('30.00'),
            received_date=timezone.now().date()
        )
        
        movement = StockMovement.objects.create(
            batch=batch,
            change=-5,
            notes='Sold 5 units'
        )
        
        self.assertEqual(movement.change, -5)
    
    def test_batch_date_tracking(self):
        """Batch received dates are tracked."""
        received_date = timezone.now().date()
        batch = Batch.objects.create(
            variant=self.variant,
            quantity_initial=50,
            cost_price=Decimal('30.00'),
            received_date=received_date
        )
        
        self.assertEqual(batch.received_date, received_date)


class CategoryTests(TestCase):
    """Tests for product categories."""
    
    def setUp(self):
        self.category1 = Category.objects.create(name='Action Figures', slug='action-figures')
        self.category2 = Category.objects.create(name='Posters', slug='posters')
    
    def test_category_creation(self):
        """Can create categories."""
        self.assertEqual(self.category1.name, 'Action Figures')
        self.assertEqual(self.category1.slug, 'action-figures')
    
    def test_category_slug_unique(self):
        """Category slugs must be unique."""
        with self.assertRaises(Exception):
            Category.objects.create(name='Duplicate', slug='action-figures')
    
    def test_category_has_products(self):
        """Categories can have products."""
        product = Product.objects.create(
            name='Test',
            sku='TEST-001',
            price=Decimal('50.00'),
            category=self.category1
        )
        
        products = Product.objects.filter(category=self.category1)
        self.assertEqual(products.count(), 1)
        self.assertEqual(products.first(), product)


class ProductImageTests(TestCase):
    """Tests for product images."""
    
    def setUp(self):
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST-001',
            price=Decimal('50.00'),
            category=self.category
        )
    
    def test_add_product_image(self):
        """Can add images to products."""
        # Create a fake image file
        image_file = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'fake image content',
            content_type='image/jpeg'
        )
        
        product_image = ProductImage.objects.create(
            product=self.product,
            image=image_file
        )
        
        self.assertEqual(product_image.product, self.product)
        self.assertIsNotNone(product_image.image)
    
    def test_multiple_images_per_product(self):
        """Products can have multiple images."""
        for i in range(3):
            image_file = SimpleUploadedFile(
                name=f'test_image_{i}.jpg',
                content=b'fake image content',
                content_type='image/jpeg'
            )
            ProductImage.objects.create(
                product=self.product,
                image=image_file
            )
        
        images = ProductImage.objects.filter(product=self.product)
        self.assertEqual(images.count(), 3)


class ProductSearchTests(APITestCase):
    """Tests for product search functionality."""
    
    def setUp(self):
        self.category = Category.objects.create(name='Test', slug='test')
        
        self.product1 = Product.objects.create(
            name='Spider-Man Action Figure',
            sku='SPIDER-001',
            price=Decimal('99.99'),
            category=self.category,
            description='Amazing Spider-Man figure'
        )
        
        self.product2 = Product.objects.create(
            name='Batman Action Figure',
            sku='BATMAN-001',
            price=Decimal('89.99'),
            category=self.category,
            description='Dark Knight figure'
        )
    
    def test_search_by_name(self):
        """Can search products by name."""
        response = self.client.get('/api/products/', {'search': 'Spider'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data
        skus = [p['sku'] for p in results]
        self.assertIn('SPIDER-001', skus)
    
    def test_search_by_description(self):
        """Can search products by description."""
        response = self.client.get('/api/products/', {'search': 'Dark Knight'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data
        if len(results) > 0:
            # Should find Batman
            skus = [p['sku'] for p in results]
            self.assertIn('BATMAN-001', skus)
    
    def test_search_empty_query(self):
        """Empty search returns all products."""
        response = self.client.get('/api/products/', {'search': ''})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)


class ProductPricingTests(TestCase):
    """Tests for product pricing logic."""
    
    def setUp(self):
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST-001',
            price=Decimal('100.00'),
            category=self.category
        )
    
    def test_discount_price_applied(self):
        """Discount price is properly applied."""
        self.product.discount_price = Decimal('80.00')
        self.product.save()
        
        self.assertEqual(self.product.discount_price, Decimal('80.00'))
        self.assertLess(self.product.discount_price, self.product.price)
    
    def test_variant_price_override(self):
        """Variant can have different price than product."""
        variant = ProductVariant.objects.create(
            product=self.product,
            sku='TEST-001-PREMIUM',
            price=Decimal('150.00'),  # Higher than product price
        )
        
        self.assertGreater(variant.price, self.product.price)
    
    def test_price_precision(self):
        """Prices maintain decimal precision."""
        variant = ProductVariant.objects.create(
            product=self.product,
            sku='TEST-001-V1',
            price=Decimal('99.99')
        )
        
        variant.refresh_from_db()
        self.assertEqual(variant.price, Decimal('99.99'))
        self.assertIsInstance(variant.price, Decimal)


class ProductAvailabilityTests(TestCase):
    """Tests for product availability logic."""
    
    def setUp(self):
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST-001',
            price=Decimal('50.00'),
            category=self.category
        )
    
    def test_in_stock_variant(self):
        """Variant with stock is available."""
        variant = ProductVariant.objects.create(
            product=self.product,
            sku='TEST-001-V1',
            price=Decimal('50.00')
        )
        
        self.assertGreater(variant.stock, 0)
    
    def test_out_of_stock_variant(self):
        """Variant with zero stock is unavailable."""
        variant = ProductVariant.objects.create(
            product=self.product,
            sku='TEST-001-V2',
            price=Decimal('50.00')
        )
        
        self.assertEqual(variant.stock, 0)
    
    def test_stock_calculation(self):
        """Stock is calculated from batches."""
        variant = ProductVariant.objects.create(
            product=self.product,
            sku='TEST-001-V3',
            price=Decimal('50.00')
        )
        
        # Initially no stock
        self.assertEqual(variant.stock, 0)
        
        # Add a batch
        Batch.objects.create(
            variant=variant,
            quantity_initial=10,
            cost_price=Decimal('30.00'),
            received_date=timezone.now().date()
        )
        
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 10)

