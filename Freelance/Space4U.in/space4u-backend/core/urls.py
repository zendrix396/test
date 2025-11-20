from django.urls import path
from .views import QRRedirectView
from .admin_api import (
    admin_check_superuser,
    admin_dashboard_stats,
    admin_orders_list,
    admin_order_detail,
    admin_users_list,
    admin_products_list,
    admin_audit_log,
)
from .generic_admin_api import generic_model_list, generic_model_detail
from .admin_metadata import get_admin_models_view, get_model_config_view

app_name = 'core'

urlpatterns = [
    path('qr/<str:batch_code>/', QRRedirectView.as_view(), name='qr_redirect'),
    # Admin API endpoints
    path('admin/check-superuser/', admin_check_superuser, name='admin_check_superuser'),
    path('admin/dashboard-stats/', admin_dashboard_stats, name='admin_dashboard_stats'),
    path('admin/orders/', admin_orders_list, name='admin_orders_list'),
    path('admin/orders/<int:order_id>/', admin_order_detail, name='admin_order_detail'),
    path('admin/users/', admin_users_list, name='admin_users_list'),
    path('admin/products/', admin_products_list, name='admin_products_list'),
    path('admin/audit-log/', admin_audit_log, name='admin_audit_log'),
    # Generic model CRUD endpoints
    path('admin/api/<str:model_key>/', generic_model_list, name='generic_model_list'),
    path('admin/api/<str:model_key>/<str:pk>/', generic_model_detail, name='generic_model_detail'),
    # New Admin Metadata Endpoints
    path('admin/metadata/models/', get_admin_models_view, name='admin_metadata_models'),
    path('admin/metadata/config/<str:app_label>/<str:model_name>/', get_model_config_view, name='admin_metadata_config'),
]
