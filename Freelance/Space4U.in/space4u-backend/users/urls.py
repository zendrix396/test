from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    UserRegistrationView,
    GoogleLoginView,
    MeView,
    MyOrdersView,
    MyOrderDetailView,
    MyReferralView,
    LeaderboardView,
    LoyaltyConfigView,
    ReferralCodeView,
    RedeemLoyaltyPointsView,
    ReferralConfigView,
    ValidateReferralCodeView,
    UserAddressListView,
    UserAddressDetailView,
    SetUsernameView,
    CustomRegisterView,
)

app_name = "users"

urlpatterns = [
    path("jwt/create/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("jwt/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path('registration/', CustomRegisterView.as_view(), name='rest_register'),
    path("google/", GoogleLoginView.as_view(), name="google_login"),
    path("me/", MeView.as_view(), name="me"),
    path("orders/", MyOrdersView.as_view(), name="my_orders"),
    path("orders/<int:order_id>/", MyOrderDetailView.as_view(), name="my_order_detail"),
    path("referrals/", MyReferralView.as_view(), name="my_referral"),
    path("referral-code/", ReferralCodeView.as_view(), name="referral_code"),
    path("referral-config/", ReferralConfigView.as_view(), name="referral_config"),
    path("validate-referral-code/", ValidateReferralCodeView.as_view(), name="validate_referral_code"),
    path("leaderboard/", LeaderboardView.as_view(), name="leaderboard"),
    path("loyalty-config/", LoyaltyConfigView.as_view(), name="loyalty_config"),
    path("redeem-points/", RedeemLoyaltyPointsView.as_view(), name="redeem_points"),
    path("addresses/", UserAddressListView.as_view(), name="user_address_list"),
    path("addresses/<int:pk>/", UserAddressDetailView.as_view(), name="user_address_detail"),
    path("set-username/", SetUsernameView.as_view(), name="set_username"),
]


