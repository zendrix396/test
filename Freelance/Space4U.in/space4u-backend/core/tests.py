from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from products.models import Product, Category, Batch

class QRRedirectViewTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.staff_user = User.objects.create_superuser('admin', 'admin@test.com', 'password')
        self.customer_user = User.objects.create_user('customer', 'customer@test.com', 'password')
        
        category = Category.objects.create(name="Figures")
        product = Product.objects.create(category=category, name="Goku Figure", sku="FIG-GOKU-001", price="59.99")
        self.batch = Batch.objects.create(
            product=product,
            quantity_initial=10,
            quantity_current=10,
            cost_price="30.00",
            received_date=timezone.now().date(),
            batch_code="TEST-BATCH-001"
        )
        self.url = reverse('core:qr_redirect', kwargs={'batch_code': 'TEST-BATCH-001'})

    def test_redirect_for_staff_user(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        
        expected_admin_url = reverse('admin:products_product_change', args=[self.batch.product.id])
        
        self.assertRedirects(response, expected_admin_url, fetch_redirect_response=False)

    def test_redirect_for_customer(self):
        self.client.login(username='customer', password='password')
        response = self.client.get(self.url)
        
        expected_frontend_url = f"https://space4u.in/products/{self.batch.product.sku}"
        
        self.assertRedirects(response, expected_frontend_url, fetch_redirect_response=False)
        
    def test_redirect_for_anonymous_user(self):
        response = self.client.get(self.url)
        
        expected_frontend_url = f"https://space4u.in/products/{self.batch.product.sku}"
        
        self.assertRedirects(response, expected_frontend_url, fetch_redirect_response=False)
        
    def test_invalid_batch_code_returns_404(self):
        invalid_url = reverse('core:qr_redirect', kwargs={'batch_code': 'FAKE-CODE'})
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 404)