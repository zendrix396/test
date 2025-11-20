"""
Admin API endpoints for Next.js admin panel
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from django.views.decorators.cache import cache_page
from datetime import timedelta
from decimal import Decimal

from users.models import CustomUser, LoyaltyTransaction, WalletTransaction
from commerce.models import Order, OrderItem, Cart, CartItem, Coupon, GiftCard
from products.models import Product, ProductVariant, Category
from shipping.models import Shipment
from django.contrib.admin.models import LogEntry

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_check_superuser(request):
    """Check if the current user is a superuser"""
    return Response({
        'is_superuser': request.user.is_superuser,
        'is_staff': request.user.is_staff,
        'username': request.user.username,
        'email': request.user.email
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
@cache_page(60 * 5)  # Cache this view for 5 minutes
def admin_dashboard_stats(request):
    """Get dashboard statistics"""
    now = timezone.now()
    today = now.date()
    this_week = today - timedelta(days=7)
    this_month = today - timedelta(days=30)
    
    # Optimized Queries
    paid_statuses = ['PAID', 'PROCESSING', 'SHIPPED', 'COMPLETED']
    
    order_stats = Order.objects.aggregate(
        total_orders=Count('id'),
        orders_today=Count('id', filter=Q(created_at__date=today)),
        orders_this_week=Count('id', filter=Q(created_at__date__gte=this_week)),
        orders_this_month=Count('id', filter=Q(created_at__date__gte=this_month)),
        total_revenue=Sum('total_cost'),
        revenue_today=Sum('total_cost', filter=Q(created_at__date=today, status__in=paid_statuses)),
        revenue_this_week=Sum('total_cost', filter=Q(created_at__date__gte=this_week, status__in=paid_statuses)),
        revenue_this_month=Sum('total_cost', filter=Q(created_at__date__gte=this_month, status__in=paid_statuses)),
    )
    
    user_stats = CustomUser.objects.aggregate(
        total_users=Count('id'),
        users_today=Count('id', filter=Q(date_joined__date=today)),
        users_this_week=Count('id', filter=Q(date_joined__date__gte=this_week)),
        users_this_month=Count('id', filter=Q(date_joined__date__gte=this_month)),
    )
    
    product_stats = Product.objects.aggregate(
        total_products=Count('id'),
        published_products=Count('id', filter=Q(status='PUBLISHED'))
    )
    
    # Orders by status
    orders_by_status = Order.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Recent orders
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10].values(
        'id', 'order_number', 'user__username', 'status', 'total_cost', 'created_at'
    )
    
    # Cart abandon data
    # Carts that haven't been updated in 24 hours and have items
    abandoned_cutoff = now - timedelta(hours=24)
    abandoned_carts = Cart.objects.filter(
        updated_at__lt=abandoned_cutoff,
        items__isnull=False
    ).distinct().count()
    
    # Calculate abandoned cart value
    abandoned_cart_value = Decimal('0')
    for cart in Cart.objects.filter(updated_at__lt=abandoned_cutoff, items__isnull=False).distinct():
        cart_total = Decimal('0')
        for item in cart.items.all():
            if item.variant:
                price = item.variant.discount_price or item.variant.price
                cart_total += price * item.quantity
        abandoned_cart_value += cart_total
    
    # Repeat purchases: users with more than 1 completed order
    repeat_customers = CustomUser.objects.filter(
        orders__status='COMPLETED'
    ).annotate(
        order_count=Count('orders', filter=Q(orders__status='COMPLETED'))
    ).filter(order_count__gt=1).count()
    
    # Calculate low stock products (available stock < reserved + 10)
    low_stock_count = 0
    for variant in ProductVariant.objects.all():
        if variant.stock < variant.reserved_quantity + 10:
            low_stock_count += 1
    low_stock_products = low_stock_count
    
    # Sales data for real-time dashboard (last 7 days daily breakdown)
    sales_data = []
    for i in range(7):
        date = today - timedelta(days=i)
        day_revenue = Order.objects.filter(
            created_at__date=date,
            status__in=paid_statuses
        ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0')
        day_orders = Order.objects.filter(created_at__date=date).count()
        sales_data.append({
            'date': date.isoformat(),
            'revenue': str(day_revenue),
            'orders': day_orders
        })
    sales_data.reverse()  # Oldest to newest
    
    return Response({
        'orders': {
            'total': order_stats['total_orders'] or 0,
            'today': order_stats['orders_today'] or 0,
            'this_week': order_stats['orders_this_week'] or 0,
            'this_month': order_stats['orders_this_month'] or 0,
            'by_status': list(orders_by_status),
            'recent': list(recent_orders)
        },
        'revenue': {
            'total': str(order_stats['total_revenue'] or Decimal('0')),
            'today': str(order_stats['revenue_today'] or Decimal('0')),
            'this_week': str(order_stats['revenue_this_week'] or Decimal('0')),
            'this_month': str(order_stats['revenue_this_month'] or Decimal('0'))
        },
        'users': {
            'total': user_stats['total_users'] or 0,
            'today': user_stats['users_today'] or 0,
            'this_week': user_stats['users_this_week'] or 0,
            'this_month': user_stats['users_this_month'] or 0
        },
        'products': {
            'total': product_stats['total_products'] or 0,
            'published': product_stats['published_products'] or 0,
            'low_stock': low_stock_products
        },
        'carts': {
            'abandoned_count': abandoned_carts,
            'abandoned_value': str(abandoned_cart_value),
            'repeat_customers': repeat_customers
        },
        'sales_data': sales_data
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_orders_list(request):
    """List all orders with filters"""
    status_filter = request.query_params.get('status', None)
    search = request.query_params.get('search', None)
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 50))
    
    queryset = Order.objects.select_related('user').order_by('-created_at')
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if search:
        queryset = queryset.filter(
            Q(order_number__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(id__icontains=search)
        )
    
    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    
    orders = queryset[start:end].values(
        'id', 'order_number', 'user__username', 'user__email',
        'status', 'total_cost', 'payment_method', 'created_at', 'updated_at'
    )
    
    return Response({
        'results': list(orders),
        'total': total,
        'page': page,
        'page_size': page_size
    })


@api_view(['GET', 'PATCH'])
@permission_classes([IsAdminUser])
def admin_order_detail(request, order_id):
    """Get or update order details"""
    try:
        order = Order.objects.select_related('user').prefetch_related('items').get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        order_data = {
            'id': order.id,
            'order_number': order.order_number,
            'user': {
                'id': order.user.id if order.user else None,
                'username': order.user.username if order.user else None,
                'email': order.user.email if order.user else None,
            },
            'status': order.status,
            'payment_method': order.payment_method,
            'total_cost': str(order.total_cost),
            'discount_amount': str(order.discount_amount),
            'wallet_applied_amount': str(order.wallet_applied_amount),
            'created_at': order.created_at,
            'updated_at': order.updated_at,
            'items': [{
                'id': item.id,
                'variant': {
                    'id': item.variant.id,
                    'sku': item.variant.sku,
                    'name': item.variant.name,
                },
                'quantity': item.quantity,
                'unit_price': str(item.unit_price),
                'line_total': str(item.line_total),
            } for item in order.items.all()],
            'shipping': {
                'full_name': order.full_name,
                'email': order.email,
                'phone': order.phone,
                'address_line1': order.address_line1,
                'address_line2': order.address_line2,
                'city': order.city,
                'state': order.state,
                'postal_code': order.postal_code,
                'country': order.country,
                'courier_name': order.courier_name,
                'tracking_number': order.tracking_number,
            }
        }
        return Response(order_data)
    
    elif request.method == 'PATCH':
        status_new = request.data.get('status')
        if status_new:
            order.status = status_new
            order.save()
        return Response({'message': 'Order updated', 'status': order.status})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_users_list(request):
    """List all users"""
    search = request.query_params.get('search', None)
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 50))
    
    queryset = CustomUser.objects.all().order_by('-date_joined')
    
    if search:
        queryset = queryset.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(display_name__icontains=search)
        )
    
    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    
    users = queryset[start:end].values(
        'id', 'username', 'email', 'display_name', 'is_staff', 'is_superuser',
        'loyalty_points', 'wallet_balance', 'loyalty_tier', 'date_joined'
    )
    
    return Response({
        'results': list(users),
        'total': total,
        'page': page,
        'page_size': page_size
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_products_list(request):
    """List all products"""
    search = request.query_params.get('search', None)
    status_filter = request.query_params.get('status', None)
    category_filter = request.query_params.get('category', None)
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 50))
    
    queryset = Product.objects.select_related('category').prefetch_related('variants').order_by('-id')
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if category_filter:
        queryset = queryset.filter(category_id=category_filter)
    
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(sku__icontains=search)
        )
    
    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    
    products = []
    for product in queryset[start:end]:
        products.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'category': product.category.name if product.category else None,
            'status': product.status,
            'has_variants': product.has_variants,
            'variants_count': product.variants.count(),
            'image': product.image.url if product.image else None,
        })
    
    return Response({
        'results': products,
        'total': total,
        'page': page,
        'page_size': page_size
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_audit_log(request):
    """Get all admin activities (audit log)"""
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 100))
    action_filter = request.query_params.get('action', None)
    user_filter = request.query_params.get('user', None)
    
    queryset = LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')
    
    if action_filter:
        # LogEntry action flags: ADDITION=1, CHANGE=2, DELETION=3
        action_map = {
            'add': 1,
            'change': 2,
            'delete': 3
        }
        if action_filter.lower() in action_map:
            queryset = queryset.filter(action_flag=action_map[action_filter.lower()])
    
    if user_filter:
        queryset = queryset.filter(user__username__icontains=user_filter)
    
    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    
    log_entries = []
    for entry in queryset[start:end]:
        action_name = 'ADDITION' if entry.action_flag == 1 else 'CHANGE' if entry.action_flag == 2 else 'DELETION'
        log_entries.append({
            'id': entry.id,
            'action_time': entry.action_time,
            'user': entry.user.username if entry.user else 'System',
            'user_id': entry.user.id if entry.user else None,
            'content_type': entry.content_type.model if entry.content_type else None,
            'object_id': entry.object_id,
            'object_repr': entry.object_repr,
            'action_flag': entry.action_flag,
            'action_name': action_name,
            'change_message': entry.change_message,
        })
    
    return Response({
        'results': log_entries,
        'total': total,
        'page': page,
        'page_size': page_size
    })

