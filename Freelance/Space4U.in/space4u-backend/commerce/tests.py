from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from products.models import Product, ProductVariant, Batch
from commerce.models import Cart, CartItem, SavedForLaterItem, RecentlyViewedItem, Order
from unittest.mock import patch


User = get_user_model()


class CommerceFeatureTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='p1')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.product = Product.objects.create(name='Prod', status='PUBLISHED')
        self.variant = ProductVariant.objects.create(product=self.product, name='Def', sku='SKU1', price=100)
        # ensure stock exists
        Batch.objects.create(
            variant=self.variant,
            quantity_initial=50,
            quantity_current=50,
            cost_price=50,
            received_date='2024-01-01'
        )

    def test_save_for_later_crud(self):
        url = '/api/commerce/saved-for-later/'
        r = self.client.post(url, {"variant_id": self.variant.id}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SavedForLaterItem.objects.filter(user=self.user).count(), 1)
        r = self.client.get(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.client.delete(url, {"variant_id": self.variant.id}, format='json')
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(SavedForLaterItem.objects.filter(user=self.user).count(), 0)

    def test_recently_viewed_list(self):
        mv_url = f'/api/products/{self.product.id}/mark_viewed/'
        r = self.client.post(mv_url, {})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        list_url = '/api/commerce/recently-viewed/'
        r = self.client.get(list_url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(len(r.data) >= 1)

    def test_cart_and_preliminary_order_and_cod(self):
        cart_url = '/api/commerce/cart/'
        r = self.client.post(cart_url, {"variant_id": self.variant.id, "quantity": 2}, format='json')
        self.assertIn(r.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        create_order_url = '/api/commerce/orders/create/'
        r = self.client.post(create_order_url, {
            "full_name": "Test User",
            "address_line1": "Line1",
            "city": "City",
            "postal_code": "12345",
            "email": "test@example.com",
        }, format='json')
        if r.status_code != status.HTTP_201_CREATED:
            print(f"Order creation failed with: {r.data}")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        order_id = r.data.get('id') or Order.objects.filter(user=self.user).order_by('-id').first().id
        pay_url = '/api/commerce/orders/create-payment/'
        r = self.client.post(pay_url, {"order_id": order_id, "payment_method": "COD"}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.payment_method, Order.PaymentMethod.COD)
        self.assertIn(order.status, (Order.Status.PAID, Order.Status.PROCESSING))

    @patch('commerce.views.generate_invoice_pdf')
    def test_invoice_pdf_generation(self, mock_generate_pdf):
        mock_generate_pdf.return_value = b'%PDF-1.5\\n%%EOF'

        cart_url = '/api/commerce/cart/'
        self.client.post(cart_url, {"variant_id": self.variant.id, "quantity": 1}, format='json')
        create_order_url = '/api/commerce/orders/create/'
        r = self.client.post(create_order_url, {
            "full_name": "Test User",
            "address_line1": "Line1",
            "city": "City",
            "postal_code": "12345",
            "email": "test@example.com",
        }, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        order_id = r.data.get('id')

        pdf_url = f'/api/commerce/invoices/pdf/{order_id}/'
        r = self.client.get(pdf_url)
        
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF-'))
        mock_generate_pdf.assert_called_once()
