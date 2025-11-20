import json
import logging
from datetime import datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .services import DelhiveryService, ShiprocketService
from .models import Shipment, ShipmentTracking, Warehouse, Waybill
from commerce.models import Order

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_pincode_serviceability(request):
    """Check if a pincode is serviceable by Delhivery"""
    pincode = request.GET.get('pincode')
    if not pincode:
        return Response(
            {'error': 'Pincode is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    service = DelhiveryService()
    result, error = service.check_pincode_serviceability(pincode)
    
    if error:
        return Response(
            {'error': error},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fetch_bulk_waybills(request):
    """Fetch bulk waybills from Delhivery"""
    count = int(request.GET.get('count', 10))
    
    service = DelhiveryService()
    waybills, error = service.fetch_bulk_waybills(count)
    
    if error:
        return Response(
            {'error': error},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response({
        'status': 'success',
        'waybills_fetched': len(waybills),
        'waybills': [wb.number for wb in waybills]
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_shipment_view(request):
    """Create a shipment in Delhivery for an order"""
    order_id = request.data.get('order_id')
    if not order_id:
        return Response(
            {'error': 'order_id is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    warehouse_id = request.data.get('warehouse_id')
    warehouse = None
    if warehouse_id:
        try:
            warehouse = Warehouse.objects.get(id=warehouse_id)
        except Warehouse.DoesNotExist:
            return Response(
                {'error': 'Warehouse not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

    service = DelhiveryService()
    result, error = service.create_shipment(order, warehouse)
    
    if error:
        return Response(
            {'error': error},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response(result, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_shipment(request):
    """Update shipment details"""
    waybill = request.data.get('waybill')
    if not waybill:
        return Response(
            {'error': 'waybill is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    service = DelhiveryService()
    # Delhivery update endpoint
    url = f"{service.api_url}/api/p/edit"
    headers = service._get_headers()
    
    try:
        import requests
        response = requests.post(url, headers=headers, json=request.data, timeout=10)
        response.raise_for_status()
        return Response(response.json())
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_shipment(request):
    """Cancel a shipment"""
    waybill = request.data.get('waybill')
    if not waybill:
        return Response(
            {'error': 'waybill is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    service = DelhiveryService()
    result, error = service.cancel_shipment(waybill)
    
    if error:
        return Response(
            {'error': error},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def track_shipment(request):
    """Track a shipment by waybill number or order ID"""
    waybill = request.GET.get('waybill')
    order_id = request.GET.get('order_id')
    
    if not waybill and not order_id:
        return Response(
            {'error': 'Either waybill or order_id is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    service = DelhiveryService()
    result, error = service.track_shipment(waybill_number=waybill, order_id=order_id)
    
    if error:
        return Response(
            {'error': error},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_tracking(request, order_id):
    """Get comprehensive tracking information for an order (supports both Delhivery and Shiprocket)"""
    try:
        order = Order.objects.get(id=order_id)
        # Check if user owns the order or is staff
        if order.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to view this order.'},
                status=status.HTTP_403_FORBIDDEN
            )
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Get or create shipment
    shipment, created = Shipment.objects.get_or_create(order=order)
    
    # Determine which service to use based on courier_name
    courier_name = order.courier_name or ""
    tracking_data = None
    
    if "shiprocket" in courier_name.lower():
        service = ShiprocketService()
        if order.tracking_number:
            tracking_data, error = service.track_shipment(awb=order.tracking_number)
        elif order.shipping_id:
            tracking_data, error = service.track_shipment(order_id=order.shipping_id)
    else:
        # Default to Delhivery
        service = DelhiveryService()
        if shipment.waybill:
            tracking_data, error = service.update_shipment_tracking(shipment)
    
    # Update shipment status from tracking data if available
    if tracking_data and isinstance(tracking_data, dict):
        if "shipment_status" in tracking_data:
            shipment.status = tracking_data.get("shipment_status", shipment.status)
        if "current_status" in tracking_data:
            shipment.status = tracking_data.get("current_status", shipment.status)
        if "expected_delivery_date" in tracking_data or "etd" in tracking_data:
            etd = tracking_data.get("expected_delivery_date") or tracking_data.get("etd")
            if etd:
                try:
                    if isinstance(etd, str):
                        shipment.expected_delivery_date = datetime.strptime(etd.split()[0], "%Y-%m-%d").date()
                    else:
                        shipment.expected_delivery_date = etd
                except:
                    pass
        shipment.save()
        
        # Update tracking history for Shiprocket
        if "scans" in tracking_data and isinstance(tracking_data["scans"], list):
            for scan in tracking_data["scans"]:
                scan_time = datetime.now()
                if "date" in scan:
                    try:
                        scan_time = datetime.strptime(scan["date"], "%Y-%m-%d %H:%M:%S")
                    except:
                        try:
                            scan_time = datetime.strptime(scan["date"], "%Y-%m-%d")
                        except:
                            pass
                
                ShipmentTracking.objects.get_or_create(
                    shipment=shipment,
                    status=scan.get("status", ""),
                    scan_date_time=scan_time,
                    defaults={
                        'status_type': scan.get("sr-status-label", ""),
                        'location': scan.get("location", ""),
                        'instructions': scan.get("activity", ""),
                    }
                )
    
    # Get tracking history
    tracking_history = ShipmentTracking.objects.filter(shipment=shipment).order_by('-scan_date_time')
    
    from .serializers import ShipmentTrackingSerializer, ShipmentSerializer
    shipment_data = ShipmentSerializer(shipment).data
    tracking_data_list = ShipmentTrackingSerializer(tracking_history, many=True).data
    
    return Response({
        'shipment': shipment_data,
        'tracking_history': tracking_data_list,
        'order': {
            'id': order.id,
            'status': order.status,
            'tracking_number': order.tracking_number,
            'courier_name': order.courier_name,
        },
        'raw_tracking': tracking_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_shipping_label(request):
    """Generate shipping label for a waybill"""
    waybill = request.GET.get('waybill')
    if not waybill:
        return Response(
            {'error': 'waybill is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    pdf = request.GET.get('pdf', 'true').lower() == 'true'
    pdf_size = request.GET.get('pdf_size', 'A4')

    service = DelhiveryService()
    content, error = service.generate_shipping_label(waybill, pdf=pdf, pdf_size=pdf_size)
    
    if error:
        return Response(
            {'error': error},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="label_{waybill}.pdf"'
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_pickup_request(request):
    """Create a pickup request"""
    service = DelhiveryService()
    url = f"{service.api_url}/fm/request/new/"
    headers = service._get_headers()
    
    try:
        import requests
        response = requests.post(url, headers=headers, json=request.data, timeout=10)
        response.raise_for_status()
        return Response(response.json())
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_warehouse(request):
    """Create a warehouse in Delhivery and locally"""
    service = DelhiveryService()
    url = f"{service.api_url}/api/backend/clientwarehouse/create/"
    headers = service._get_headers()
    
    try:
        import requests
        response = requests.put(url, headers=headers, json=request.data, timeout=10)
        response.raise_for_status()
        
        # Create warehouse in local database
        warehouse_data = request.data.copy()
        warehouse = Warehouse.objects.create(**warehouse_data)
        
        return Response({
            'delhivery_response': response.json(),
            'warehouse_id': warehouse.id
        })
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
def delhivery_webhook(request):
    """Handle Delhivery webhook callbacks"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=400)

    try:
        data = json.loads(request.body)
        waybill_number = data.get('waybill') or data.get('waybill_no')
        
        if not waybill_number:
            return JsonResponse({'error': 'Waybill number not found in webhook data.'}, status=400)

        try:
            waybill = Waybill.objects.get(number=waybill_number)
            shipment = Shipment.objects.get(waybill=waybill)
            
            # Update shipment status
            shipment.status = data.get('status', shipment.status)
            if 'expected_delivery_date' in data:
                try:
                    shipment.expected_delivery_date = datetime.strptime(
                        data['expected_delivery_date'],
                        '%Y-%m-%d'
                    ).date()
                except:
                    pass
            shipment.save()
            
            # Create tracking entry
            scan_time = datetime.now()
            if 'scan_date_time' in data:
                try:
                    scan_time = datetime.fromisoformat(data['scan_date_time'].replace('Z', '+00:00'))
                except:
                    scan_time = datetime.now()
            
            ShipmentTracking.objects.create(
                shipment=shipment,
                status=data.get('status', ''),
                status_type=data.get('status_type', ''),
                location=data.get('location', ''),
                scan_date_time=scan_time,
                instructions=data.get('instructions', ''),
            )
            
            return JsonResponse({'status': 'success'}, status=200)
        except (Waybill.DoesNotExist, Shipment.DoesNotExist):
            logger.warning(f"Webhook received for unknown waybill: {waybill_number}")
            return JsonResponse({'status': 'warning', 'message': 'Waybill not found'}, status=200)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
    except Exception as e:
        logger.error(f"Error processing Delhivery webhook: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def shiprocket_webhook(request):
    """Handle Shiprocket webhook callbacks for tracking updates"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=400)

    try:
        data = json.loads(request.body)
        
        # Shiprocket webhook format may vary, handle common fields
        order_id = data.get('order_id') or data.get('orderId')
        awb_code = data.get('awb_code') or data.get('awbCode') or data.get('awb')
        shipment_id = data.get('shipment_id') or data.get('shipmentId')
        status_update = data.get('status') or data.get('current_status') or data.get('shipment_status')
        
        # Try to find order by shipping_id or tracking_number
        order = None
        if order_id:
            try:
                order = Order.objects.get(shipping_id=str(order_id))
            except Order.DoesNotExist:
                pass
        
        if not order and awb_code:
            try:
                order = Order.objects.get(tracking_number=awb_code)
            except Order.DoesNotExist:
                pass
        
        if not order:
            logger.warning(f"Shiprocket webhook received for unknown order: {data}")
            return JsonResponse({'status': 'warning', 'message': 'Order not found'}, status=200)
        
        # Get or create shipment
        shipment, created = Shipment.objects.get_or_create(order=order)
        
        # Update shipment status
        if status_update:
            shipment.status = status_update
        if awb_code and not order.tracking_number:
            order.tracking_number = awb_code
            order.save(update_fields=['tracking_number'])
        if shipment_id:
            shipment.external_id = str(shipment_id)
        
        # Handle tracking scan data
        if 'scans' in data and isinstance(data['scans'], list):
            for scan in data['scans']:
                scan_time = datetime.now()
                if 'date' in scan:
                    try:
                        scan_time = datetime.strptime(scan['date'], "%Y-%m-%d %H:%M:%S")
                    except:
                        try:
                            scan_time = datetime.strptime(scan['date'], "%Y-%m-%d")
                        except:
                            pass
                
                ShipmentTracking.objects.get_or_create(
                    shipment=shipment,
                    status=scan.get('status', status_update or ''),
                    scan_date_time=scan_time,
                    defaults={
                        'status_type': scan.get('sr-status-label', ''),
                        'location': scan.get('location', ''),
                        'instructions': scan.get('activity', ''),
                    }
                )
        else:
            # Single status update
            if status_update:
                ShipmentTracking.objects.get_or_create(
                    shipment=shipment,
                    status=status_update,
                    scan_date_time=datetime.now(),
                    defaults={
                        'status_type': data.get('sr-status-label', ''),
                        'location': data.get('location', ''),
                        'instructions': data.get('activity', ''),
                    }
                )
        
        # Update expected delivery date if provided
        if 'expected_delivery_date' in data or 'etd' in data:
            etd = data.get('expected_delivery_date') or data.get('etd')
            if etd:
                try:
                    if isinstance(etd, str):
                        shipment.expected_delivery_date = datetime.strptime(etd.split()[0], "%Y-%m-%d").date()
                    else:
                        shipment.expected_delivery_date = etd
                except:
                    pass
        
        shipment.save()
        
        return JsonResponse({'status': 'success'}, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
    except Exception as e:
        logger.error(f"Error processing Shiprocket webhook: {e}")
        return JsonResponse({'error': str(e)}, status=500)

