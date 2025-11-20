import requests
import json
import logging
from datetime import datetime
from django.conf import settings
from commerce.models import Order
from .models import Shipment, Waybill, ShipmentTracking, Warehouse

logger = logging.getLogger(__name__)


class DelhiveryService:
    """Service class for interacting with Delhivery API"""

    def __init__(self):
        self.api_token = getattr(settings, 'DELHIVERY_API_TOKEN', None)
        self.production_mode = getattr(settings, 'DELHIVERY_PRODUCTION_MODE', False)
        
        if self.production_mode:
            self.api_url = 'https://track.delhivery.com'
        else:
            self.api_url = 'https://staging-express.delhivery.com'

    def _get_headers(self):
        """Get headers for Delhivery API requests"""
        return {
            'Authorization': f'Token {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def check_pincode_serviceability(self, pincode):
        """Check if a pincode is serviceable by Delhivery"""
        url = f"{self.api_url}/c/api/pin-codes/json/?filter_codes={pincode}"
        headers = self._get_headers()
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to check pincode serviceability: {e}")
            return None, str(e)

    def fetch_bulk_waybills(self, count=10):
        """Fetch bulk waybills from Delhivery"""
        url = f"{self.api_url}/waybill/api/bulk/json/?count={count}"
        headers = self._get_headers()
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            waybills_str = response.text.strip().strip('"')
            
            if waybills_str:
                waybill_numbers = [wb.strip() for wb in waybills_str.split(',') if wb.strip()]
                waybill_objects = []
                
                for wb_number in waybill_numbers:
                    waybill, created = Waybill.objects.get_or_create(
                        number=wb_number,
                        defaults={'is_used': False}
                    )
                    if created:
                        waybill_objects.append(waybill)
                
                return waybill_objects, None
            return [], None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch waybills: {e}")
            return None, str(e)

    def create_shipment(self, order: Order, warehouse: Warehouse = None):
        """Create a shipment in Delhivery for an order"""
        if not warehouse:
            warehouse = Warehouse.objects.filter(is_active=True).first()
            if not warehouse:
                return None, "No active warehouse found"

        # Get an unused waybill
        waybill = Waybill.objects.filter(is_used=False).first()
        if not waybill:
            # Try to fetch new waybills
            waybills, error = self.fetch_bulk_waybills(10)
            if error or not waybills:
                return None, "No waybills available and failed to fetch new ones"
            waybill = waybills[0]

        # Prepare shipment data
        shipment_data = {
            "shipments": [{
                "waybill": waybill.number,
                "name": order.full_name,
                "order": str(order.id),
                "order_date": order.created_at.strftime("%Y-%m-%d"),
                "total_amount": str(order.total_cost),
                "cod_amount": str(order.total_cost) if order.payment_method == Order.PaymentMethod.COD else "0",
                "add": order.address_line1,
                "city": order.city,
                "state": order.state or "",
                "pin": order.postal_code,
                "country": order.country,
                "phone": order.phone,
                "payment_mode": "COD" if order.payment_method == Order.PaymentMethod.COD else "Prepaid",
                "return_name": warehouse.registered_name or warehouse.name,
                "return_add": warehouse.return_address,
                "return_city": warehouse.return_city,
                "return_state": warehouse.return_state,
                "return_pin": warehouse.return_pin,
                "return_country": warehouse.return_country,
                "return_phone": warehouse.phone,
                "products_desc": ", ".join([item.variant.product.name if item.variant else "Product" for item in order.items.all()]),
            }],
            "pickup_location": {
                "name": warehouse.name,
                "add": warehouse.address,
                "city": warehouse.city,
                "pin": warehouse.pin,
                "country": warehouse.country,
                "phone": warehouse.phone,
            }
        }

        url = f"{self.api_url}/api/cmu/create.json"
        headers = self._get_headers()
        
        try:
            # Delhivery expects form data with format=json&data=<json>
            data = f'format=json&data={json.dumps(shipment_data)}'
            response = requests.post(
                url,
                headers={**headers, 'Content-Type': 'application/x-www-form-urlencoded'},
                data=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # Mark waybill as used
            waybill.is_used = True
            waybill.save()
            
            # Create or update shipment record
            shipment, created = Shipment.objects.get_or_create(
                order=order,
                defaults={
                    'waybill': waybill,
                    'payment_mode': 'COD' if order.payment_method == Order.PaymentMethod.COD else 'Prepaid',
                    'total_amount': order.total_cost,
                    'cod_amount': order.total_cost if order.payment_method == Order.PaymentMethod.COD else 0,
                    'pickup_location': warehouse,
                    'status': 'Manifested',
                }
            )
            
            if not created:
                shipment.waybill = waybill
                shipment.status = 'Manifested'
                shipment.save()
            
            # Update order with tracking info
            order.shipping_id = result.get('shipment_id', '')
            order.tracking_number = waybill.number
            order.courier_name = 'Delhivery'
            order.save(update_fields=['shipping_id', 'tracking_number', 'courier_name'])
            
            return result, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create shipment for order {order.id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_text = e.response.text
                    logger.error(f"Delhivery API error response: {error_text}")
                except:
                    pass
            return None, str(e)

    def track_shipment(self, waybill_number=None, order_id=None):
        """Track a shipment by waybill number or order ID"""
        url = f"{self.api_url}/api/v1/packages/json/"
        params = {}
        
        if waybill_number:
            params['waybill'] = waybill_number
        elif order_id:
            params['ref_ids'] = str(order_id)
        else:
            return None, "Either waybill or order_id is required"
        
        headers = self._get_headers()
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to track shipment: {e}")
            return None, str(e)

    def update_shipment_tracking(self, shipment: Shipment):
        """Fetch and update tracking information for a shipment"""
        if not shipment.waybill:
            return None, "No waybill associated with shipment"
        
        tracking_data, error = self.track_shipment(waybill_number=shipment.waybill.number)
        if error:
            return None, error
        
        if tracking_data and isinstance(tracking_data, dict):
            packages = tracking_data.get('packages', [])
            if packages:
                package = packages[0]
                shipment.status = package.get('status', shipment.status)
                if 'expected_delivery_date' in package:
                    try:
                        shipment.expected_delivery_date = datetime.strptime(
                            package['expected_delivery_date'],
                            '%Y-%m-%d'
                        ).date()
                    except:
                        pass
                shipment.save()
                
                # Update tracking history
                if 'track' in package and isinstance(package['track'], list):
                    for track_item in package['track']:
                        ShipmentTracking.objects.get_or_create(
                            shipment=shipment,
                            status=track_item.get('status', ''),
                            status_type=track_item.get('status_type', ''),
                            scan_date_time=datetime.fromisoformat(
                                track_item['scan_date_time'].replace('Z', '+00:00')
                            ) if 'scan_date_time' in track_item else datetime.now(),
                            defaults={
                                'location': track_item.get('location', ''),
                                'instructions': track_item.get('instructions', ''),
                            }
                        )
                
                return tracking_data, None
        
        return tracking_data, None

    def cancel_shipment(self, waybill_number):
        """Cancel a shipment"""
        url = f"{self.api_url}/api/p/edit"
        headers = self._get_headers()
        payload = {
            "waybill": waybill_number,
            "cancellation": "true"
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to cancel shipment: {e}")
            return None, str(e)

    def generate_shipping_label(self, waybill_number, pdf=True, pdf_size='A4'):
        """Generate shipping label for a waybill"""
        url = f"{self.api_url}/api/p/packing_slip"
        params = {
            'wbns': waybill_number,
            'pdf': 'true' if pdf else 'false',
            'pdf_size': pdf_size
        }
        headers = self._get_headers()
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.content, None  # Return binary content for PDF
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to generate shipping label: {e}")
            return None, str(e)


class ShiprocketService:
    """Service class for interacting with Shiprocket API"""

    def __init__(self):
        self.api_email = getattr(settings, 'SHIPROCKET_API_EMAIL', None)
        self.api_password = getattr(settings, 'SHIPROCKET_API_PASSWORD', None)
        self.api_url = 'https://apiv2.shiprocket.in/v1/external'
        self._token = None
        self._token_expiry = None

    def _get_auth_token(self):
        """Get or refresh authentication token"""
        from datetime import datetime, timedelta
        if self._token and self._token_expiry and datetime.now() < self._token_expiry:
            return self._token

        url = f"{self.api_url}/auth/login"
        payload = {
            "email": self.api_email,
            "password": self.api_password
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            self._token = data.get('token')
            # Token typically expires in 24 hours, refresh after 23 hours
            self._token_expiry = datetime.now() + timedelta(hours=23)
            return self._token
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to authenticate with Shiprocket: {e}")
            return None

    def _get_headers(self):
        """Get headers for Shiprocket API requests"""
        token = self._get_auth_token()
        if not token:
            raise Exception("Unable to authenticate with Shiprocket")
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def get_pickup_locations(self):
        """Get all pickup locations from Shiprocket"""
        url = f"{self.api_url}/settings/company/pickup"
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('data', {}).get('shipping_address', []), None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch pickup locations: {e}")
            return None, str(e)

    def create_order(self, order: Order, pickup_location_id=None):
        """Create an order in Shiprocket"""
        url = f"{self.api_url}/orders/create/adhoc"
        headers = self._get_headers()

        # Get pickup location if not provided
        if not pickup_location_id:
            locations, error = self.get_pickup_locations()
            if error or not locations:
                return None, "No pickup locations available"
            pickup_location_id = locations[0].get('id')

        # Calculate total weight (estimate 0.5kg per item if not available)
        total_weight = sum(item.quantity * 0.5 for item in order.items.all())

        # Build order items
        order_items = []
        for item in order.items.all():
            product_name = "Product"
            if item.variant and item.variant.product:
                product_name = item.variant.product.name
            elif item.product:
                product_name = item.product.name

            order_items.append({
                "name": product_name,
                "sku": item.variant.sku if item.variant else f"SKU-{item.id}",
                "units": int(item.quantity),
                "selling_price": float(item.unit_price)
            })

        payload = {
            "order_id": str(order.id),
            "order_date": order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "pickup_location": pickup_location_id,
            "billing_customer_name": order.full_name,
            "billing_last_name": "",
            "billing_address": order.address_line1,
            "billing_address_2": order.address_line2 or "",
            "billing_city": order.city,
            "billing_state": order.state or "",
            "billing_pincode": order.postal_code,
            "billing_country": order.country or "India",
            "billing_email": order.email,
            "billing_phone": order.phone,
            "shipping_is_billing": True,
            "order_items": order_items,
            "payment_method": "Prepaid" if order.payment_method == Order.PaymentMethod.RAZORPAY else "COD",
            "sub_total": float(order.subtotal),
            "length": 10,
            "breadth": 10,
            "height": 10,
            "weight": total_weight
        }

        # Add COD amount if COD
        if order.payment_method == Order.PaymentMethod.COD:
            payload["cod_amount"] = float(order.total_cost)

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            # Update order with Shiprocket order ID
            sr_order_id = result.get('order_id')
            if sr_order_id:
                order.shipping_id = str(sr_order_id)
                order.courier_name = "Shiprocket"
                order.save(update_fields=['shipping_id', 'courier_name'])
            
            return result, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create Shiprocket order for order {order.id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_text = e.response.text
                    logger.error(f"Shiprocket API error response: {error_text}")
                except:
                    pass
            return None, str(e)

    def assign_awb(self, shipment_id, courier_id=None):
        """Assign AWB to a shipment"""
        url = f"{self.api_url}/orders/assign/awb"
        headers = self._get_headers()
        payload = {
            "shipment_id": shipment_id
        }
        if courier_id:
            payload["courier_id"] = courier_id

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to assign AWB for shipment {shipment_id}: {e}")
            return None, str(e)

    def track_shipment(self, awb=None, order_id=None):
        """Track a shipment by AWB or order ID"""
        if awb:
            url = f"{self.api_url}/courier/track/awb/{awb}"
        elif order_id:
            url = f"{self.api_url}/orders/tracking/{order_id}"
        else:
            return None, "Either awb or order_id is required"

        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to track Shiprocket shipment: {e}")
            return None, str(e)

    def generate_pickup_request(self, shipment_ids):
        """Generate pickup request for shipments"""
        url = f"{self.api_url}/courier/generate/pickup"
        headers = self._get_headers()
        payload = {
            "shipment_id": shipment_ids if isinstance(shipment_ids, list) else [shipment_ids]
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to generate pickup request: {e}")
            return None, str(e)

    def generate_manifest(self, shipment_ids):
        """Generate manifest for shipments"""
        url = f"{self.api_url}/manifests/generate"
        headers = self._get_headers()
        payload = {
            "shipment_id": shipment_ids if isinstance(shipment_ids, list) else [shipment_ids]
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to generate manifest: {e}")
            return None, str(e)

    def create_shipment(self, order: Order, pickup_location_id=None):
        """Create shipment for an order (creates order and assigns AWB)"""
        # Create order first
        order_result, error = self.create_order(order, pickup_location_id)
        if error:
            return None, error

        sr_order_id = order_result.get('order_id')
        if not sr_order_id:
            return None, "Order created but no order_id returned"

        # Get shipment ID from order
        shipment_id = order_result.get('shipment_id')
        if not shipment_id:
            # Try to get from order details
            return order_result, None

        # Assign AWB
        awb_result, awb_error = self.assign_awb(shipment_id)
        if awb_error:
            logger.warning(f"Order created but AWB assignment failed: {awb_error}")
        
        # Update order with tracking number if AWB assigned
        if awb_result and awb_result.get('awb_code'):
            order.tracking_number = awb_result.get('awb_code')
            order.save(update_fields=['tracking_number'])

        return order_result, None


# Convenience function for backward compatibility
def create_shipment(order: Order):
    """Convenience function to create a shipment - tries Shiprocket first, falls back to Delhivery"""
    # Check if Shiprocket is configured
    shiprocket_email = getattr(settings, 'SHIPROCKET_API_EMAIL', None)
    shiprocket_password = getattr(settings, 'SHIPROCKET_API_PASSWORD', None)
    
    if shiprocket_email and shiprocket_password:
        try:
            service = ShiprocketService()
            return service.create_shipment(order)
        except Exception as e:
            logger.warning(f"Shiprocket failed, falling back to Delhivery: {e}")
    
    # Fallback to Delhivery
    service = DelhiveryService()
    return service.create_shipment(order)
