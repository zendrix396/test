"""
Currency detection and conversion utilities.
"""
from decimal import Decimal
from django.conf import settings
import os
import logging
import ipaddress

try:
    import geoip2.database
    import geoip2.errors
    GEOIP2_AVAILABLE = True
except ImportError:
    GEOIP2_AVAILABLE = False

logger = logging.getLogger(__name__)

# Country to currency mapping (ISO 3166-1 alpha-2 to ISO 4217)
COUNTRY_CURRENCY_MAP = {
    'IN': 'INR',  # India
    'US': 'USD',  # United States
    'GB': 'GBP',  # United Kingdom
    'CA': 'CAD',  # Canada
    'AU': 'AUD',  # Australia
    'JP': 'JPY',  # Japan
    'EU': 'EUR',  # European Union (fallback)
    'DE': 'EUR',  # Germany
    'FR': 'EUR',  # France
    'IT': 'EUR',  # Italy
    'ES': 'EUR',  # Spain
    'NL': 'EUR',  # Netherlands
    'BE': 'EUR',  # Belgium
    'AT': 'EUR',  # Austria
    'CH': 'CHF',  # Switzerland
    'SE': 'SEK',  # Sweden
    'NO': 'NOK',  # Norway
    'DK': 'DKK',  # Denmark
    'PL': 'PLN',  # Poland
    'BR': 'BRL',  # Brazil
    'MX': 'MXN',  # Mexico
    'AR': 'ARS',  # Argentina
    'CN': 'CNY',  # China
    'KR': 'KRW',  # South Korea
    'SG': 'SGD',  # Singapore
    'HK': 'HKD',  # Hong Kong
    'AE': 'AED',  # UAE
    'SA': 'SAR',  # Saudi Arabia
    'ZA': 'ZAR',  # South Africa
    'NZ': 'NZD',  # New Zealand
}

# Default currency
DEFAULT_CURRENCY = 'INR'

# Currency symbols
CURRENCY_SYMBOLS = {
    'INR': '₹',
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'JPY': '¥',
    'CAD': 'C$',
    'AUD': 'A$',
    'CHF': 'CHF',
    'CNY': '¥',
    'KRW': '₩',
    'SGD': 'S$',
    'HKD': 'HK$',
    'AED': 'د.إ',
    'SAR': '﷼',
    'BRL': 'R$',
    'MXN': '$',
    'ARS': '$',
    'ZAR': 'R',
    'NZD': 'NZ$',
    'SEK': 'kr',
    'NOK': 'kr',
    'DKK': 'kr',
    'PLN': 'zł',
}


def get_country_from_ip(ip_address):
    """
    Get country code from IP address using GeoIP2.
    """
    logger.info(f"Attempting to get country for IP: {ip_address}")
    if not GEOIP2_AVAILABLE:
        logger.warning("GeoIP2 library not installed. Cannot determine country from IP.")
        return None
    if not ip_address:
        logger.warning("No IP address provided to get_country_from_ip.")
        return None

    # FIX: Add this block to ignore private/local IPs
    try:
        ip_obj = ipaddress.ip_address(ip_address)
        if ip_obj.is_private or ip_obj.is_loopback:
            logger.info(f"Skipping GeoIP lookup for private/loopback IP: {ip_address}")
            return None
    except ValueError:
        logger.warning(f"Invalid IP address provided: {ip_address}")
        return None
    # END FIX

    # Path to the GeoLite2 database
    db_path = os.path.join(settings.BASE_DIR, 'geoip_data', 'GeoLite2-Country.mmdb')
    
    try:
        reader = geoip2.database.Reader(db_path)
        response = reader.country(ip_address)
        country_code = response.country.iso_code
        logger.info(f"GeoIP success: IP {ip_address} resolved to country: {country_code}")
        return country_code
    except FileNotFoundError:
        logger.error(
            f"GeoIP database not found at {db_path}. "
            "Please download it from MaxMind and place it in the 'geoip_data' directory. "
            "IP-based currency detection will not work until this is fixed."
        )
        return None
    except geoip2.errors.AddressNotFoundError:
        logger.warning(f"IP address {ip_address} not found in the GeoIP database. (This is common for local/private IPs).")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during GeoIP lookup for IP {ip_address}: {e}")
        return None


def get_currency_from_country(country_code):
    """
    Get currency code from country code.
    """
    if not country_code:
        return DEFAULT_CURRENCY
    return COUNTRY_CURRENCY_MAP.get(country_code.upper(), DEFAULT_CURRENCY)


def get_currency_from_request(request):
    """
    Detect currency from request headers or IP.
    Priority:
    1. X-Currency header (explicit override)
    2. IP-based GeoIP detection
    3. Default currency
    """
    # Check explicit currency header
    currency_header = request.META.get('HTTP_X_CURRENCY', '').upper()
    if currency_header and currency_header in CURRENCY_SYMBOLS:
        logger.info(f"Currency override: Found '{currency_header}' in X-Currency header.")
        return currency_header
    
    # Try IP-based detection
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    remote_addr = request.META.get('REMOTE_ADDR')
    logger.info(f"Detecting currency from request. X-Forwarded-For: '{forwarded_for}', Remote-Addr: '{remote_addr}'")

    ip_address = None
    if forwarded_for:
        ip_address = forwarded_for.split(',')[0].strip()
        logger.info(f"Using IP from X-Forwarded-For: {ip_address}")
    elif remote_addr:
        ip_address = remote_addr
        logger.info(f"Using IP from Remote-Addr: {ip_address}")
    
    if ip_address:
        country_code = get_country_from_ip(ip_address)
        if country_code:
            currency = get_currency_from_country(country_code)
            logger.info(f"Determined currency '{currency}' from country '{country_code}'.")
            return currency
    
    logger.info(f"Falling back to default currency '{DEFAULT_CURRENCY}'.")
    return DEFAULT_CURRENCY


def get_currency_symbol(currency_code):
    """Get currency symbol for a currency code."""
    return CURRENCY_SYMBOLS.get(currency_code, currency_code)


def get_exchange_rates():
    """
    Get exchange rates from database or settings fallback.
    Returns dict mapping currency_code -> rate_to_inr
    """
    try:
        from .models import CurrencyExchangeRate
        rates = {}
        for rate_obj in CurrencyExchangeRate.objects.filter(is_active=True):
            rates[rate_obj.currency_code] = rate_obj.rate_to_inr
        return rates
    except Exception:
        # Fallback to settings
        return getattr(settings, 'CURRENCY_EXCHANGE_RATES', {
            'USD': Decimal('83.0'),
            'EUR': Decimal('90.0'),
            'GBP': Decimal('105.0'),
            'JPY': Decimal('0.55'),
            'CAD': Decimal('61.0'),
            'AUD': Decimal('55.0'),
        })


def convert_currency(amount, from_currency, to_currency, exchange_rates=None):
    """
    Convert amount from one currency to another.
    exchange_rates should be a dict like {'USD': 83.0, 'EUR': 90.0} (1 USD = 83 INR, 1 EUR = 90 INR)
    If not provided, fetches from database or settings.
    """
    if from_currency == to_currency:
        return amount
    
    if exchange_rates is None:
        exchange_rates = get_exchange_rates()
    
    # Convert to base currency (INR) first
    if from_currency == 'INR':
        base_amount = amount
    elif from_currency in exchange_rates:
        # Rate is: 1 foreign_currency = rate_to_inr INR
        # So: amount_in_foreign * rate = amount_in_inr
        base_amount = amount * exchange_rates[from_currency]
    else:
        # Unknown currency, return original
        return amount
    
    # Convert from base (INR) to target
    if to_currency == 'INR':
        return base_amount
    elif to_currency in exchange_rates:
        # To convert from INR to foreign: amount_in_inr / rate = amount_in_foreign
        return base_amount / exchange_rates[to_currency]
    else:
        # Unknown target currency, return base
        return base_amount

