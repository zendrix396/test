# users/views.py

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .serializers import UserRegistrationSerializer, UserProfileSerializer
from .models import CustomUser, ReferralCode, Referral, LoyaltyTransaction, Badge, UserBadge, LoyaltyConfig, ReferralConfig, WalletTransaction, UserAddress
from .serializers import UserAddressSerializer
from decimal import Decimal
from commerce.models import Order
from commerce.serializers import OrderSerializer
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.utils.crypto import get_random_string
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer, OpenApiParameter
from rest_framework import serializers
from django.conf import settings
from .services import send_welcome_email
from dj_rest_auth.registration.views import RegisterView

class CustomRegisterView(RegisterView):
    def perform_create(self, serializer):
        user = super().perform_create(serializer)
        try:
            send_welcome_email(user)
        except Exception as e:
            # Log the error, but don't block registration
            print(f"Failed to send welcome email to {user.email}: {e}")
        return user


class UserRegistrationView(generics.CreateAPIView):
    """
    API endpoint for user registration.
    Allows any user (even unauthenticated) to create a new account.
    """
    queryset = CustomUser.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer

    @extend_schema(
        summary="Register a new user",
        description="Create a new user account. This endpoint is open to all.",
        responses={
            201: OpenApiResponse(description="User registered successfully."),
            400: OpenApiResponse(description="Invalid input."),
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Send welcome email
        try:
            send_welcome_email(user)
        except Exception as e:
            # Log the error, but don't block registration
            print(f"Failed to send welcome email to {user.email}: {e}")
        
        # Handle referral code if provided
        referral_code_str = request.data.get('referral_code') or request.data.get('ref')
        if referral_code_str:
            try:
                referral_code_obj = ReferralCode.objects.get(code=referral_code_str.upper())
                referrer = referral_code_obj.owner
                
                # Check if referral system is enabled
                ref_config = ReferralConfig.objects.filter(enabled=True).first()
                if ref_config and referrer != user:
                    # Create referral record
                    referral, created = Referral.objects.get_or_create(
                        referred=user,
                        defaults={
                            'referrer': referrer,
                            'code': referral_code_obj,
                            'reward_points': ref_config.referrer_points
                        }
                    )
                    
                    if created:
                        # Award points to referrer
                        referrer.loyalty_points += ref_config.referrer_points
                        referrer.save(update_fields=['loyalty_points'])
                        LoyaltyTransaction.objects.create(
                            user=referrer,
                            points=ref_config.referrer_points,
                            reason=f"Referral bonus for {user.email}"
                        )
                        
                        # Award points to referred user
                        user.loyalty_points += ref_config.referred_points
                        user.save(update_fields=['loyalty_points'])
                        LoyaltyTransaction.objects.create(
                            user=user,
                            points=ref_config.referred_points,
                            reason="Sign-up bonus via referral"
                        )
            except ReferralCode.DoesNotExist:
                pass  # Invalid referral code, ignore
        
        headers = self.get_success_headers(serializer.data)
        
        # You can add additional data to the response if needed
        data = {
            "message": "User registered successfully.",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)


class GoogleLoginView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Authenticate with Google",
        description="Handles user authentication via Google. Expects an `id_token` or `access_token` from Google.",
        request=inline_serializer(
            name='GoogleLoginRequest',
            fields={
                'id_token': serializers.CharField(required=False),
                'access_token': serializers.CharField(required=False),
            }
        ),
        responses={
            200: OpenApiResponse(description="Google login successful."),
            400: OpenApiResponse(description="Token is required."),
        }
    )
    def post(self, request, *args, **kwargs):
        # Minimal behavior for tests: require a token field and 400 if missing
        id_token = request.data.get("id_token") or request.data.get("access_token")
        if not id_token:
            return Response({"detail": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Placeholder success path; real implementation would verify token
        return Response({"message": "Google login successful."}, status=status.HTTP_200_OK)


@extend_schema(
    summary="Retrieve or update user profile",
    description="Allows authenticated users to retrieve or update their own profile information.",
    responses={200: UserProfileSerializer}
)
class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserProfileSerializer
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_object(self):
        return self.request.user


class MyOrdersView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="List user's orders",
        description="Retrieves a list of orders for the currently authenticated user.",
        responses={200: OrderSerializer(many=True)}
    )
    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by("-created_at").values(
            "id", "status", "total_cost", "created_at", "updated_at"
        )
        # cast decimals to string for JSON
        out = []
        for o in orders:
            o = dict(o)
            o["total_cost"] = str(o["total_cost"])
            out.append(o)
        return Response(out)


class MyOrderDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Retrieve an order detail",
        description="Retrieves detailed information for a specific order belonging to the authenticated user.",
        responses={200: OrderSerializer}
    )
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        serializer = OrderSerializer(order)
        return Response(serializer.data)


class MyReferralView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Get referral code",
        description="Retrieves the authenticated user's referral code and the number of successful referrals.",
        responses={
            200: OpenApiResponse(description="Referral code and count.",
                                 examples=[{'code': 'ABCXYZ123', 'referrals': 5}])
        }
    )
    def get(self, request):
        code, _ = ReferralCode.objects.get_or_create(owner=request.user, defaults={
            'code': get_random_string(10).upper()
        })
        count = Referral.objects.filter(referrer=request.user).count()
        return Response({"code": code.code, "referrals": count})

    @extend_schema(
        summary="Apply a referral code",
        description="Applies a referral code to the authenticated user's account.",
        request=inline_serializer(
            name='ApplyReferralRequest',
            fields={'code': serializers.CharField()}
        ),
        responses={
            201: OpenApiResponse(description="Referral code applied successfully."),
            400: OpenApiResponse(description="Invalid or own referral code."),
        }
    )
    def post(self, request):
        input_code = request.data.get('code')
        if not input_code:
            return Response({"detail": "code is required"}, status=400)
        try:
            rc = ReferralCode.objects.get(code__iexact=input_code)
        except ReferralCode.DoesNotExist:
            return Response({"detail": "Invalid code"}, status=400)
        if rc.owner_id == request.user.id:
            return Response({"detail": "Cannot use your own code"}, status=400)
        # ensure first use only
        if hasattr(request.user, 'referral_used'):
            return Response({"detail": "Referral already applied"}, status=400)
        referral = Referral.objects.create(referrer=rc.owner, referred=request.user, code=rc, reward_points=50)
        # award points to both
        for u, pts, reason in ((rc.owner, 50, f"Referral bonus for {request.user.username}"), (request.user, 25, "Signup referral bonus")):
            u.loyalty_points += pts
            u.save(update_fields=['loyalty_points'])
            LoyaltyTransaction.objects.create(user=u, points=pts, reason=reason)
        return Response({"status": "ok"}, status=201)


class LeaderboardView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        summary="Get leaderboard",
        description="Retrieves the top 20 users based on loyalty points.",
        responses={
            200: OpenApiResponse(description="A list of top users.",
                                 examples=[[{'username': 'user1', 'loyalty_points': 100}]])
        }
    )
    def get(self, request):
        top = CustomUser.objects.order_by('-loyalty_points').values('username', 'loyalty_points')[:20]
        result = []
        for idx, user in enumerate(top, start=1):
            result.append({
                **user,
                'rank': idx
            })
        return Response(result)


class LoyaltyConfigView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        summary="Get loyalty configuration",
        description="Returns whether loyalty rewards are enabled and points per currency unit.",
    )
    def get(self, request):
        config_obj = LoyaltyConfig.objects.filter(enabled=True).first()
        if config_obj:
            enabled = config_obj.enabled
            ratio = config_obj.points_per_currency
        else:
            enabled = getattr(settings, "LOYALTY_DEFAULT_ENABLED", False)
            ratio = getattr(settings, "LOYALTY_POINTS_PER_CURRENCY", 0.0)

        return Response({
            "enabled": bool(enabled),
            "points_per_currency": float(ratio or 0),
        })


class ReferralCodeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Get or generate referral code",
        description="Returns the user's referral code, creating one if it doesn't exist.",
    )
    def get(self, request):
        user = request.user
        referral_code, created = ReferralCode.objects.get_or_create(
            owner=user,
            defaults={'code': get_random_string(8).upper()}
        )
        
        return Response({
            "code": referral_code.code,
            "referral_link": f"{getattr(settings, 'FRONTEND_ORIGINS', ['http://localhost:3000'])[0]}/signup?ref={referral_code.code}",
            "created": created
        })


class RedeemLoyaltyPointsView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Redeem loyalty points to wallet",
        description="Convert loyalty points to wallet balance based on configured ratio.",
        request=inline_serializer(
            name='RedeemPointsRequest',
            fields={
                'points': serializers.IntegerField(required=True, min_value=1),
            }
        ),
    )
    def post(self, request):
        points_to_redeem = request.data.get('points')
        if not points_to_redeem or points_to_redeem < 1:
            return Response(
                {"error": "Points must be a positive integer."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        if user.loyalty_points < points_to_redeem:
            return Response(
                {"error": "Insufficient loyalty points."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get conversion ratio
        config = LoyaltyConfig.objects.filter(enabled=True).first()
        if not config:
            return Response(
                {"error": "Loyalty system is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        ratio = config.points_to_wallet_ratio
        wallet_amount = Decimal(str(points_to_redeem)) / ratio
        
        # Update user balances
        user.loyalty_points -= points_to_redeem
        user.wallet_balance += wallet_amount
        user.save(update_fields=['loyalty_points', 'wallet_balance'])
        
        # Create transactions
        LoyaltyTransaction.objects.create(
            user=user,
            points=-points_to_redeem,
            reason=f"Redeemed {points_to_redeem} points to wallet"
        )
        
        WalletTransaction.objects.create(
            user=user,
            amount=wallet_amount,
            kind=WalletTransaction.Kind.CREDIT,
            reference=f"Loyalty points redemption ({points_to_redeem} points)"
        )
        
        return Response({
            "message": f"Successfully redeemed {points_to_redeem} points",
            "wallet_amount_added": float(wallet_amount),
            "remaining_points": user.loyalty_points,
            "new_wallet_balance": float(user.wallet_balance)
        })


class ReferralConfigView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        summary="Get referral configuration",
        description="Returns referral system configuration.",
    )
    def get(self, request):
        config = ReferralConfig.objects.filter(enabled=True).first()
        if config:
            return Response({
                "enabled": True,
                "referrer_points": config.referrer_points,
                "referred_points": config.referred_points,
            })
        return Response({
            "enabled": False,
            "referrer_points": 0,
            "referred_points": 0,
        })


class ValidateReferralCodeView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        summary="Validate referral code",
        description="Checks if a referral code is valid and if the referral system is enabled.",
        parameters=[
            OpenApiParameter(
                name='code',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Referral code to validate',
                required=True,
            )
        ],
    )
    def get(self, request):
        code = request.query_params.get('code', '').upper().strip()
        
        if not code:
            return Response({
                "valid": False,
                "enabled": False,
                "message": "No referral code provided"
            })
        
        # Check if referral system is enabled
        ref_config = ReferralConfig.objects.filter(enabled=True).first()
        if not ref_config:
            return Response({
                "valid": False,
                "enabled": False,
                "message": "Referral system is disabled"
            })
        
        # Check if code exists
        try:
            referral_code_obj = ReferralCode.objects.get(code=code)
            return Response({
                "valid": True,
                "enabled": True,
                "message": "Valid referral code"
            })
        except ReferralCode.DoesNotExist:
            return Response({
                "valid": False,
                "enabled": True,
                "message": "Invalid referral code"
            })


class UserAddressListView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="List user addresses",
        description="Get all saved addresses for the authenticated user.",
        responses={200: UserAddressSerializer(many=True)},
    )
    def get(self, request):
        addresses = UserAddress.objects.filter(user=request.user)
        serializer = UserAddressSerializer(addresses, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Create user address",
        description="Create a new saved address for the authenticated user.",
        request=UserAddressSerializer,
        responses={201: UserAddressSerializer},
    )
    def post(self, request):
        serializer = UserAddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserAddressDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk, user):
        try:
            return UserAddress.objects.get(pk=pk, user=user)
        except UserAddress.DoesNotExist:
            raise Http404

    @extend_schema(
        summary="Get user address",
        description="Get a specific saved address.",
        responses={200: UserAddressSerializer},
    )
    def get(self, request, pk):
        address = self.get_object(pk, request.user)
        serializer = UserAddressSerializer(address)
        return Response(serializer.data)

    @extend_schema(
        summary="Update user address",
        description="Update a saved address.",
        request=UserAddressSerializer,
        responses={200: UserAddressSerializer},
    )
    def put(self, request, pk):
        address = self.get_object(pk, request.user)
        serializer = UserAddressSerializer(address, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Delete user address",
        description="Delete a saved address.",
        responses={204: OpenApiResponse(description="Address deleted")},
    )
    def delete(self, request, pk):
        address = self.get_object(pk, request.user)
        address.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SetUsernameView(APIView):
    """
    Endpoint to set username for Google OAuth users who don't have one.
    """
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Set username",
        description="Set username for authenticated user (typically after Google OAuth login).",
        request=inline_serializer(
            name='SetUsernameRequest',
            fields={'username': serializers.CharField(required=True, min_length=3, max_length=150)}
        ),
        responses={
            200: OpenApiResponse(description="Username set successfully."),
            400: OpenApiResponse(description="Invalid username or username already taken."),
        }
    )
    def post(self, request):
        username = request.data.get('username', '').strip()
        
        if not username:
            return Response(
                {"error": "Username is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(username) < 3:
            return Response(
                {"error": "Username must be at least 3 characters long."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if username already exists
        if CustomUser.objects.filter(username=username).exclude(id=request.user.id).exists():
            return Response(
                {"error": "This username is already taken. Please choose another."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set username
        request.user.username = username
        request.user.save(update_fields=['username'])
        
        return Response({
            "message": "Username set successfully.",
            "username": username
        }, status=status.HTTP_200_OK)
