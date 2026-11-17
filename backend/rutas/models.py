"""Tablas de la base de datos (SQLite) para guardar el histórico.

    Escenario      condición preparada (bloqueos, zonas ocupadas, α, β) que se puede ejecutar
    Evento         una línea JSON enviada por el ESP32, tal como llegó
    RutaCalculada  lo que calculó el servidor con modelo.py y si coincide con el ESP32
    Medicion       una fila por zona de cada cálculo: costo, metros, tiempo y salida

Referencia: https://docs.djangoproject.com/en/5.2/topics/db/models/
"""
from django.db import models


class Escenario(models.Model):
    class EstadoEnvio(models.TextChoices):
        INACTIVO = "inactivo", "Inactivo"
        PENDIENTE = "pendiente", "Pendiente de enviar al ESP32"
        ENVIADO = "enviado", "Enviado al ESP32"

    nombre = models.CharField(max_length=40, unique=True)
    descripcion = models.CharField(max_length=200, blank=True)
    bloqueos = models.JSONField(default=list, blank=True)   # ej. ["e2", "e4"]
    ocupadas = models.JSONField(default=list, blank=True)   # ej. ["Z7"]
    alarma = models.BooleanField(default=True)              # el ESP32 debe activar la alarma
    alfa_pct = models.PositiveIntegerField(default=50)
    beta_pct = models.PositiveIntegerField(default=100)
    estado_envio = models.CharField(max_length=10, choices=EstadoEnvio.choices, default=EstadoEnvio.INACTIVO)
    enviado_en = models.DateTimeField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre}: {self.descripcion}"


class Evento(models.Model):
    """Lo que imprime el firmware en informar(): se guarda campo a campo y también entero."""
    recibido = models.DateTimeField(auto_now_add=True, db_index=True)
    ms = models.BigIntegerField(help_text="millis() del ESP32 al emitir el evento")
    evento = models.CharField(max_length=16, db_index=True, help_text="LISTO, B0, B7, B1–B9, PIR1, PIR2")
    estado = models.CharField(max_length=16, db_index=True)
    bloqueos = models.JSONField(default=list)
    ocupadas = models.JSONField(default=list)
    calculo_us = models.PositiveIntegerField()
    explorados = models.PositiveIntegerField()
    aisladas = models.PositiveIntegerField()
    rutas = models.JSONField()
    json_original = models.JSONField()
    origen = models.CharField(max_length=16, default="esp32", help_text="esp32 o simulador")

    class Meta:
        ordering = ["-recibido", "-id"]

    def __str__(self):
        return f"#{self.pk} {self.evento} {self.estado}"


class RutaCalculada(models.Model):
    """Resultado de modelo.calcular_campo() en el servidor, para un evento o para un escenario."""
    creada = models.DateTimeField(auto_now_add=True, db_index=True)
    evento = models.OneToOneField(Evento, null=True, blank=True, on_delete=models.CASCADE, related_name="ruta")
    escenario = models.ForeignKey(Escenario, null=True, blank=True, on_delete=models.SET_NULL, related_name="rutas")
    bloqueos = models.JSONField(default=list)
    ocupadas = models.JSONField(default=list)
    alfa_pct = models.PositiveIntegerField()
    beta_pct = models.PositiveIntegerField()
    estado = models.CharField(max_length=16)                 # estado según el modelo (sin tener en cuenta la alarma)
    explorados = models.PositiveIntegerField()
    aisladas = models.PositiveIntegerField()
    resultado = models.JSONField()                           # salida completa de motor.calcular()
    calculo_us = models.PositiveIntegerField(help_text="tiempo de cálculo en el servidor")
    # None cuando no hay ESP32 con quien comparar (ejecución de un escenario).
    coincide_esp32 = models.BooleanField(null=True)
    diferencias = models.JSONField(default=list)

    class Meta:
        ordering = ["-creada", "-id"]

    def __str__(self):
        return f"Ruta #{self.pk} {self.estado}"


class Medicion(models.Model):
    """Una fila por zona: permite graficar y filtrar el histórico sin abrir el JSON."""
    ruta = models.ForeignKey(RutaCalculada, on_delete=models.CASCADE, related_name="mediciones")
    zona = models.CharField(max_length=4, db_index=True)
    costo_m = models.FloatField(null=True)         # costo con penalizaciones (null = aislada)
    longitud_m = models.FloatField(null=True)      # metros reales a recorrer
    tiempo_s = models.FloatField(null=True)        # longitud / velocidad de marcha
    salida = models.CharField(max_length=4, null=True)

    class Meta:
        ordering = ["ruta_id", "zona"]

    def __str__(self):
        return f"{self.zona}: {self.longitud_m} m -> {self.salida}"
