from rest_framework.throttling import ScopedRateThrottle


class GuestScopedRateThrottle(ScopedRateThrottle):
    """A ScopedRateThrottle that only counts anonymous requests, so guest-facing endpoints are
    rate-limited per IP without slowing down signed-in Customers."""

    def allow_request(self, request, view):
        if request.user and request.user.is_authenticated:
            return True
        return super().allow_request(request, view)
