"""
Middleware for currency detection and request context.
"""
from .currency_utils import get_currency_from_request


class CurrencyMiddleware:
    """
    Middleware to detect and set currency on request based on IP, headers, or defaults.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Detect currency and attach to request
        request.currency = get_currency_from_request(request)
        response = self.get_response(request)
        return response

