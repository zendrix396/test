"""
Custom allauth adapter to handle post-social-login redirects and JWT token generation.
"""
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.http import HttpResponseRedirect
from rest_framework_simplejwt.tokens import RefreshToken
from decouple import config
import logging

logger = logging.getLogger(__name__)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter that handles post-social-login redirects with JWT tokens.
    """
    
    def get_connect_redirect_url(self, request, socialaccount):
        """
        Returns the URL to redirect to after successfully connecting a social account.
        """
        return self._get_redirect_url_with_tokens(request)
    
    def get_login_redirect_url(self, request):
        """
        Returns the URL to redirect to after a successful login.
        This is called by allauth after social login completes.
        """
        return self._get_redirect_url_with_tokens(request)
    
    def populate_user(self, request, sociallogin, data):
        """
        Populate user fields from social account data.
        This is called before save_user, so we can set username here.
        The 'data' parameter contains the user info from Google OAuth.
        Only set username if user doesn't have one yet (new user signup).
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Only generate username if user doesn't have one (new signup, not existing user login)
        if not user.username or user.username.strip() == '':
            # Extract Google profile data from the data parameter
            # Google OAuth returns: name, given_name, family_name, email, etc.
            name = None
            if isinstance(data, dict):
                if 'name' in data:
                    name = data.get('name', '').strip()
                elif 'given_name' in data and 'family_name' in data:
                    given = data.get('given_name', '').strip()
                    family = data.get('family_name', '').strip()
                    if given or family:
                        name = f"{given} {family}".strip()
            
            username_base = None
            
            # First try to use the Google name
            if name:
                # Clean the name to make it a valid username
                username_base = ''.join(c for c in name if c.isalnum() or c in ['_', '-', ' '])
                username_base = username_base.replace(' ', '_').lower()
                # Remove multiple underscores
                while '__' in username_base:
                    username_base = username_base.replace('__', '_')
                username_base = username_base.strip('_-')
            
            # Fallback to email if name didn't work
            if not username_base or len(username_base) < 3:
                email = user.email or (data.get('email', '') if isinstance(data, dict) else '')
                if email:
                    username_base = email.split('@')[0]
                    username_base = ''.join(c for c in username_base if c.isalnum() or c in ['_', '-'])
            
            # If still no good base, use a default
            if not username_base or len(username_base) < 3:
                username_base = "user"
            
            # Ensure uniqueness - check before assigning
            from .models import CustomUser
            username = username_base
            counter = 1
            # Check if username exists (user might not have ID yet, so we check by username)
            while CustomUser.objects.filter(username=username).exists():
                username = f"{username_base}{counter}"
                counter += 1
                # Safety limit to prevent infinite loop
                if counter > 1000:
                    import uuid
                    username = f"{username_base}_{uuid.uuid4().hex[:8]}"
                    break
            
            user.username = username
        
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """
        Override to handle referral codes for Google OAuth signups.
        """
        user = super().save_user(request, sociallogin, form)
        
        # Handle referral code from URL parameter (e.g., ?ref=CODE)
        # Check both GET and session (in case it was stored during OAuth flow)
        referral_code_str = request.GET.get('ref') or request.GET.get('referral_code') or request.session.get('referral_code')
        if referral_code_str and user and user.pk:
            try:
                from .models import ReferralCode, Referral, ReferralConfig, LoyaltyTransaction
                
                referral_code_obj = ReferralCode.objects.get(code=referral_code_str.upper())
                referrer = referral_code_obj.owner
                
                # Check if referral system is enabled
                ref_config = ReferralConfig.objects.filter(enabled=True).first()
                if ref_config and referrer != user:
                    # Check if referral already exists
                    referral_exists = Referral.objects.filter(referred=user).exists()
                    
                    if not referral_exists:
                        # Create referral record
                        referral = Referral.objects.create(
                            referrer=referrer,
                            referred=user,
                            code=referral_code_obj,
                            reward_points=ref_config.referrer_points
                        )
                        
                        # Award points to referrer
                        referrer.loyalty_points += ref_config.referrer_points
                        referrer.save(update_fields=['loyalty_points'])
                        LoyaltyTransaction.objects.create(
                            user=referrer,
                            points=ref_config.referrer_points,
                            reason=f"Referral bonus for {user.email}"
                        )
                        
                        # Award points to referred user
                        user.loyalty_points += ref_config.referred_points
                        user.save(update_fields=['loyalty_points'])
                        LoyaltyTransaction.objects.create(
                            user=user,
                            points=ref_config.referred_points,
                            reason="Sign-up bonus via referral"
                        )
                        logger.info(f"Referral points awarded: {referrer.email} got {ref_config.referrer_points}, {user.email} got {ref_config.referred_points}")
                        
                        # Clear referral code from session
                        if 'referral_code' in request.session:
                            del request.session['referral_code']
            except Exception as e:
                logger.error(f"Error processing referral code for Google OAuth user: {e}", exc_info=True)
        
        return user
    
    def pre_social_login(self, request, sociallogin):
        """
        Called before social login completes. Store referral code from URL if present.
        """
        # Store referral code in session if present in URL
        referral_code_str = request.GET.get('ref') or request.GET.get('referral_code')
        if referral_code_str:
            request.session['referral_code'] = referral_code_str
    
    def authentication_error(self, request, provider_id, error=None, exception=None, extra_context=None):
        """
        Called when there's an authentication error.
        """
        frontend_origins = [
            origin.strip()
            for origin in config("FRONTEND_ORIGINS", default="http://localhost:3000").split(",")
            if origin.strip()
        ]
        frontend_url = frontend_origins[0] if frontend_origins else "http://localhost:3000"
        return HttpResponseRedirect(f"{frontend_url}/login?error=oauth_error")
    
    def _get_redirect_url_with_tokens(self, request):
        """
        Helper method to generate redirect URL with JWT tokens.
        """
        if not request.user.is_authenticated:
            # Fallback to default
            frontend_origins = [
                origin.strip()
                for origin in config("FRONTEND_ORIGINS", default="http://localhost:3000").split(",")
                if origin.strip()
            ]
            frontend_url = frontend_origins[0] if frontend_origins else "http://localhost:3000"
            return f"{frontend_url}/login"
        
        user = request.user
        
        # Generate JWT tokens
        try:
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
        except Exception as e:
            logger.error(f"Error generating JWT tokens: {e}")
            frontend_origins = [
                origin.strip()
                for origin in config("FRONTEND_ORIGINS", default="http://localhost:3000").split(",")
                if origin.strip()
            ]
            frontend_url = frontend_origins[0] if frontend_origins else "http://localhost:3000"
            return f"{frontend_url}/login?error=token_error"
        
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
        
        return redirect_url

