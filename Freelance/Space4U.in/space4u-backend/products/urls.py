from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, TrendingDealViewSet

router = DefaultRouter()
router.register(r'', ProductViewSet, basename='product')

urlpatterns = [
    path('trending-deals/', TrendingDealViewSet.as_view({'get': 'list'}), name='trending-deals-list'),
    path('trending-deals/<int:pk>/', TrendingDealViewSet.as_view({'get': 'retrieve'}), name='trending-deals-detail'),
    path('', include(router.urls)),
]
