"""
ASGI entrypoint: the REST API over HTTP, plus the realtime socket at `/ws/` (apps.realtime).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Loads the apps before anything below imports a model.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import OriginValidator  # noqa: E402
from django.conf import settings  # noqa: E402
from django.urls import path  # noqa: E402

from apps.realtime.consumers import RealtimeConsumer  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # The shop's pages open the socket, so their origin is the one to trust, the same list
        # CORS already trusts (ALLOWED_HOSTS only names the API domain).
        "websocket": OriginValidator(
            URLRouter([path("ws/", RealtimeConsumer.as_asgi())]),
            settings.CORS_ALLOWED_ORIGINS,
        ),
    }
)
