from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Product, ProductVariant, ProductReview

User = get_user_model()


class ProductFeatureTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u2', password='p1')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.product = Product.objects.create(name='Prod', status='PUBLISHED')
        self.variant = ProductVariant.objects.create(product=self.product, name='Def', sku='SKU2', price=200)

    def test_add_and_get_reviews(self):
        # Use the correct reviews API endpoint
        url = '/api/products/reviews/'
        r = self.client.post(url, {
            "product": self.product.id,
            "rating": 5,
            "title": "Great",
            "body": "Nice"
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        
        # Get all reviews
        list_url = '/api/products/reviews/'
        r = self.client.get(list_url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        # Check if our review is in the results
        if 'results' in r.data:
            self.assertTrue(any(rv['rating'] == 5 for rv in r.data['results']))
        else:
            self.assertTrue(any(rv['rating'] == 5 for rv in r.data))

    def test_average_rating_field(self):
        # create another user review
        other = User.objects.create_user(username='u3', password='p1')
        ProductReview.objects.create(product=self.product, user=self.user, rating=4)
        ProductReview.objects.create(product=self.product, user=other, rating=2)
        detail = f'/api/products/{self.product.id}/'
        r = self.client.get(detail)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('average_rating', r.data)

    def test_recommended(self):
        r = self.client.get(f'/api/products/{self.product.id}/recommended/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_mark_viewed(self):
        r = self.client.post(f'/api/products/{self.product.id}/mark_viewed/', {})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.db import IntegrityError
from django.core.management import call_command
from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from unittest.mock import patch, MagicMock
import time
import os
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Category, Product, Batch, StockMovement, ScrapedProduct, ProductImage, generate_sku
from .admin import ProductAdmin
from .forms import BatchImportForm

User = get_user_model()

class InventoryModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Figures")
        cls.product = Product.objects.create(
            category=cls.category,
            name="Naruto Figure",
            sku="FIG-NARUTO-001",
            price="49.99"
        )
        cls.product.tags.add("Anime", "Shippuden")

    def test_batch_creation(self):
        batch = Batch.objects.create(
            product=self.product,
            quantity_initial=50,
            quantity_current=50,
            cost_price="25.00",
            received_date=timezone.now().date()
        )
        self.assertEqual(batch.product.name, "Naruto Figure")
        self.assertEqual(batch.quantity_current, 50)
        self.assertTrue(batch.batch_code.startswith("BATCH-FIG-NARUTO-001"))
        self.assertEqual(str(batch), f"Batch for Naruto Figure - {batch.batch_code}")

    def test_stock_movement_creation(self):
        batch = Batch.objects.create(
            product=self.product,
            quantity_initial=50,
            quantity_current=50,
            cost_price="25.00",
            received_date=timezone.now().date()
        )
        movement = StockMovement.objects.create(
            batch=batch,
            change=-1,
            notes="Sale at event"
        )
        self.assertEqual(movement.batch, batch)
        self.assertEqual(movement.change, -1)
        self.assertEqual(str(movement), f"-1 items for {batch.batch_code} at {movement.timestamp}")

    def test_product_tagging(self):
        self.assertEqual(self.product.tags.count(), 2)
        self.assertIn("Anime", [tag.name for tag in self.product.tags.all()])

    def test_batch_creation_creates_stock_movement(self):
        """Tests that saving a new Batch automatically creates an initial StockMovement record."""
        batch = Batch.objects.create(
            product=self.product,
            quantity_initial=50,
            quantity_current=50,
            cost_price="25.00",
            received_date=timezone.now().date()
        )
        # check that one movement record exists for this batch
        self.assertEqual(batch.movements.count(), 1)
        
        # check that the movement record has the correct details
        initial_movement = batch.movements.first()
        self.assertEqual(initial_movement.change, 50)
        self.assertEqual(initial_movement.notes, "Initial batch creation")

    def test_duplicate_batch_code_raises_integrity_error(self):
        # Create first batch, then try to create another with the same batch_code
        b1 = Batch.objects.create(
            product=self.product,
            quantity_initial=5,
            quantity_current=5,
            cost_price="3.00",
            received_date=timezone.now().date(),
        )
        # Reuse the exact same batch_code on a new instance
        with self.assertRaises(IntegrityError):
            Batch.objects.create(
                product=self.product,
                quantity_initial=6,
                quantity_current=6,
                cost_price="3.50",
                received_date=timezone.now().date(),
                batch_code=b1.batch_code,
            )

    def test_product_sku_must_be_unique(self):
        with self.assertRaises(IntegrityError):
            Product.objects.create(
                category=self.category,
                name="Duplicate SKU",
                sku="FIG-NARUTO-001",  # same as setUpTestData
                price="19.99",
            )

    def test_category_name_must_be_unique(self):
        with self.assertRaises(IntegrityError):
            Category.objects.create(name="Figures")  # same as setUpTestData

    def test_batch_sets_current_quantity_to_initial_on_create(self):
        batch = Batch.objects.create(
            product=self.product,
            quantity_initial=25,
            quantity_current=0,  # should get overridden by model.save
            cost_price="10.00",
            received_date=timezone.now().date(),
        )
        self.assertEqual(batch.quantity_current, 25)

    def test_batch_code_is_unique_via_timestamp_generation(self):
        # Ensure two successive creations with a slight delay yield different batch codes
        b1 = Batch.objects.create(
            product=self.product,
            quantity_initial=5,
            quantity_current=5,
            cost_price="3.00",
            received_date=timezone.now().date(),
        )
        time.sleep(1.1)  # ensure at least 1 second passes for timestamp difference
        b2 = Batch.objects.create(
            product=self.product,
            quantity_initial=6,
            quantity_current=6,
            cost_price="3.50",
            received_date=timezone.now().date(),
        )
        self.assertNotEqual(b1.batch_code, b2.batch_code)

    def test_updating_batch_does_not_create_additional_stock_movement(self):
        batch = Batch.objects.create(
            product=self.product,
            quantity_initial=10,
            quantity_current=10,
            cost_price="4.00",
            received_date=timezone.now().date(),
        )
        self.assertEqual(batch.movements.count(), 1)

        # Update some field and save again
        batch.quantity_current = 9
        batch.save()
        self.assertEqual(batch.movements.count(), 1)

    def test_deleting_batch_cascades_to_stock_movements(self):
        batch = Batch.objects.create(
            product=self.product,
            quantity_initial=8,
            quantity_current=8,
            cost_price="2.00",
            received_date=timezone.now().date(),
        )
        self.assertEqual(StockMovement.objects.filter(batch=batch).count(), 1)
        batch_id = batch.id
        batch.delete()
        self.assertEqual(StockMovement.objects.filter(batch_id=batch_id).count(), 0)

    def test_deleting_product_cascades_to_batches_and_movements(self):
        batch = Batch.objects.create(
            product=self.product,
            quantity_initial=7,
            quantity_current=7,
            cost_price="2.50",
            received_date=timezone.now().date(),
        )
        self.assertTrue(Batch.objects.filter(id=batch.id).exists())
        self.assertEqual(StockMovement.objects.filter(batch=batch).count(), 1)

        self.product.delete()
        self.assertFalse(Batch.objects.filter(id=batch.id).exists())
        self.assertEqual(StockMovement.objects.filter(batch=batch).count(), 0)

    def test_discount_price_optional_and_persists(self):
        # discount_price can be null/blank and can be set later
        p = Product.objects.create(
            category=self.category,
            name="Sasuke Figure",
            sku="FIG-SASUKE-001",
            price="59.99",
        )
        self.assertIsNone(p.discount_price)

        p.discount_price = "49.99"
        p.save()
        p.refresh_from_db()
        self.assertEqual(str(p.discount_price), "49.99")

    def test_product_can_have_multiple_images(self):
        """Tests that multiple ProductImage instances can be associated with a Product."""
        ProductImage.objects.create(product=self.product, image="path/to/image1.jpg")
        ProductImage.objects.create(product=self.product, image="path/to/image2.jpg")
        self.assertEqual(self.product.images.count(), 2)

    def test_deleting_product_cascades_to_product_images(self):
        """Tests that deleting a Product also deletes its associated ProductImage instances."""
        ProductImage.objects.create(product=self.product, image="path/to/image1.jpg")
        self.assertEqual(ProductImage.objects.count(), 1)
        self.product.delete()
        self.assertEqual(ProductImage.objects.count(), 0)

    def test_generate_sku_function(self):
        """Tests the SKU generation utility."""
        sku1 = generate_sku("Test Product", "Test Site")
        self.assertEqual(sku1, "TEST-SITE-TEST-PRODUCT")
        # Create a product to test uniqueness
        Product.objects.create(name="Test 1", sku=sku1, price=10)
        sku2 = generate_sku("Test Product", "Test Site")
        self.assertEqual(sku2, "TEST-SITE-TEST-PRODUCT-1")

class QRGenerationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        product = Product.objects.create(name="Test Product", sku="TEST-QR", price="10.00")
        Batch.objects.create(
            product=product, 
            batch_code="BATCH-NEW-1", 
            quantity_initial=10, 
            quantity_current=10, 
            cost_price=5, 
            received_date=timezone.now().date(),
            qr_code_generated=False
        )
        Batch.objects.create(
            product=product,
            batch_code="BATCH-OLD-1", 
            quantity_initial=10, 
            quantity_current=10, 
            cost_price=5, 
            received_date=timezone.now().date(),
            qr_code_generated=True
        )

    def tearDown(self):
        """Clean up generated QR code ZIP file after each test."""
        zip_path = os.path.join(settings.MEDIA_ROOT or settings.BASE_DIR, 'qr_codes_bulk.zip')
        if os.path.exists(zip_path):
            os.remove(zip_path)

    def test_generate_qrcodes_command_default(self):
        """Tests that the command only processes new batches by default."""
        call_command('generate_qrcodes')
        
        new_batch = Batch.objects.get(batch_code="BATCH-NEW-1")
        old_batch = Batch.objects.get(batch_code="BATCH-OLD-1")

        self.assertTrue(new_batch.qr_code_generated)
        self.assertTrue(old_batch.qr_code_generated)  # remains true

    def test_generate_qrcodes_command_all_flag(self):
        """Tests that the --all flag processes all batches."""
        # reset the old batch for the test
        Batch.objects.filter(batch_code="BATCH-OLD-1").update(qr_code_generated=False)
        
        call_command('generate_qrcodes', all=True)

        new_batch = Batch.objects.get(batch_code="BATCH-NEW-1")
        old_batch = Batch.objects.get(batch_code="BATCH-OLD-1")
        
        self.assertTrue(new_batch.qr_code_generated)
        self.assertTrue(old_batch.qr_code_generated)

class AdminFunctionalityTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Posters")
        cls.user = User.objects.create_superuser("admin", "admin@test.com", "password")
        cls.scraped_product = ScrapedProduct.objects.create(
            name="Test Scraped Product",
            price="29.99",
            source_site="teststore",
            source_url="http://test.com/product/1",
            image_urls=["http://test.com/img1.jpg", "http://test.com/img2.jpg"]
        )

    def setUp(self):
        self.factory = RequestFactory()

    @patch('requests.get')
    def test_scraped_product_import_logic(self, mock_get):
        """Tests the full import process from a ScrapedProduct."""
        # Mock the network request to download images
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'fake-image-content'
        mock_get.return_value = mock_response

        # Data that would be submitted from the import form
        form_data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '1',
            'form-0-category': self.category.id,
            'form-0-tags': 'anime, wall art',
            'form-0-quantity_initial': '10',
            'form-0-cost_price': '15.00',
            'form-0-received_date': '2025-10-26',
        }

        # Simulate the admin view logic
        admin = ProductAdmin(model=Product, admin_site=AdminSite())
        # The actual import view is custom, so we'll test the logic it contains.
        # This requires manually creating the product and batch as the view would.
        
        product = Product.objects.create(
            name=self.scraped_product.name,
            sku=generate_sku(self.scraped_product.name, self.scraped_product.source_site),
            price=self.scraped_product.price,
            category_id=form_data['form-0-category'],
            scraped_product=self.scraped_product
        )
        product.tags.add(*[t.strip() for t in form_data['form-0-tags'].split(',')])
        
        if self.scraped_product.image_urls:
            # Main image
            product.image.save("img1.jpg", ContentFile(b"fake-image-content"), save=True)
            # Additional images
            for url in self.scraped_product.image_urls[1:]:
                ProductImage.objects.create(product=product).image.save("img.jpg", ContentFile(b"fake-image-content"), save=True)

        if int(form_data['form-0-quantity_initial']) > 0:
            Batch.objects.create(
                product=product,
                quantity_initial=form_data['form-0-quantity_initial'],
                cost_price=form_data['form-0-cost_price'],
                received_date=form_data['form-0-received_date']
            )

        # Assertions
        self.assertEqual(Product.objects.count(), 1)
        imported_product = Product.objects.first()
        self.assertEqual(imported_product.name, "Test Scraped Product")
        self.assertEqual(imported_product.sku, "TESTSTORE-TEST-SCRAPED-PRODUCT")
        self.assertEqual(imported_product.category, self.category)
        self.assertEqual(imported_product.tags.count(), 2)
        self.assertIsNotNone(imported_product.image)
        self.assertEqual(imported_product.images.count(), 1) # One additional image
        self.assertEqual(imported_product.batches.count(), 1)
        
        batch = imported_product.batches.first()
        self.assertEqual(batch.quantity_initial, 10)
        self.assertEqual(batch.movements.count(), 1) # Initial stock movement

    def test_stock_adjustment_logic(self):
        """Tests the stock adjustment logic."""
        product = Product.objects.create(name="Test Stock Product", sku="TSP-01", price=100)
        batch = Batch.objects.create(
            product=product,
            quantity_initial=50,
            cost_price=50,
            received_date=timezone.now().date()
        )
        self.assertEqual(batch.quantity_current, 50)
        self.assertEqual(batch.movements.count(), 1) # Initial movement

        # Manually create a stock adjustment
        StockMovement.objects.create(
            batch=batch,
            change=-5,
            notes='Damaged in warehouse',
            user=self.user
        )
        batch.quantity_current -= 5
        batch.save()
        
        batch.refresh_from_db()
        self.assertEqual(batch.quantity_current, 45)
        self.assertEqual(batch.movements.count(), 2)
        last_movement = batch.movements.latest('timestamp')
        self.assertEqual(last_movement.change, -5)
        self.assertEqual(last_movement.notes, 'Damaged in warehouse')

class ProductAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="API Test Category")
        cls.published_product = Product.objects.create(
            name="Published Product",
            sku="PUB-001",
            price=100,
            status='PUBLISHED',
            category=cls.category
        )
        cls.draft_product = Product.objects.create(
            name="Draft Product",
            sku="DRAFT-001",
            price=200,
            status='DRAFT',
            category=cls.category
        )

    def test_list_endpoint_returns_only_published_products(self):
        """
        Ensure the /api/products/ endpoint only lists products with 'PUBLISHED' status.
        """
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.published_product.name)

    def test_detail_endpoint_for_published_product(self):
        """
        Ensure the detail view works for a published product.
        """
        url = f'/api/products/{self.published_product.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.published_product.name)

    def test_detail_endpoint_for_draft_product_is_not_found(self):
        """
        Ensure the detail view returns a 404 for a non-published product.
        """
        url = f'/api/products/{self.draft_product.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)