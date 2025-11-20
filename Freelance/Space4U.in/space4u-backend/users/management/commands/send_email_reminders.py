from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from users.models import CustomUser, EmailReminderConfig
from commerce.models import Cart, CartItem
from users.services import send_abandoned_cart_reminder, send_wishlist_reminder
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sends email reminders for abandoned carts and wishlists based on configured frequency'

    def handle(self, *args, **options):
        config = EmailReminderConfig.objects.filter(enabled=True).first()
        if not config:
            self.stdout.write(self.style.WARNING('Email reminders are disabled. No emails sent.'))
            return

        self.stdout.write('Starting email reminder process...')
        
        # Process abandoned carts
        self.process_abandoned_carts(config)
        
        # Process wishlist reminders (if wishlist model exists)
        # self.process_wishlist_reminders(config)
        
        self.stdout.write(self.style.SUCCESS('Email reminder process completed.'))

    def process_abandoned_carts(self, config):
        """Process abandoned cart reminders"""
        self.stdout.write('Processing abandoned carts...')
        
        # Get carts that haven't been updated in the configured days
        cutoff_date = timezone.now() - timedelta(days=config.cart_reminder_days)
        abandoned_carts = Cart.objects.filter(
            updated_at__lte=cutoff_date,
            items__isnull=False
        ).distinct()
        
        sent_count = 0
        for cart in abandoned_carts:
            if not cart.user or not cart.user.email:
                continue
            
            # Calculate days since last update
            days_abandoned = (timezone.now() - cart.updated_at).days
            
            # Check if we should send a reminder based on frequency
            if days_abandoned % config.cart_reminder_frequency == 0:
                # Count how many reminders we've sent (simplified - in production, track this)
                # For now, just check if it's within max reminders
                reminder_number = days_abandoned // config.cart_reminder_frequency
                if reminder_number <= config.max_cart_reminders:
                    try:
                        cart_items = cart.items.all()
                        if cart_items.exists():
                            send_abandoned_cart_reminder(cart.user, cart_items, days_abandoned)
                            sent_count += 1
                            self.stdout.write(f'Sent cart reminder to {cart.user.email} (abandoned {days_abandoned} days)')
                    except Exception as e:
                        logger.error(f"Failed to send cart reminder to {cart.user.email}: {e}")
                        self.stdout.write(self.style.ERROR(f'Error sending to {cart.user.email}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'Sent {sent_count} cart reminder emails.'))

    def process_wishlist_reminders(self, config):
        """Process wishlist reminders (placeholder - implement when wishlist model exists)"""
        # TODO: Implement when wishlist model is available
        self.stdout.write('Wishlist reminders not yet implemented.')
        pass

