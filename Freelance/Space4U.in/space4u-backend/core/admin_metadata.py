# core/admin_metadata.py
from django.contrib import admin
from django.apps import apps
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_admin_models_view(request):
    """
    Returns a list of all registered models in the Django admin,
    grouped by app, to dynamically build the admin sidebar.
    """
    app_list = admin.site.get_app_list(request)
    result = []
    
    for app in app_list:
        app_data = {
            'name': app['name'],
            'app_label': app['app_label'],
            'models': []
        }
        
        for model in app['models']:
            # Extract model name from object_name (e.g., 'CustomUser' -> 'user')
            model_name_lower = model['object_name'].lower()
            # Map to our model_key format used in generic_admin_api
            from .generic_admin_api import MODEL_MAP
            model_key = None
            for key, (app_label, obj_name) in MODEL_MAP.items():
                if app_label == app['app_label'] and obj_name == model['object_name']:
                    model_key = key
                    break
            
            # If not found in MODEL_MAP, use lowercase object_name
            if not model_key:
                model_key = model_name_lower
            
            app_data['models'].append({
                'name': model['name'],
                'object_name': model['object_name'],
                'admin_url': model['admin_url'],
                'model_key': model_key,
                'app_label': app['app_label']
            })
        
        result.append(app_data)
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_model_config_view(request, app_label, model_name):
    """
    Returns the admin configuration for a specific model,
    including list_display, search_fields, and form fields.
    """
    try:
        model = apps.get_model(app_label, model_name)
        model_admin = admin.site._registry.get(model)
        
        if not model_admin:
            return Response({'error': 'Model admin not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get list_display fields
        list_display = list(model_admin.get_list_display(request))
        if 'id' not in list_display:
            list_display.insert(0, 'id')
        
        # Get search fields
        search_fields = list(model_admin.get_search_fields(request))
        
        # Get form fields
        form = model_admin.get_form(request)
        form_fields = []
        
        for name, field in form.base_fields.items():
            field_info = {
                'name': name,
                'type': field.widget.__class__.__name__,
                'label': field.label or name,
                'required': field.required,
                'help_text': field.help_text or '',
            }
            
            # Determine field type for better frontend rendering
            widget = field.widget
            if hasattr(field, 'queryset'):
                # Foreign key or many-to-many
                # Check the field class name to determine type
                from django.forms import ModelMultipleChoiceField
                if isinstance(field, ModelMultipleChoiceField):
                    field_info['field_type'] = 'many_to_many'
                else:
                    field_info['field_type'] = 'foreign_key'
            elif 'Date' in widget.__class__.__name__ or 'Time' in widget.__class__.__name__:
                field_info['field_type'] = 'datetime'
            elif 'Textarea' in widget.__class__.__name__:
                field_info['field_type'] = 'textarea'
            elif 'Checkbox' in widget.__class__.__name__ or widget.__class__.__name__ == 'CheckboxInput':
                field_info['field_type'] = 'checkbox'
            elif 'Number' in widget.__class__.__name__ or 'Integer' in widget.__class__.__name__:
                field_info['field_type'] = 'number'
            else:
                field_info['field_type'] = 'text'
            
            form_fields.append(field_info)
        
        config = {
            'list_display': list_display,
            'search_fields': search_fields,
            'form_fields': form_fields,
        }
        
        return Response(config)
    
    except (LookupError, KeyError) as e:
        return Response({'error': f'Model or admin not found: {str(e)}'}, status=status.HTTP_404_NOT_FOUND)

