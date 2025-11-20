"""
Generic CRUD API endpoints for admin panel
Supports all Django models with list, detail, create, update, delete operations
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.db import models
from django.apps import apps
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
import json

# Model mapping for API endpoints
MODEL_MAP = {
    # django.contrib.auth
    'group': ('auth', 'Group'),
    
    # allauth.account
    'emailaddress': ('account', 'EmailAddress'),
    
    # rest_framework.authtoken
    'token': ('authtoken', 'TokenProxy'),

    # Commerce
    'cart': ('commerce', 'Cart'),
    'coupon': ('commerce', 'Coupon'),
    'currencyexchangerate': ('commerce', 'CurrencyExchangeRate'),
    'giftcardtransaction': ('commerce', 'GiftCardTransaction'),
    'giftcard': ('commerce', 'GiftCard'),
    'giftwrapsetting': ('commerce', 'GiftWrapSetting'),
    'orderitem': ('commerce', 'OrderItem'),
    'orderrefund': ('commerce', 'OrderRefund'),
    'order': ('commerce', 'Order'),
    'recentlyvieweditem': ('commerce', 'RecentlyViewedItem'),
    'refundconfig': ('commerce', 'RefundConfig'),
    'returnrequest': ('commerce', 'ReturnRequest'),
    'savedforlateritem': ('commerce', 'SavedForLaterItem'),
    'usercouponusage': ('commerce', 'UserCouponUsage'),
    'wishlistitem': ('commerce', 'WishlistItem'),
    
    # Products
    'batch': ('products', 'Batch'),
    'category': ('products', 'Category'),
    'productreview': ('products', 'ProductReview'),
    'productvariant': ('products', 'ProductVariant'),
    'product': ('products', 'Product'),
    'scrapedproduct': ('products', 'ScrapedProduct'),
    'stockadjustmentreason': ('products', 'StockAdjustmentReason'),
    'stockmovement': ('products', 'StockMovement'),
    'trendingdeal': ('products', 'TrendingDeal'),
    
    # Users
    'user': ('users', 'CustomUser'),
    'badge': ('users', 'Badge'),
    'emailreminderconfig': ('users', 'EmailReminderConfig'),
    'loyaltyconfig': ('users', 'LoyaltyConfig'),
    'loyaltytransaction': ('users', 'LoyaltyTransaction'),
    'referralcode': ('users', 'ReferralCode'),
    'referralconfig': ('users', 'ReferralConfig'),
    'referral': ('users', 'Referral'),
    'userbadge': ('users', 'UserBadge'),
    'wallettransaction': ('users', 'WalletTransaction'),
    
    # Shipping
    'shipmenttracking': ('shipping', 'ShipmentTracking'),
    'shipment': ('shipping', 'Shipment'),
    'warehouse': ('shipping', 'Warehouse'),
    'waybill': ('shipping', 'Waybill'),
    
    # Taggit
    'tag': ('taggit', 'Tag'),

    # Token Blacklist
    'blacklistedtoken': ('token_blacklist', 'BlacklistedToken'),
    'outstandingtoken': ('token_blacklist', 'OutstandingToken'),

    # Sites
    'site': ('sites', 'Site'),

    # Social Accounts
    'socialaccount': ('socialaccount', 'SocialAccount'),
    'socialapplicationtoken': ('socialaccount', 'SocialAppToken'),
    'socialapplication': ('socialaccount', 'SocialApplication'),
}


def get_model_class(model_key):
    """Get Django model class from model key"""
    if model_key not in MODEL_MAP:
        return None
    app_label, model_name = MODEL_MAP[model_key]
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


def serialize_model_instance(instance, model_class):
    """Serialize a model instance to dict"""
    data = {}
    for field in model_class._meta.get_fields():
        if field.is_relation:
            if hasattr(instance, field.name):
                related_obj = getattr(instance, field.name, None)
                if related_obj:
                    if hasattr(related_obj, 'id'):
                        data[field.name] = related_obj.id
                    else:
                        data[field.name] = str(related_obj)
                else:
                    data[field.name] = None
        else:
            value = getattr(instance, field.name, None)
            if isinstance(value, (int, float, str, bool, type(None))):
                data[field.name] = value
            elif hasattr(value, 'isoformat'):  # DateTime, Date
                data[field.name] = value.isoformat()
            else:
                data[field.name] = str(value)
    return data


@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def generic_model_list(request, model_key):
    """List all instances or create new instance"""
    model_class = get_model_class(model_key)
    if not model_class:
        return Response({'error': 'Model not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        # List view
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        search = request.query_params.get('search', None)
        
        queryset = model_class.objects.all()
        
        # Apply search if provided
        if search:
            search_filters = Q()
            for field in model_class._meta.get_fields():
                if isinstance(field, (models.CharField, models.TextField, models.EmailField)):
                    search_filters |= Q(**{f"{field.name}__icontains": search})
            queryset = queryset.filter(search_filters)
        
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        
        instances = queryset[start:end]
        results = [serialize_model_instance(inst, model_class) for inst in instances]
        
        return Response({
            'results': results,
            'total': total,
            'page': page,
            'page_size': page_size
        })
    
    elif request.method == 'POST':
        # Create view
        try:
            data = request.data
            # Handle foreign key fields
            for field in model_class._meta.get_fields():
                if field.is_relation and field.name in data:
                    if data[field.name] is None or data[field.name] == '':
                        data[field.name] = None
                    else:
                        # Keep as ID for foreign keys
                        pass
            
            instance = model_class.objects.create(**data)
            return Response(serialize_model_instance(instance, model_class), status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAdminUser])
def generic_model_detail(request, model_key, pk):
    """Get, update, or delete a specific instance"""
    model_class = get_model_class(model_key)
    if not model_class:
        return Response({'error': 'Model not found'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        instance = model_class.objects.get(pk=pk)
    except ObjectDoesNotExist:
        return Response({'error': 'Object not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        return Response(serialize_model_instance(instance, model_class))
    
    elif request.method == 'PATCH':
        try:
            data = request.data
            # Handle foreign key fields
            for field in model_class._meta.get_fields():
                if field.is_relation and field.name in data:
                    if data[field.name] is None or data[field.name] == '':
                        data[field.name] = None
            
            for key, value in data.items():
                setattr(instance, key, value)
            instance.save()
            return Response(serialize_model_instance(instance, model_class))
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        try:
            instance.delete()
            return Response({'message': 'Deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

