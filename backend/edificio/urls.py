"""Direcciones del proyecto: el panel de administración y todo lo de la app rutas."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("rutas.urls")),
]
