from decimal import Decimal, InvalidOperation

from django.db.models import DecimalField, Min, Q, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Product, ProductReview, TrendingDeal
from .serializers import ProductSerializer, ProductReviewSerializer, TrendingDealSerializer
from commerce.models import RecentlyViewedItem
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.parsers import MultiPartParser, FormParser

# Create your views here.
@extend_schema(
    summary="Product Catalog",
    description="Publicly accessible product catalog supporting list and detail views."
)
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """A simple ViewSet for viewing published products with rich filtering."""

    serializer_class = ProductSerializer
    permission_classes = (AllowAny,)

    @method_decorator(cache_page(60 * 15))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(60 * 15))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def get_queryset(self):
        queryset = (
            Product.objects.filter(status='PUBLISHED')
            .select_related('category')
            .prefetch_related('tags', 'images', 'variants')
        )

        queryset = queryset.annotate(
            variant_discount_floor=Coalesce(
                Min('variants__discount_price'),
                Value(None),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
            variant_price_floor=Coalesce(
                Min('variants__price'),
                Value(None),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
            product_floor=Coalesce(
                'discount_price',
                'price',
                Value(None),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
        )

        queryset = queryset.annotate(
            effective_price=Coalesce(
                'variant_discount_floor',
                'product_floor',
                'variant_price_floor',
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )

        params = self.request.query_params

        sku_param = params.get('sku')
        if sku_param:
            queryset = queryset.filter(
                Q(sku__iexact=sku_param) | Q(variants__sku__iexact=sku_param)
            )
            return queryset.distinct()

        category_slug = params.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        tags_param = params.get('tags')
        if tags_param:
            tag_names = [tag.strip() for tag in tags_param.split(',') if tag.strip()]
            for tag_name in tag_names:
                queryset = queryset.filter(tags__name__iexact=tag_name)

        search_query = params.get('search')
        if search_query:
            search_query = search_query.strip()
            if search_query:
                queryset = queryset.filter(
                    Q(name__icontains=search_query)
                    | Q(description__icontains=search_query)
                    | Q(sku__icontains=search_query)
                    | Q(tags__name__icontains=search_query)
                )

        min_price = params.get('min_price')
        if min_price:
            try:
                queryset = queryset.filter(effective_price__gte=Decimal(min_price))
            except (InvalidOperation, TypeError):
                pass

        max_price = params.get('max_price')
        if max_price:
            try:
                queryset = queryset.filter(effective_price__lte=Decimal(max_price))
            except (InvalidOperation, TypeError):
                pass

        ordering_param = params.get('ordering')
        if ordering_param:
            direction = '-' if ordering_param.startswith('-') else ''
            field = ordering_param.lstrip('-')

            if field == 'price':
                queryset = queryset.order_by(f"{direction}effective_price", f"{direction}name")
            elif field in {'name', 'created_at'}:
                queryset = queryset.order_by(f"{direction}{field}")
            else:
                queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('-created_at')

        return queryset.distinct()

    @extend_schema(
        summary="Mark a product as viewed",
        description="Authenticated users can mark a product as recently viewed.",
        responses={200: OpenApiResponse(description="Status OK.")}
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def mark_viewed(self, request, pk=None):
        product = self.get_object()
        # pick default or first variant to represent viewed item
        variant = product.variants.filter(is_default=True).first() or product.variants.first()
        if not variant:
            return Response({"detail": "No variant available to track view."}, status=status.HTTP_400_BAD_REQUEST)
        RecentlyViewedItem.objects.update_or_create(user=request.user, variant=variant)
        return Response({"status": "ok"})

    @extend_schema(
        summary="Get product reviews",
        description="Get all reviews for a specific product.",
        responses={200: ProductReviewSerializer(many=True)}
    )
    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def reviews(self, request, pk=None):
        product = self.get_object()
        qs = ProductReview.objects.filter(product=product).order_by('-created_at')
        serializer = ProductReviewSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Add a product review",
        description="Authenticated users can add or update their review for a product.",
        request=ProductReviewSerializer,
        responses={201: OpenApiResponse(description="Review added/updated successfully.")}
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated], parser_classes=[MultiPartParser, FormParser])
    def add_review(self, request, pk=None):
        product = self.get_object()
        data = request.data.copy()
        data['product'] = product.id
        
        # Ensure rating is an integer
        if 'rating' in data:
            try:
                data['rating'] = int(data['rating'])
            except (ValueError, TypeError):
                pass
        
        # Ensure title and body are strings (empty strings are valid)
        if 'title' in data and data['title'] is None:
            data['title'] = ''
        if 'body' in data and data['body'] is None:
            data['body'] = ''
        
        serializer = ProductReviewSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        # ensure single review per user
        review, created = ProductReview.objects.update_or_create(
            product=product, user=request.user,
            defaults={
                'rating': serializer.validated_data['rating'],
                'title': serializer.validated_data.get('title', ''),
                'body': serializer.validated_data.get('body', ''),
                'image': serializer.validated_data.get('image'),
            }
        )
        return Response(ProductReviewSerializer(review, context={'request': request}).data, status=201)

    @extend_schema(
        summary="Get recommended products",
        description="Get a list of recommended products based on the current product's category.",
        responses={200: ProductSerializer(many=True)}
    )
    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def recommended(self, request, pk=None):
        product = self.get_object()
        # simple recommendations: same category or shared tags
        qs = Product.objects.filter(status='PUBLISHED').exclude(id=product.id)
        if product.category_id:
            qs = qs.filter(category_id=product.category_id)
        qs = qs[:12]
        return Response(ProductSerializer(qs, many=True).data)


@extend_schema(
    summary="Trending Deals",
    description="Get active trending deals and offers for the hero section."
)
class TrendingDealViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for fetching active trending deals."""
    
    serializer_class = TrendingDealSerializer
    permission_classes = (AllowAny,)
    
    def get_queryset(self):
        return TrendingDeal.objects.live().select_related('product', 'category')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context
    
    @method_decorator(cache_page(60 * 15))
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
