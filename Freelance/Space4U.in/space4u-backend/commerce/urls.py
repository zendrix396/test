from django.urls import path
from .views import (
    WishlistView,
    SavedForLaterView,
    CartView,
    CartGiftWrapView,
    CartCouponView,
    CreatePreliminaryOrderView,
    CreateRazorpayOrderView,
    RazorpayWebhookView,
    ApplyCouponView,
    ReturnRequestListView,
    ReturnRequestView,
    RecentlyViewedView,
    InvoiceTexView,
    InvoicePDFView,
    InternalInvoicePDFView,
    VerifyRazorpayPaymentView,
    CancelOrderView,
    OrderListView,
    OrderDetailView,
    GiftCardListView,
    GiftCardIssueView,
    GiftCardRedeemView,
)

app_name = "commerce"

urlpatterns = [
    path("wishlist/", WishlistView.as_view(), name="wishlist"),
    path("saved-for-later/", SavedForLaterView.as_view(), name="saved_for_later"),
    path("recently-viewed/", RecentlyViewedView.as_view(), name="recently_viewed"),
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/gift-wrap/", CartGiftWrapView.as_view(), name="cart_gift_wrap"),
    path("cart/apply-coupon/", CartCouponView.as_view(), name="cart_apply_coupon"),
    path("orders/create/", CreatePreliminaryOrderView.as_view(), name="create_order"),
    path("orders/apply-coupon/", ApplyCouponView.as_view(), name="apply_coupon"),
    path("orders/create-payment/", CreateRazorpayOrderView.as_view(), name="create_payment"),
    path("orders/verify-payment/", VerifyRazorpayPaymentView.as_view(), name="verify_payment"),
    path("orders/cancel/", CancelOrderView.as_view(), name="cancel_order"),
    path("orders/<int:order_id>/", OrderDetailView.as_view(), name="order_detail"),
    path("orders/", OrderListView.as_view(), name="order_list"),
    path("webhooks/razorpay/", RazorpayWebhookView.as_view(), name="razorpay_webhook"),
    path("returns/", ReturnRequestListView.as_view(), name="list_returns"),
    path("returns/create/", ReturnRequestView.as_view(), name="create_return"),
    path("invoices/tex/<int:order_id>/", InvoiceTexView.as_view(), name="invoice_tex"),
    path("invoices/pdf/<int:order_id>/", InvoicePDFView.as_view(), name="invoice_pdf"),
    path("invoices/internal/<int:order_id>/", InternalInvoicePDFView.as_view(), name="internal_invoice_pdf"),
    path("giftcards/", GiftCardListView.as_view(), name="giftcard_list"),
    path("giftcards/issue/", GiftCardIssueView.as_view(), name="giftcard_issue"),
    path("giftcards/redeem/", GiftCardRedeemView.as_view(), name="giftcard_redeem"),
]


