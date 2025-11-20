"""
URL configuration for space4u project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from users.google_auth import GoogleOAuthRedirectView, GoogleOAuthCallbackView
from allauth.socialaccount.providers.google import views as google_views
from users.views import CustomRegisterView

# Custom URL patterns for Google OAuth to match GCP redirect URI
# Note: django-allauth generates callback URL as /accounts/google/login/callback/
# based on the login URL pattern
google_urlpatterns = [
    path("login/", GoogleOAuthRedirectView.as_view(), name="google_login"),
    path("login/callback/", GoogleOAuthCallbackView.as_view(), name="google_callback"),
]


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("api/products/", include("products.urls")),
    path("api/commerce/", include("commerce.urls")),
    path("api/shipping/", include("shipping.urls")),
    path("api/auth/", include("dj_rest_auth.urls")),
    # Project users app (JWT, registration, social endpoints)
    path("api/auth/", include(("users.urls", "users"), namespace="users")),
    # Admin API endpoints
    path("api/", include("core.urls")),
    # Django allauth URLs for social authentication
    # Custom Google OAuth handler (checks for SocialApp configuration) - must come before allauth.urls
    path("accounts/google/", include(google_urlpatterns)),
    path("accounts/", include("allauth.urls")),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('auth/registration/', CustomRegisterView.as_view(), name='rest_register'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
