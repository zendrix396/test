"""
Signal handlers for user-related events.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.socialaccount.signals import social_account_added
from .models import CustomUser
import logging

logger = logging.getLogger(__name__)


@receiver(social_account_added)
def handle_social_account_added(sender, request, sociallogin, **kwargs):
    """
    When a social account is added (e.g., Google OAuth), 
    ensure the user has a username. If not, generate one from email.
    """
    user = sociallogin.user
    if user and user.pk:
        # Check if username is missing or empty
        if not user.username or user.username.strip() == '':
            # Generate username from email
            email = user.email
            if email:
                # Use the part before @ as username base
                username_base = email.split('@')[0]
                # Clean the username (remove invalid characters)
                username_base = ''.join(c for c in username_base if c.isalnum() or c in ['_', '-'])
                
                # Ensure it's not empty and has minimum length
                if len(username_base) < 3:
                    username_base = f"user{user.id}"
                
                # Check if username already exists, if so append user ID
                username = username_base
                counter = 1
                while CustomUser.objects.filter(username=username).exclude(id=user.id).exists():
                    username = f"{username_base}{counter}"
                    counter += 1
                
                user.username = username
                user.save(update_fields=['username'])
                logger.info(f"Auto-generated username '{username}' for user {user.email}")


@receiver(post_save, sender=CustomUser)
def handle_user_created(sender, instance, created, **kwargs):
    """
    When a user is created, ensure they have a username.
    This handles cases where users are created without usernames.
    """
    if created and (not instance.username or instance.username.strip() == ''):
        # Generate username from email
        email = instance.email
        if email:
            # Use the part before @ as username base
            username_base = email.split('@')[0]
            # Clean the username (remove invalid characters)
            username_base = ''.join(c for c in username_base if c.isalnum() or c in ['_', '-'])
            
            # Ensure it's not empty and has minimum length
            if len(username_base) < 3:
                username_base = f"user{instance.id}"
            
            # Check if username already exists, if so append user ID
            username = username_base
            counter = 1
            while CustomUser.objects.filter(username=username).exclude(id=instance.id).exists():
                username = f"{username_base}{counter}"
                counter += 1
            
            instance.username = username
            # Use update to avoid recursion
            CustomUser.objects.filter(id=instance.id).update(username=username)
            logger.info(f"Auto-generated username '{username}' for user {instance.email}")

