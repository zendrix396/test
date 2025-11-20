from django.db import models
from django.contrib.auth.models import AbstractUser

# extending the default user model
class CustomUser(AbstractUser):
    loyalty_points = models.IntegerField(default=0)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    loyalty_tier = models.CharField(max_length=20, default='FAN')
    display_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    bio = models.TextField(blank=True)
    profile_image = models.ImageField(upload_to='profile_avatars/', blank=True, null=True)

    # add additional fields here in the future


class LoyaltyTransaction(models.Model):
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='loyalty_transactions')
    points = models.IntegerField()
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.points} points for {self.user_id}"


class WalletTransaction(models.Model):
    class Kind(models.TextChoices):
        CREDIT = 'CREDIT', 'Credit'
        DEBIT = 'DEBIT', 'Debit'

    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='wallet_transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        sign = '-' if self.kind == self.Kind.DEBIT else '+'
        return f"{sign}{self.amount} for {self.user_id}"


class LoyaltyConfig(models.Model):
    enabled = models.BooleanField(default=True)
    points_per_currency = models.FloatField(default=0.0, help_text="Points awarded per 1 unit of currency paid")
    points_to_wallet_ratio = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=100.0,
        help_text="How many loyalty points = 1 unit of wallet currency (e.g., 100 points = ₹1)"
    )

    def __str__(self):
        return f"Loyalty(enabled={self.enabled}, ratio={self.points_per_currency})"


class ReferralConfig(models.Model):
    enabled = models.BooleanField(default=True)
    referrer_points = models.IntegerField(
        default=100,
        help_text="Points awarded to the referrer when someone signs up using their code"
    )
    referred_points = models.IntegerField(
        default=50,
        help_text="Points awarded to the new user when they sign up using a referral code"
    )

    def __str__(self):
        return f"Referral(enabled={self.enabled}, referrer={self.referrer_points}, referred={self.referred_points})"


class ReferralCode(models.Model):
    owner = models.OneToOneField('users.CustomUser', on_delete=models.CASCADE, related_name='referral_code')
    code = models.CharField(max_length=16, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} for {self.owner_id}"


class Referral(models.Model):
    referrer = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='referrals_made')
    referred = models.OneToOneField('users.CustomUser', on_delete=models.CASCADE, related_name='referral_used')
    code = models.ForeignKey(ReferralCode, on_delete=models.PROTECT)
    reward_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.referrer_id} -> {self.referred_id} ({self.reward_points})"


class Badge(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "badge")

    def __str__(self):
        return f"{self.user_id}:{self.badge_id}"


class UserAddress(models.Model):
    """
    Saved addresses for users to enable faster checkout.
    """
    user = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Mark this as the default address for checkout"
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="India")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name = "User Address"
        verbose_name_plural = "User Addresses"

    def __str__(self):
        return f"{self.full_name} - {self.city}, {self.postal_code}"

    def save(self, *args, **kwargs):
        # Ensure only one default address per user
        if self.is_default:
            UserAddress.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class EmailReminderConfig(models.Model):
    """
    Configuration for email reminder frequency for abandoned carts and wishlists.
    Only one active configuration should exist at a time.
    """
    enabled = models.BooleanField(default=True, help_text="Enable/disable email reminders")
    cart_reminder_days = models.IntegerField(
        default=1,
        help_text="Days after cart abandonment to send first reminder"
    )
    cart_reminder_frequency = models.IntegerField(
        default=3,
        help_text="Days between cart reminder emails"
    )
    wishlist_reminder_days = models.IntegerField(
        default=7,
        help_text="Days after adding to wishlist to send first reminder"
    )
    wishlist_reminder_frequency = models.IntegerField(
        default=7,
        help_text="Days between wishlist reminder emails"
    )
    max_cart_reminders = models.IntegerField(
        default=3,
        help_text="Maximum number of cart reminder emails to send"
    )
    max_wishlist_reminders = models.IntegerField(
        default=2,
        help_text="Maximum number of wishlist reminder emails to send"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Email Reminder Configuration"
        verbose_name_plural = "Email Reminder Configurations"

    def __str__(self):
        return f"Email Reminder Config (enabled={self.enabled})"

    def save(self, *args, **kwargs):
        # Ensure only one active configuration
        if self.enabled:
            EmailReminderConfig.objects.filter(enabled=True).exclude(pk=self.pk).update(enabled=False)
        super().save(*args, **kwargs)