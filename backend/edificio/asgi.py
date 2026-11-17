"""Punto de entrada ASGI: reparte cada conexión según su protocolo.

- HTTP      -> las vistas normales de Django (API y dashboard).
- WebSocket -> el consumidor de rutas/consumers.py (actualización en tiempo real).

Sigue el ejemplo del tutorial oficial de Channels:
https://channels.readthedocs.io/en/stable/tutorial/part_2.html
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edificio.settings")

# Se crea antes de importar el código que usa modelos de Django.
aplicacion_http = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from rutas.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": aplicacion_http,
        # Solo acepta WebSocket abiertos desde un host de ALLOWED_HOSTS.
        "websocket": AllowedHostsOriginValidator(URLRouter(websocket_urlpatterns)),
    }
)
