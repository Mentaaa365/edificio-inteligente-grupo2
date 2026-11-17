"""Direcciones HTTP de la app rutas."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/eventos/", views.recibir_evento, name="eventos"),
    path("api/comandos/", views.comandos, name="comandos"),
    path("api/escenarios/", views.lista_escenarios, name="escenarios"),
    path("api/escenarios/<int:escenario_id>/ejecutar/", views.ejecutar_escenario, name="ejecutar_escenario"),
    path("api/historico/", views.historico, name="historico"),
    path("api/grafo/", views.grafo, name="grafo"),
    path("api/simular/", views.simular, name="simular"),
]
