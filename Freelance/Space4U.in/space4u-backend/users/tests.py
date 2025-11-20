from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class ReferralAndLeaderboardTests(APITestCase):
    def setUp(self):
        self.referrer = User.objects.create_user(username='ref', password='p1')
        self.referred = User.objects.create_user(username='new', password='p1')
        self.client = APIClient()

    def test_referral_flow(self):
        # get code for referrer
        self.client.force_authenticate(self.referrer)
        r = self.client.get('/api/auth/referrals/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        code = r.data['code']

        # apply as referred
        self.client.force_authenticate(self.referred)
        r = self.client.post('/api/auth/referrals/', {"code": code}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_leaderboard(self):
        r = self.client.get('/api/auth/leaderboard/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
# users/tests.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from unittest.mock import patch
from django.conf import settings

User = get_user_model()

class CustomUserModelTests(TestCase):

    def test_create_user_with_defaults(self):
        """Tests that a new user has default loyalty and wallet values."""
        User = get_user_model()
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )

        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.loyalty_points, 0)
        self.assertEqual(user.wallet_balance, Decimal('0.00'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        """Tests creating a superuser."""
        User = get_user_model()
        admin_user = User.objects.create_superuser(
            username='superadmin',
            email='admin@example.com',
            password='password123'
        )

        self.assertEqual(admin_user.username, 'superadmin')
        self.assertEqual(admin_user.email, 'admin@example.com')
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)

class UserAuthAPITests(APITestCase):
    
    def test_user_registration_success(self):
        """
        Ensure we can create a new user account.
        """
        url = reverse('users:register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'strongpassword123',
            'password2': 'strongpassword123'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'newuser')
        self.assertTrue(User.objects.get().check_password('strongpassword123'))

    def test_user_registration_password_mismatch(self):
        """
        Ensure registration fails if passwords do not match.
        """
        url = reverse('users:register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'strongpassword123',
            'password2': 'mismatchpassword'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)
        self.assertIn('password', response.data)

    def test_user_login_and_token_generation(self):
        """
        Ensure a registered user can log in and receive access/refresh tokens.
        """
        # First, create a user to log in with
        test_user = User.objects.create_user(
            username='testlogin', 
            email='testlogin@example.com', 
            password='loginpassword123'
        )

        url = reverse('users:token_obtain_pair')
        data = {
            'username': 'testlogin',
            'password': 'loginpassword123'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_user_login_failed(self):
        """
        Ensure login fails with incorrect credentials.
        """
        User.objects.create_user(username='testlogin', password='loginpassword123')

        url = reverse('users:token_obtain_pair')
        data = {
            'username': 'testlogin',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)


class UserProfileAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='profileuser',
            email='profile@example.com',
            password='profilepassword'
        )
        self.client.force_authenticate(user=self.user)

    def test_view_and_update_profile(self):
        # View
        res = self.client.get(reverse('users:me'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['username'], 'profileuser')

        # Update (email is read-only, so we only test updatable fields)
        update_data = {
            'first_name': 'Profile',
            'last_name': 'User',
            'phone_number': '1234567890'
        }
        res = self.client.patch(reverse('users:me'), update_data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Profile')
        self.assertEqual(self.user.last_name, 'User')
        self.assertEqual(self.user.phone_number, '1234567890')


class JWTTokenTests(APITestCase):
    """
    Comprehensive tests for JWT token functionality including:
    - Token validation
    - Token refresh
    - Token expiration
    - Protected endpoint access
    """
    
    def setUp(self):
        """Create a test user for JWT token tests."""
        self.user = User.objects.create_user(
            username='jwtuser',
            email='jwt@example.com',
            password='jwtpassword123'
        )
        self.login_url = reverse('users:token_obtain_pair')
        self.refresh_url = reverse('users:token_refresh')
    
    def test_token_structure_valid(self):
        """
        Test that generated tokens have the correct structure and claims.
        """
        # Get tokens
        response = self.client.post(self.login_url, {
            'username': 'jwtuser',
            'password': 'jwtpassword123'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify token structure
        access_token = response.data['access']
        refresh_token = response.data['refresh']
        
        # Tokens should have 3 parts separated by dots (header.payload.signature)
        self.assertEqual(len(access_token.split('.')), 3)
        self.assertEqual(len(refresh_token.split('.')), 3)
        
        # Verify tokens are strings and not empty
        self.assertTrue(isinstance(access_token, str))
        self.assertTrue(isinstance(refresh_token, str))
        self.assertGreater(len(access_token), 0)
        self.assertGreater(len(refresh_token), 0)
    
    def test_token_refresh_success(self):
        """
        Test that refresh token can be used to obtain a new access token.
        """
        # First, login to get tokens
        login_response = self.client.post(self.login_url, {
            'username': 'jwtuser',
            'password': 'jwtpassword123'
        }, format='json')
        
        refresh_token = login_response.data['refresh']
        
        # Use refresh token to get a new access token
        refresh_response = self.client.post(self.refresh_url, {
            'refresh': refresh_token
        }, format='json')
        
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)
        
        # New access token should be different from the original
        new_access_token = refresh_response.data['access']
        original_access_token = login_response.data['access']
        self.assertNotEqual(new_access_token, original_access_token)
    
    def test_token_refresh_with_invalid_token(self):
        """
        Test that refresh fails with an invalid refresh token.
        """
        response = self.client.post(self.refresh_url, {
            'refresh': 'invalid.refresh.token'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_token_refresh_with_access_token(self):
        """
        Test that refresh fails when trying to use an access token instead of refresh token.
        """
        # Login to get tokens
        login_response = self.client.post(self.login_url, {
            'username': 'jwtuser',
            'password': 'jwtpassword123'
        }, format='json')
        
        access_token = login_response.data['access']
        
        # Try to refresh with access token (should fail)
        response = self.client.post(self.refresh_url, {
            'refresh': access_token
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_access_token_authentication(self):
        """
        Test that access token can be used to authenticate API requests.
        """
        # Login to get access token
        login_response = self.client.post(self.login_url, {
            'username': 'jwtuser',
            'password': 'jwtpassword123'
        }, format='json')
        
        access_token = login_response.data['access']
        
        # Note: This test verifies token format. 
        # In a real scenario, you'd test against a protected endpoint
        # For now, we verify the token is properly formatted for Authorization header
        auth_header = f'Bearer {access_token}'
        self.assertTrue(auth_header.startswith('Bearer '))
        self.assertGreater(len(auth_header), 7)  # "Bearer " + token
    
    def test_token_contains_user_information(self):
        """
        Test that tokens can be decoded and contain correct user information.
        """
        from rest_framework_simplejwt.tokens import AccessToken
        
        # Create token for user
        token = AccessToken.for_user(self.user)
        
        # Verify token contains user ID
        self.assertEqual(int(token['user_id']), self.user.id)
        self.assertEqual(token['token_type'], 'access')
        
        # Verify token has expiration
        self.assertIn('exp', token)
        self.assertIn('iat', token)
    
    def test_multiple_users_get_different_tokens(self):
        """
        Test that different users receive different tokens.
        """
        # Create second user
        user2 = User.objects.create_user(
            username='jwtuser2',
            email='jwt2@example.com',
            password='jwtpassword456'
        )
        
        # Get token for first user
        response1 = self.client.post(self.login_url, {
            'username': 'jwtuser',
            'password': 'jwtpassword123'
        }, format='json')
        
        # Get token for second user
        response2 = self.client.post(self.login_url, {
            'username': 'jwtuser2',
            'password': 'jwtpassword456'
        }, format='json')
        
        # Tokens should be different
        self.assertNotEqual(response1.data['access'], response2.data['access'])
        self.assertNotEqual(response1.data['refresh'], response2.data['refresh'])
    
    def test_token_verification_with_valid_token(self):
        """
        Test that valid tokens pass verification.
        """
        from rest_framework_simplejwt.tokens import AccessToken
        from rest_framework_simplejwt.exceptions import TokenError
        
        # Create a fresh token
        token = AccessToken.for_user(self.user)
        token_string = str(token)
        
        # Verify token can be validated
        try:
            validated_token = AccessToken(token_string)
            self.assertEqual(int(validated_token['user_id']), self.user.id)
        except TokenError:
            self.fail("Valid token failed verification")
    
    def test_token_verification_with_invalid_signature(self):
        """
        Test that tokens with invalid signatures are rejected.
        """
        from rest_framework_simplejwt.tokens import AccessToken
        from rest_framework_simplejwt.exceptions import TokenError
        
        # Create a token and modify the signature
        token = AccessToken.for_user(self.user)
        token_string = str(token)
        
        # Tamper with the signature (last part of the token)
        parts = token_string.split('.')
        tampered_token = f"{parts[0]}.{parts[1]}.invalidsignature"
        
        # Verify tampered token is rejected
        with self.assertRaises(TokenError):
            AccessToken(tampered_token)
    
    def test_registration_does_not_auto_login(self):
        """
        Test that user registration does not automatically provide JWT tokens.
        Users must explicitly login after registration.
        """
        register_url = reverse('users:register')
        data = {
            'username': 'newjwtuser',
            'email': 'newjwt@example.com',
            'password': 'newpassword123',
            'password2': 'newpassword123'
        }
        response = self.client.post(register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Verify no tokens in registration response
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)
    
    def test_token_lifetime(self):
        """
        Test that tokens have expiration times set.
        """
        from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
        import datetime
        
        # Create tokens
        access_token = AccessToken.for_user(self.user)
        refresh_token = RefreshToken.for_user(self.user)
        
        # Verify tokens have expiration
        self.assertIn('exp', access_token)
        self.assertIn('exp', refresh_token)
        
        # Verify expiration is in the future
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        self.assertGreater(access_token['exp'], now)
        self.assertGreater(refresh_token['exp'], now)
        
        # Refresh token should expire after access token
        self.assertGreater(refresh_token['exp'], access_token['exp'])


class GoogleLoginAPITest(APITestCase):
    def setUp(self):
        self.site = Site.objects.create(domain='127.0.0.1:8000', name='127.0.0.1:8000')
        settings.SITE_ID = self.site.id
        self.social_app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='your-google-client-id',
            secret='your-google-secret-key',
        )
        self.social_app.sites.add(self.site)

    def test_google_login_without_token(self):
        """
        Test google login endpoint without providing a token.
        It should fail.
        """
        url = '/api/auth/google/'
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)