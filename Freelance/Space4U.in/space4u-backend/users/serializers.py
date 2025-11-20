# users/serializers.py

from decimal import Decimal

from django.db.models import Count, Sum, Q
from django.db.models.functions import Coalesce
from rest_framework import serializers

from .models import CustomUser, LoyaltyConfig, UserAddress
from commerce.models import Order

class LoyaltyConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyConfig
        fields = ('enabled', 'points_per_currency')

class UserProfileSerializer(serializers.ModelSerializer):
    loyalty_points = serializers.IntegerField(read_only=True)
    wallet_balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)
    profile_image_url = serializers.SerializerMethodField()
    order_stats = serializers.SerializerMethodField()
    loyalty_config = LoyaltyConfigSerializer(source='loyaltyconfig', read_only=True)
    remove_profile_image = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'username',
            'email',
            'display_name',
            'first_name',
            'last_name',
            'phone_number',
            'bio',
            'profile_image',
            'profile_image_url',
            'loyalty_points',
            'wallet_balance',
            'loyalty_tier',
            'order_stats',
            'loyalty_config',
            'remove_profile_image',
        )
        extra_kwargs = {
            'email': {'read_only': True},
        }

    def get_profile_image_url(self, obj):
        if obj.profile_image:
            request = self.context.get('request')
            url = obj.profile_image.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return None

    def get_order_stats(self, obj):
        aggregates = Order.objects.filter(user=obj).aggregate(
            total_orders=Count('id'),
            completed_orders=Count('id', filter=Q(status=Order.Status.COMPLETED)),
            open_orders=Count('id', filter=~Q(status__in=[Order.Status.CANCELLED, Order.Status.COMPLETED])),
            total_spent=Coalesce(Sum('total_cost'), Decimal('0.00')),
        )

        return {
            'total_orders': aggregates['total_orders'] or 0,
            'completed_orders': aggregates['completed_orders'] or 0,
            'open_orders': aggregates['open_orders'] or 0,
            'total_spent': str(aggregates['total_spent'] or Decimal('0.00')),
        }

    def update(self, instance, validated_data):
        profile_image = validated_data.pop('profile_image', serializers.empty)
        remove_image = validated_data.pop('remove_profile_image', False)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if profile_image is not serializers.empty:
            instance.profile_image = profile_image

        if remove_image:
            if instance.profile_image:
                instance.profile_image.delete(save=False)
            instance.profile_image = None

        instance.save()
        return instance

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, label='Confirm Password', style={'input_type': 'password'})

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password', 'password2')
        extra_kwargs = {
            'email': {'required': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = (
            'id',
            'is_default',
            'full_name',
            'phone',
            'email',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'postal_code',
            'country',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')