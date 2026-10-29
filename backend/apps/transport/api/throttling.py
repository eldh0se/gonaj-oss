"""Per-IP throttling with hashed, expiring counter keys (FR-021–FR-024).

The minute and day budgets are shared across all five reads. The
client identity is the direct connection address unless the
deployment configures a known proxy (``TRANSPORT_TRUSTED_PROXY``),
in which case the leftmost forwarded-for address is used. Counter
keys carry only a SHA-256 hash of the IP — raw IPs never reach the
cache backend (FR-023).
"""
import hashlib

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


def throttle_identity(request):
    """Return the client IP identifying this request for throttling."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded and getattr(settings, "TRANSPORT_TRUSTED_PROXY", ""):
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def hashed_identity(ident):
    return hashlib.sha256(ident.encode("utf-8")).hexdigest()


class _HashedThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        ident = hashed_identity(throttle_identity(request))
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }

    def get_rate(self):
        # Read rates lazily so settings overrides (deployments and
        # tests) take effect; DRF otherwise binds them at import.
        from rest_framework.settings import api_settings

        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]


class TransportMinuteThrottle(_HashedThrottle):
    scope = "transport_minute"


class TransportDayThrottle(_HashedThrottle):
    scope = "transport_day"


READ_THROTTLE_CLASSES = [TransportMinuteThrottle, TransportDayThrottle]
