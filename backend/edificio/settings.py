"""Configuración del servidor del Grupo 2 (Fase 3).

Los valores que cambian entre equipos (clave secreta, modo depuración, hosts,
base de datos y clave del ESP32) se leen del archivo backend/.env con django-environ.
Referencia: https://docs.djangoproject.com/en/5.2/topics/settings/
"""
from pathlib import Path

import environ

# backend/  (donde está manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent
# Raíz del repositorio: de aquí se toman modelo/grafo.json y simulacion/modelo.py
REPO_DIR = BASE_DIR.parent

# ----------------------------------------------------------------- variables del .env
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost"]),
    DB_PATH=(str, "db.sqlite3"),
    API_TOKEN=(str, ""),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
API_TOKEN = env("API_TOKEN")  # clave que debe enviar el ESP32 en la cabecera X-Token

# ----------------------------------------------------------------- aplicaciones
INSTALLED_APPS = [
    # daphne va primero: así "manage.py runserver" arranca un servidor ASGI
    # que entiende HTTP y WebSocket (documentación de Channels, "Installation").
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "rutas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "edificio.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "edificio.wsgi.application"
# Punto de entrada ASGI (HTTP + WebSocket) que usa Daphne.
ASGI_APPLICATION = "edificio.asgi.application"

# ----------------------------------------------------------------- tiempo real
# Capa de canales en memoria: no necesita Redis y funciona en Windows.
# Limitación: solo sirve con UN proceso de servidor (suficiente para la maqueta).
# Referencia: https://channels.readthedocs.io/en/stable/topics/channel_layers.html
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}

# ----------------------------------------------------------------- base de datos
# SQLite: un solo archivo, sin instalar nada más.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / env("DB_PATH"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ----------------------------------------------------------------- idioma y hora
LANGUAGE_CODE = "es-ec"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

# ----------------------------------------------------------------- archivos estáticos
STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
