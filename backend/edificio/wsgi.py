"""Punto de entrada WSGI (solo HTTP). Se deja por compatibilidad; el proyecto usa asgi.py."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edificio.settings")

application = get_wsgi_application()
