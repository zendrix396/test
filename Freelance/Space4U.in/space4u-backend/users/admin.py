from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, LoyaltyConfig, LoyaltyTransaction, WalletTransaction, ReferralCode, Referral, Badge, UserBadge, ReferralConfig, EmailReminderConfig

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        'username',
        'email',
        'display_name',
        'first_name',
        'last_name',
        'is_staff',
        'loyalty_points',
        'loyalty_tier',
    )
    fieldsets = UserAdmin.fieldsets + (
        ('Profile', {
            'fields': (
                'display_name',
                'phone_number',
                'bio',
                'profile_image',
            )
        }),
        ('Loyalty & Wallet', {'fields': ('loyalty_points', 'wallet_balance', 'loyalty_tier')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile', {'fields': ('display_name', 'phone_number')}),
        ('Loyalty & Wallet', {'fields': ('loyalty_points', 'wallet_balance', 'loyalty_tier')}),
    )

@admin.register(LoyaltyConfig)
class LoyaltyConfigAdmin(admin.ModelAdmin):
    list_display = ('enabled', 'points_per_currency', 'points_to_wallet_ratio')

@admin.register(ReferralConfig)
class ReferralConfigAdmin(admin.ModelAdmin):
    list_display = ('enabled', 'referrer_points', 'referred_points')

@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'reason', 'created_at')
    list_filter = ('user',)
    search_fields = ('user__username', 'reason')

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'kind', 'reference', 'created_at')
    list_filter = ('kind', 'user')
    search_fields = ('user__username', 'reference')

@admin.register(EmailReminderConfig)
class EmailReminderConfigAdmin(admin.ModelAdmin):
    list_display = ('enabled', 'cart_reminder_days', 'cart_reminder_frequency', 'wishlist_reminder_days', 'wishlist_reminder_frequency')
    fieldsets = (
        ('General', {
            'fields': ('enabled',)
        }),
        ('Cart Reminders', {
            'fields': ('cart_reminder_days', 'cart_reminder_frequency', 'max_cart_reminders')
        }),
        ('Wishlist Reminders', {
            'fields': ('wishlist_reminder_days', 'wishlist_reminder_frequency', 'max_wishlist_reminders')
        }),
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(ReferralCode)
admin.site.register(Referral)
admin.site.register(Badge)
admin.site.register(UserBadge)

