from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.http import urlencode
from django.urls import reverse
from django.utils.crypto import get_random_string
from email.utils import formataddr
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

def _send_email_with_unique_id(subject, plain_message, html_message, recipient_email, entity_type, entity_id=None):
    """Helper function to send email with unique Message-ID to prevent Gmail collapsing."""
    msg = EmailMultiAlternatives(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient_email],
    )
    msg.attach_alternative(html_message, "text/html")
    # Add unique Message-ID and reference to prevent Gmail from collapsing emails
    unique_id = uuid.uuid4()
    timestamp = int(datetime.now().timestamp())
    msg.extra_headers['Message-ID'] = f'<{unique_id}@space4u.in>'
    if entity_id:
        msg.extra_headers['X-Entity-Ref-ID'] = f'{entity_type}-{entity_id}-{timestamp}'
    else:
        msg.extra_headers['X-Entity-Ref-ID'] = f'{entity_type}-{timestamp}'
    msg.send()

def send_welcome_email(user):
    """Sends a welcome email to a new user."""
    subject = "Welcome to Space4U - Your Otaku Haven!"
    context = {
        'username': user.username,
    }
    html_message = render_to_string('emails/welcome_email.html', context)
    plain_message = render_to_string('emails/welcome_email.txt', context)
    
    _send_email_with_unique_id(subject, plain_message, html_message, user.email, 'welcome', user.id)


def send_verification_email(user, verification_token):
    """Sends an email verification link to a new user."""
    frontend_url = getattr(settings, 'FRONTEND_ORIGINS', ['http://localhost:3000'])[0]
    verification_url = f"{frontend_url}/verify-email?token={verification_token}&email={urlencode({'email': user.email})}"
    
    subject = "Verify Your Space4U Account"
    context = {
        'username': user.username,
        'verification_url': verification_url,
    }
    html_message = render_to_string('emails/verification_email.html', context)
    plain_message = render_to_string('emails/verification_email.txt', context)
    
    _send_email_with_unique_id(subject, plain_message, html_message, user.email, 'verification', user.id)


def send_order_confirmation_email(order):
    """Sends an order confirmation email when an order is created."""
    # Use order email if user doesn't have email, or user email if available
    recipient_email = None
    recipient_name = None
    
    if order.user and order.user.email:
        recipient_email = order.user.email
        recipient_name = order.user.username or order.full_name
    elif order.email:
        recipient_email = order.email
        recipient_name = order.full_name
    
    if not recipient_email:
        logger.warning(f"No email found for order {order.id}")
        return
    
    frontend_url = getattr(settings, 'FRONTEND_ORIGINS', ['http://localhost:3000'])[0]
    order_url = f"{frontend_url}/orders/{order.id}"
    
    subject = f"Order Confirmation - #{order.order_number or order.id}"
    context = {
        'username': recipient_name or 'Valued Customer',
        'order_number': order.order_number or order.id,
        'order_id': order.id,
        'order_status': order.status,
        'order_date': order.created_at,
        'items': order.items.all(),
        'subtotal': order.subtotal,
        'discount_amount': order.discount_amount,
        'gift_wrap_amount': order.gift_wrap_amount if order.gift_wrap else 0,
        'total_cost': order.total_cost,
        'payment_method': dict(order.PaymentMethod.choices).get(order.payment_method, order.payment_method),
        'shipping_address': {
            'full_name': order.full_name,
            'address_line1': order.address_line1,
            'address_line2': order.address_line2,
            'city': order.city,
            'state': order.state,
            'postal_code': order.postal_code,
            'country': order.country,
            'phone': order.phone,
        },
        'order_url': order_url,
    }
    html_message = render_to_string('emails/order_confirmation.html', context)
    plain_message = render_to_string('emails/order_confirmation.txt', context)
    
    _send_email_with_unique_id(subject, plain_message, html_message, recipient_email, 'order-confirmation', order.id)


def send_shipping_update_email(order):
    """Sends a shipping update email when order status changes."""
    # Use order email if user doesn't have email, or user email if available
    recipient_email = None
    recipient_name = None
    
    if order.user and order.user.email:
        recipient_email = order.user.email
        recipient_name = order.user.username or order.full_name
    elif order.email:
        recipient_email = order.email
        recipient_name = order.full_name
    
    if not recipient_email:
        logger.warning(f"No email found for order {order.id}")
        return
    
    frontend_url = getattr(settings, 'FRONTEND_ORIGINS', ['http://localhost:3000'])[0]
    order_url = f"{frontend_url}/orders/{order.id}"
    
    # Personalized status messages
    status_messages = {
        'PENDING_PAYMENT': 'Your order is waiting for payment confirmation.',
        'PROCESSING': 'Great news! Your order is being prepared for shipment.',
        'PAID': 'Payment received! Your order is being processed.',
        'SHIPPED': 'Your order has been shipped! Track it below.',
        'COMPLETED': 'Your order has been delivered! We hope you love your items.',
        'CANCELLED': 'Your order has been cancelled.',
    }
    
    status_display = dict(order.Status.choices).get(order.status, order.status)
    subject = f"Order #{order.order_number or order.id} Update - {status_display}"
    context = {
        'username': recipient_name or 'Valued Customer',
        'order_number': order.order_number or order.id,
        'order_id': order.id,
        'order_status': order.status,
        'order_status_display': dict(order.Status.choices).get(order.status, order.status),
        'status_message': status_messages.get(order.status, 'Your order status has been updated.'),
        'tracking_number': order.tracking_number,
        'courier_name': order.courier_name,
        'items': order.items.all(),
        'total_cost': order.total_cost,
        'order_url': order_url,
    }
    html_message = render_to_string('emails/shipping_update.html', context)
    plain_message = render_to_string('emails/shipping_update.txt', context)
    
    # Include order ID and status in reference to make each status update unique
    _send_email_with_unique_id(subject, plain_message, html_message, recipient_email, f'order-{order.status}', order.id)


def send_loyalty_tier_update_email(user, old_tier, new_tier):
    """Sends an email when a user's loyalty tier changes."""
    subject = f"Congratulations! You've Reached {new_tier} Tier!"
    context = {
        'username': user.username,
        'old_tier': old_tier,
        'new_tier': new_tier,
        'loyalty_points': user.loyalty_points,
    }
    html_message = render_to_string('emails/loyalty_tier_update.html', context)
    plain_message = render_to_string('emails/loyalty_tier_update.txt', context)
    
    _send_email_with_unique_id(subject, plain_message, html_message, user.email, 'loyalty-tier', user.id)


def send_abandoned_cart_reminder(user, cart_items, days_abandoned=1):
    """Sends a reminder email for abandoned cart items."""
    subject = "Don't Forget Your Items! 🛒"
    frontend_url = getattr(settings, 'FRONTEND_ORIGINS', ['http://localhost:3000'])[0]
    cart_url = f"{frontend_url}/cart"
    
    context = {
        'username': user.username,
        'cart_items': cart_items,
        'cart_url': cart_url,
        'days_abandoned': days_abandoned,
    }
    html_message = render_to_string('emails/abandoned_cart_reminder.html', context)
    plain_message = render_to_string('emails/abandoned_cart_reminder.txt', context)
    
    _send_email_with_unique_id(subject, plain_message, html_message, user.email, 'cart-reminder', user.id)


def send_wishlist_reminder(user, wishlist_items):
    """Sends a reminder email for wishlist items."""
    subject = "Items in Your Wishlist Are Waiting! ⭐"
    frontend_url = getattr(settings, 'FRONTEND_ORIGINS', ['http://localhost:3000'])[0]
    wishlist_url = f"{frontend_url}/wishlist"
    
    context = {
        'username': user.username,
        'wishlist_items': wishlist_items,
        'wishlist_url': wishlist_url,
    }
    html_message = render_to_string('emails/wishlist_reminder.html', context)
    plain_message = render_to_string('emails/wishlist_reminder.txt', context)
    
    _send_email_with_unique_id(subject, plain_message, html_message, user.email, 'wishlist-reminder', user.id)


def send_promotional_email(user, subject_text, message_text, offer_code=None, offer_url=None):
    """Sends a promotional/offer email to a user."""
    frontend_url = getattr(settings, 'FRONTEND_ORIGINS', ['http://localhost:3000'])[0]
    shop_url = offer_url or f"{frontend_url}/shop"
    
    context = {
        'username': user.username,
        'subject': subject_text,
        'message': message_text,
        'offer_code': offer_code,
        'shop_url': shop_url,
    }
    html_message = render_to_string('emails/promotional_email.html', context)
    plain_message = render_to_string('emails/promotional_email.txt', context)
    
    _send_email_with_unique_id(subject_text, plain_message, html_message, user.email, 'promotional', user.id)
