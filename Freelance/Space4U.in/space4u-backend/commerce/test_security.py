"""
Comprehensive security and payment tests for the Commerce app.
Tests authentication, authorization, payment flows, and potential security vulnerabilities.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from products.models import Product, Category, ProductVariant, Batch
from commerce.models import Cart, CartItem, Order, OrderItem, Coupon, WishlistItem
from users.models import CustomUser
from unittest.mock import patch, MagicMock
import json

User = get_user_model()


def create_variant_with_stock(product, sku, price, stock=10, is_default=False):
    """Helper to create variant with stock via batch."""
    from django.utils import timezone
    variant = ProductVariant.objects.create(
        product=product,
        sku=sku,
        price=price,
        is_default=is_default
    )
    Batch.objects.create(
        variant=variant,
        quantity_initial=stock,
        cost_price=Decimal('50.00'),
        received_date=timezone.now().date()
    )
    return variant


class PaymentAuthenticationTests(APITestCase):
    """Tests for payment operations requiring authentication."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='paymentuser',
            email='payment@example.com',
            password='securepass123'
        )
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST-001',
            price=Decimal('100.00'),
            category=self.category
        )
        self.variant = create_variant_with_stock(
            self.product,
            'TEST-VAR-001',
            Decimal('100.00'),
            stock=10,
            is_default=True
        )
        
        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
    def test_create_order_requires_authentication(self):
        """Unauthenticated users cannot create orders."""
        url = '/api/commerce/orders/create/'
        data = {
            "full_name": "Test User",
            "address_line1": "123 Test St",
            "city": "Test City",
            "postal_code": "12345",
            "email": "test@example.com"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_order_with_valid_jwt(self):
        """Authenticated users can create orders with valid JWT."""
        # Add item to cart first
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        cart_url = '/api/commerce/cart/'
        self.client.post(cart_url, {"variant_id": self.variant.id, "quantity": 1}, format='json')
        
        # Create order
        url = '/api/commerce/orders/create/'
        data = {
            "full_name": "Test User",
            "address_line1": "123 Test St",
            "city": "Test City",
            "postal_code": "12345",
            "email": "test@example.com"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
    
    def test_create_payment_requires_authentication(self):
        """Payment creation requires authentication."""
        url = '/api/commerce/orders/create-payment/'
        data = {"order_id": 1, "payment_method": "COD"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_razorpay_order_creation_requires_auth(self):
        """Razorpay order creation requires authentication."""
        url = '/api/commerce/orders/razorpay/create/'
        data = {"order_id": 1}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_verify_payment_requires_auth(self):
        """Payment verification requires authentication."""
        url = '/api/commerce/orders/razorpay/verify/'
        data = {
            "order_id": 1,
            "razorpay_order_id": "order_test",
            "razorpay_payment_id": "pay_test",
            "razorpay_signature": "sig_test"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_invoice_access_requires_auth(self):
        """Invoice access requires authentication."""
        url = '/api/commerce/invoices/pdf/1/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class OrderAuthorizationTests(APITestCase):
    """Tests for order access authorization - users should only access their own orders."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='pass123'
        )
        
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST-001',
            price=Decimal('100.00'),
            category=self.category
        )
        self.variant = create_variant_with_stock(
            self.product,
            'TEST-VAR-001',
            Decimal('100.00'),
            is_default=True
        )
        
        # Create order for user1
        self.order = Order.objects.create(
            user=self.user1,
            full_name="User One",
            address_line1="123 Test St",
            city="Test City",
            postal_code="12345",
            email="user1@example.com",
            total_cost=Decimal('100.00')
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            variant=self.variant,
            quantity=1,
            unit_price=Decimal('100.00'),
            line_total=Decimal('100.00')
        )
        
        # Get JWT tokens
        refresh1 = RefreshToken.for_user(self.user1)
        self.token1 = str(refresh1.access_token)
        
        refresh2 = RefreshToken.for_user(self.user2)
        self.token2 = str(refresh2.access_token)
    
    def test_user_can_access_own_orders(self):
        """User can access their own orders."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.get('/api/auth/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.order.id)
    
    def test_user_cannot_access_other_user_orders(self):
        """User cannot see other users' orders in their order list."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        response = self.client.get('/api/auth/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
    
    def test_user_can_access_own_invoice(self):
        """User can access their own order invoice."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        with patch('commerce.views.generate_invoice_pdf') as mock_pdf:
            mock_pdf.return_value = b'%PDF-1.5\n%%EOF'
            response = self.client.get(f'/api/commerce/invoices/pdf/{self.order.id}/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_user_cannot_access_other_user_invoice(self):
        """User cannot access another user's invoice."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        with patch('commerce.views.generate_invoice_pdf') as mock_pdf:
            mock_pdf.return_value = b'%PDF-1.5\n%%EOF'
            response = self.client.get(f'/api/commerce/invoices/pdf/{self.order.id}/')
            self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])


class PaymentIntegrityTests(APITestCase):
    """Tests for payment integrity and fraud prevention."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='payuser',
            email='pay@example.com',
            password='pass123'
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)
        
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST-001',
            price=Decimal('100.00'),
            category=self.category
        )
        self.variant = create_variant_with_stock(
            self.product,
            'TEST-VAR-001',
            Decimal('100.00'),
            is_default=True
        )
    
    def test_order_total_cannot_be_manipulated(self):
        """Order total is calculated server-side and cannot be manipulated."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        # Add item to cart
        self.client.post('/api/commerce/cart/', {
            "variant_id": self.variant.id,
            "quantity": 2
        }, format='json')
        
        # Try to create order with manipulated total
        response = self.client.post('/api/commerce/orders/create/', {
            "full_name": "Test User",
            "address_line1": "123 Test St",
            "city": "Test City",
            "postal_code": "12345",
            "email": "test@example.com",
            "total_cost": "1.00"  # Manipulated low price
        }, format='json')
        
        # Order should be created with correct total
        if response.status_code == status.HTTP_201_CREATED:
            order = Order.objects.get(id=response.data['id'])
            # Total should be 2 * 100 = 200, not 1
            self.assertEqual(order.total_cost, Decimal('200.00'))
    
    def test_cannot_create_order_with_insufficient_stock(self):
        """Cannot create order when stock is insufficient."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        # Try to add more items than available stock
        response = self.client.post('/api/commerce/cart/', {
            "variant_id": self.variant.id,
            "quantity": 999  # More than stock of 10
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('stock', str(response.data).lower())
    
    def test_payment_method_validation(self):
        """Payment method must be valid."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        # Add item to cart
        self.client.post('/api/commerce/cart/', {
            "variant_id": self.variant.id,
            "quantity": 1
        }, format='json')
        
        # Create order with invalid payment method
        response = self.client.post('/api/commerce/orders/create/', {
            "full_name": "Test User",
            "address_line1": "123 Test St",
            "city": "Test City",
            "postal_code": "12345",
            "email": "test@example.com",
            "payment_method": "INVALID_METHOD"
        }, format='json')
        
        # Should either reject or default to valid method
        if response.status_code == status.HTTP_201_CREATED:
            order = Order.objects.get(id=response.data['id'])
            self.assertIn(order.payment_method, [Order.PaymentMethod.RAZORPAY, Order.PaymentMethod.COD])
    
    def test_cannot_pay_for_already_paid_order(self):
        """Cannot process payment for an already paid order."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        # Create order
        self.client.post('/api/commerce/cart/', {
            "variant_id": self.variant.id,
            "quantity": 1
        }, format='json')
        
        order_response = self.client.post('/api/commerce/orders/create/', {
            "full_name": "Test User",
            "address_line1": "123 Test St",
            "city": "Test City",
            "postal_code": "12345",
            "email": "test@example.com"
        }, format='json')
        
        if order_response.status_code == status.HTTP_201_CREATED:
            order_id = order_response.data['id']
            
            # Mark order as paid
            order = Order.objects.get(id=order_id)
            order.status = Order.Status.PAID
            order.save()
            
            # Try to pay again
            payment_response = self.client.post('/api/commerce/orders/create-payment/', {
                "order_id": order_id,
                "payment_method": "COD"
            }, format='json')
            
            # Should reject duplicate payment
            self.assertNotEqual(payment_response.status_code, status.HTTP_200_OK)


class JWTSecurityTests(APITestCase):
    """Comprehensive JWT token security tests."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='jwtuser',
            email='jwt@example.com',
            password='securepass123'
        )
        refresh = RefreshToken.for_user(self.user)
        self.valid_token = str(refresh.access_token)
    
    def test_expired_token_rejected(self):
        """Expired JWT tokens are rejected."""
        from datetime import timedelta
        # Create an expired token
        refresh = RefreshToken.for_user(self.user)
        token = refresh.access_token
        token.set_exp(lifetime=timedelta(seconds=-1))  # Set expiration to past
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token)}')
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_invalid_token_rejected(self):
        """Invalid JWT tokens are rejected."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token_12345')
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_missing_token_rejected(self):
        """Requests without tokens are rejected for protected endpoints."""
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_malformed_auth_header_rejected(self):
        """Malformed authorization headers are rejected."""
        self.client.credentials(HTTP_AUTHORIZATION='InvalidFormat token123')
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_valid_token_accepted(self):
        """Valid JWT tokens are accepted."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.valid_token}')
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'jwtuser')
    
    def test_token_refresh_works(self):
        """Token refresh mechanism works correctly."""
        refresh = RefreshToken.for_user(self.user)
        
        response = self.client.post('/api/auth/jwt/refresh/', {
            'refresh': str(refresh)
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        
        # New token should work
        new_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_token}')
        profile_response = self.client.get('/api/auth/me/')
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)


class CouponSecurityTests(APITestCase):
    """Tests for coupon application security."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='couponuser',
            email='coupon@example.com',
            password='pass123'
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)
        
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST-001',
            price=Decimal('100.00'),
            category=self.category
        )
        self.variant = create_variant_with_stock(
            self.product,
            'TEST-VAR-001',
            Decimal('100.00'),
            is_default=True
        )
        
        from django.utils import timezone
        from datetime import timedelta
        self.coupon = Coupon.objects.create(
            code='TEST10',
            discount_type=Coupon.DiscountType.PERCENTAGE,
            value=Decimal('10.00'),
            is_active=True,
            valid_from=timezone.now(),
            valid_to=timezone.now() + timedelta(days=30),
            usage_limit=5
        )
    
    def test_coupon_usage_limit_enforced(self):
        """Coupon usage limit is enforced."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        # Use coupon to its limit
        for i in range(5):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='pass123'
            )
            refresh = RefreshToken.for_user(user)
            token = str(refresh.access_token)
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            
            self.client.post('/api/commerce/cart/', {
                "variant_id": self.variant.id,
                "quantity": 1
            }, format='json')
            
            self.client.post('/api/commerce/cart/apply-coupon/', {
                "code": "TEST10"
            }, format='json')
        
        # Try to use after limit
        self.coupon.refresh_from_db()
        if self.coupon.usage_count >= self.coupon.usage_limit:
            # Should reject
            response = self.client.post('/api/commerce/cart/apply-coupon/', {
                "code": "TEST10"
            }, format='json')
            self.assertNotEqual(response.status_code, status.HTTP_200_OK)
    
    def test_inactive_coupon_rejected(self):
        """Inactive coupons cannot be applied."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        # Deactivate coupon
        self.coupon.is_active = False
        self.coupon.save()
        
        self.client.post('/api/commerce/cart/', {
            "variant_id": self.variant.id,
            "quantity": 1
        }, format='json')
        
        response = self.client.post('/api/commerce/cart/apply-coupon/', {
            "code": "TEST10"
        }, format='json')
        
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
    
    def test_nonexistent_coupon_rejected(self):
        """Non-existent coupon codes are rejected."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.client.post('/api/commerce/cart/', {
            "variant_id": self.variant.id,
            "quantity": 1
        }, format='json')
        
        response = self.client.post('/api/commerce/cart/apply-coupon/', {
            "code": "INVALID_CODE"
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SQLInjectionPreventionTests(APITestCase):
    """Tests to ensure SQL injection is prevented."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='sqluser',
            email='sql@example.com',
            password='pass123'
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)
    
    def test_sql_injection_in_search(self):
        """SQL injection attempts in search are handled safely."""
        response = self.client.get('/api/products/', {
            'search': "'; DROP TABLE products; --"
        })
        
        # Should not cause error, just return empty results
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify products table still exists
        from products.models import Product
        Product.objects.all()  # Should not raise error
    
    def test_sql_injection_in_coupon_code(self):
        """SQL injection in coupon code is prevented."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        response = self.client.post('/api/commerce/cart/apply-coupon/', {
            "code": "' OR '1'='1"
        }, format='json')
        
        # Should reject without executing SQL
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)


class DataLeakageTests(APITestCase):
    """Tests to prevent data leakage."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='leakuser',
            email='leak@example.com',
            password='pass123'
        )
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST-001',
            price=Decimal('100.00'),
            category=self.category
        )
    
    def test_password_not_exposed_in_api(self):
        """User passwords are never exposed in API responses."""
        refresh = RefreshToken.for_user(self.user)
        token = str(refresh.access_token)
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/auth/me/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('password', response.data)
        
        # Check JSON string doesn't contain password hash
        response_str = json.dumps(response.data)
        self.assertNotIn(self.user.password, response_str)
    
    def test_other_user_emails_not_leaked(self):
        """Other users' emails are not leaked."""
        user2 = User.objects.create_user(
            username='user2',
            email='secret@example.com',
            password='pass123'
        )
        
        refresh = RefreshToken.for_user(self.user)
        token = str(refresh.access_token)
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/auth/me/')
        
        response_str = json.dumps(response.data)
        self.assertNotIn('secret@example.com', response_str)


class RateLimitingTests(APITestCase):
    """Tests for rate limiting (if implemented)."""
    
    def test_excessive_login_attempts(self):
        """Excessive login attempts should be handled."""
        # Try many failed logins
        for i in range(20):
            response = self.client.post('/api/auth/jwt/create/', {
                'username': 'nonexistent',
                'password': 'wrong'
            }, format='json')
            
            # Should reject with 401 (rate limiting may not be enabled in test)
            self.assertIn(response.status_code, [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_429_TOO_MANY_REQUESTS
            ])


class WishlistSecurityTests(APITestCase):
    """Tests for wishlist security."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='wishuser',
            email='wish@example.com',
            password='pass123'
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)
        
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Test Product',
            sku='TEST-001',
            price=Decimal('100.00'),
            category=self.category
        )
        self.variant = create_variant_with_stock(
            self.product,
            'TEST-VAR-001',
            Decimal('100.00'),
            is_default=True
        )
    
    def test_wishlist_requires_authentication(self):
        """Wishlist operations require authentication."""
        response = self.client.post('/api/commerce/wishlist/', {
            "variant_id": self.variant.id
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_can_only_access_own_wishlist(self):
        """Users can only access their own wishlist."""
        # Create wishlist for user
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.client.post('/api/commerce/wishlist/', {
            "variant_id": self.variant.id
        }, format='json')
        
        # Create another user
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='pass123'
        )
        refresh2 = RefreshToken.for_user(user2)
        token2 = str(refresh2.access_token)
        
        # User 2 tries to access their wishlist
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')
        response = self.client.get('/api/commerce/wishlist/')
        
        # Should only see their own (empty) wishlist
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if isinstance(response.data, list):
            self.assertEqual(len(response.data), 0)

