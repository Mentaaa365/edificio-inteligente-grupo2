"""Panel /admin/ para revisar y editar los datos guardados."""
from django.contrib import admin

from .models import Escenario, Evento, Medicion, RutaCalculada


@admin.register(Escenario)
class EscenarioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "bloqueos", "ocupadas", "alfa_pct", "beta_pct", "estado_envio")
    list_filter = ("estado_envio",)


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ("id", "recibido", "evento", "estado", "bloqueos", "ocupadas", "calculo_us", "origen")
    list_filter = ("estado", "evento", "origen")


class MedicionEnLinea(admin.TabularInline):
    model = Medicion
    extra = 0


@admin.register(RutaCalculada)
class RutaCalculadaAdmin(admin.ModelAdmin):
    list_display = ("id", "creada", "estado", "bloqueos", "ocupadas", "coincide_esp32", "escenario")
    list_filter = ("estado", "coincide_esp32")
    inlines = [MedicionEnLinea]


@admin.register(Medicion)
class MedicionAdmin(admin.ModelAdmin):
    list_display = ("ruta", "zona", "costo_m", "longitud_m", "tiempo_s", "salida")
    list_filter = ("zona", "salida")
