"""
Custom Google OAuth view that handles missing SocialApp configuration gracefully.
"""
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.conf import settings
from decouple import config
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
import logging

logger = logging.getLogger(__name__)


def check_google_socialapp():
    """
    Check if Google SocialApp is configured.
    Returns (exists, app) tuple.
    """
    try:
        site = Site.objects.get_current()
        # Check if any Google SocialApp exists for this site
        apps = SocialApp.objects.filter(provider='google')
        for app in apps:
            if site in app.sites.all():
                return True, app
        return False, None
    except Exception as e:
        logger.error(f"Error checking Google SocialApp: {e}")
        return False, None


@method_decorator(csrf_exempt, name='dispatch')
class GoogleOAuthRedirectView(APIView):
    """
    Custom view that wraps allauth's Google OAuth login.
    Checks if SocialApp is configured before redirecting.
    Supports both GET and POST methods.
    """
    permission_classes = [AllowAny]

    def _handle_oauth(self, request):
        """Common handler for both GET and POST requests."""
        exists, app = check_google_socialapp()
        
        if not exists:
            # Get frontend URL from settings
            frontend_origins = [
                origin.strip()
                for origin in config("FRONTEND_ORIGINS", default="http://localhost:3000").split(",")
                if origin.strip()
            ]
            frontend_url = frontend_origins[0] if frontend_origins else "http://localhost:3000"
            
            # Return a helpful error message
            if request.headers.get('Accept', '').startswith('application/json'):
                return JsonResponse({
                    "error": "Google OAuth not configured",
                    "message": "Please configure Google OAuth in Django admin: Admin > Social Applications > Add Social Application",
                    "details": "Provider: Google, Client ID and Secret Key required"
                }, status=503)
            
            # For browser requests, redirect to frontend login with error parameter
            error_url = f"{frontend_url}/login?error=google_not_configured"
            return HttpResponseRedirect(error_url)
        
        # If configured, redirect directly to Google OAuth (bypass allauth's intermediate page)
        # Note: The callback URL will be /accounts/google/login/callback/
        # Make sure this matches your GCP redirect URI configuration
        try:
            from allauth.socialaccount.providers.google.views import oauth2_login
            from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
            from allauth.socialaccount.helpers import render_authentication_error
            
            # Get the adapter and build the authorization URL directly
            adapter = GoogleOAuth2Adapter(request)
            
            # Build the OAuth URL directly to skip the intermediate page
            # Manually construct the Google OAuth URL
            try:
                from allauth.socialaccount.providers.oauth2.client import OAuth2Client
                from django.contrib.sites.models import Site
                from urllib.parse import quote
                
                site = Site.objects.get_current()
                # Use request.build_absolute_uri to get the correct protocol and domain
                callback_url = request.build_absolute_uri('/accounts/google/login/callback/')
                
                # Preserve referral code in OAuth flow if present
                referral_code = request.GET.get('ref') or request.GET.get('referral_code')
                if referral_code:
                    request.session['referral_code'] = referral_code
                
                client_id = app.client_id
                redirect_uri = quote(callback_url, safe='')
                scope = 'email profile'
                state = OAuth2Client.generate_state()
                request.session['oauth_state'] = state
                
                auth_url = (
                    f"https://accounts.google.com/o/oauth2/v2/auth?"
                    f"client_id={client_id}&"
                    f"redirect_uri={redirect_uri}&"
                    f"scope={scope}&"
                    f"response_type=code&"
                    f"state={state}&"
                    f"access_type=online"
                )
                return HttpResponseRedirect(auth_url)
            except Exception as e:
                logger.error(f"Error building OAuth URL: {e}", exc_info=True)
                # Final fallback to allauth's normal flow
                return oauth2_login(request)
        except Exception as e:
            logger.error(f"Error in Google OAuth login: {e}")
            frontend_origins = [
                origin.strip()
                for origin in config("FRONTEND_ORIGINS", default="http://localhost:3000").split(",")
                if origin.strip()
            ]
            frontend_url = frontend_origins[0] if frontend_origins else "http://localhost:3000"
            return HttpResponseRedirect(f"{frontend_url}/login?error=oauth_error")

    def get(self, request):
        return self._handle_oauth(request)

    def post(self, request):
        return self._handle_oauth(request)


class GoogleOAuthCallbackView(APIView):
    """
    Custom callback handler for Google OAuth that:
    1. Completes the OAuth flow
    2. Generates JWT tokens
    3. Checks if username is set
    4. Redirects to frontend with tokens or username prompt
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            from allauth.socialaccount.providers.google.views import oauth2_callback
            from allauth.socialaccount.helpers import complete_social_login
            from allauth.socialaccount.models import SocialToken, SocialAccount
            from django.contrib.auth import login
            
            # Call the original allauth callback - this handles the OAuth flow
            response = oauth2_callback(request)
            
            # After callback, check if we have a social account token
            # This means the OAuth was successful
            try:
                # Try to get the social account from session or request
                # allauth stores this in the session during the flow
                if hasattr(request, 'session'):
                    sociallogin = request.session.get('socialaccount_sociallogin')
                    if sociallogin:
                        # Complete the social login
                        ret = complete_social_login(request, sociallogin)
                        if isinstance(ret, HttpResponseRedirect):
                            # User is now authenticated
                            if request.user.is_authenticated:
                                user = request.user
                                
                                # Generate JWT tokens
                                refresh = RefreshToken.for_user(user)
                                access_token = str(refresh.access_token)
                                refresh_token = str(refresh)
                                
                                # Get frontend URL
                                frontend_origins = [
                                    origin.strip()
                                    for origin in config("FRONTEND_ORIGINS", default="http://localhost:3000").split(",")
                                    if origin.strip()
                                ]
                                frontend_url = frontend_origins[0] if frontend_origins else "http://localhost:3000"
                                
                                # Check if username is set
                                if not user.username or user.username.strip() == '':
                                    # Redirect to frontend with tokens and username prompt flag
                                    redirect_url = f"{frontend_url}/login?google_oauth=success&access_token={access_token}&refresh_token={refresh_token}&needs_username=true"
                                else:
                                    # Redirect to frontend with tokens
                                    redirect_url = f"{frontend_url}/login?google_oauth=success&access_token={access_token}&refresh_token={refresh_token}"
                                
                                return HttpResponseRedirect(redirect_url)
                
                # Fallback: if user is authenticated after callback, generate tokens
                if request.user.is_authenticated:
                    user = request.user
                    
                    # Generate JWT tokens
                    refresh = RefreshToken.for_user(user)
                    access_token = str(refresh.access_token)
                    refresh_token = str(refresh)
                    
                    # Get frontend URL
                    frontend_origins = [
                        origin.strip()
                        for origin in config("FRONTEND_ORIGINS", default="http://localhost:3000").split(",")
                        if origin.strip()
                    ]
                    frontend_url = frontend_origins[0] if frontend_origins else "http://localhost:3000"
                    
                    # Check if username is set
                    if not user.username or user.username.strip() == '':
                        # Redirect to frontend with tokens and username prompt flag
                        redirect_url = f"{frontend_url}/login?google_oauth=success&access_token={access_token}&refresh_token={refresh_token}&needs_username=true"
                    else:
                        # Redirect to frontend with tokens
                        redirect_url = f"{frontend_url}/login?google_oauth=success&access_token={access_token}&refresh_token={refresh_token}"
                    
                    return HttpResponseRedirect(redirect_url)
                    
            except Exception as inner_e:
                logger.error(f"Error processing social login: {inner_e}")
            
            # If we get here, something went wrong or the response needs to be returned as-is
            return response
        except Exception as e:
            logger.error(f"Error in Google OAuth callback: {e}", exc_info=True)
            frontend_origins = [
                origin.strip()
                for origin in config("FRONTEND_ORIGINS", default="http://localhost:3000").split(",")
                if origin.strip()
            ]
            frontend_url = frontend_origins[0] if frontend_origins else "http://localhost:3000"
            return HttpResponseRedirect(f"{frontend_url}/login?error=oauth_error")

