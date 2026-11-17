"""Simula un ESP32 que envía eventos al servidor por HTTP, para probar sin hardware.

Uso (con el servidor ya arrancado en otra terminal):
    python manage.py simular_esp32
    python manage.py simular_esp32 --eventos 60 --intervalo 0.5 --discrepancia 0.1

Imita el loop() del firmware: guarda el estado (alarma, bloqueos, zonas ocupadas),
pulsa "botones" al azar, recalcula con modelo.py y envía la MISMA línea JSON que
imprime informar() en evacuacion_esp32.ino.
Referencia: https://docs.djangoproject.com/en/5.2/howto/custom-management-commands/
"""
import copy
import random
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from rutas import motor
from rutas.cliente_http import ErrorEnvio, enviar_evento


class EspSimulado:
    """Estado interno del ESP32 simulado."""

    def __init__(self, aleatorio: random.Random):
        ed = motor.edificio()
        self.azar = aleatorio
        self.emergencia = False
        self.bloqueada: set[str] = set()
        self.ocupada: set[str] = set()
        self.ms = 3000                                     # el firmware emite LISTO tras 3 s
        # Pulsador de cada pasillo (B5 -> e1, B1 -> e2 ...) y zona de cada PIR, desde grafo.json.
        self.pulsador = {a["id"]: a["pulsador"] for a in ed.aristas if a["tipo"] == "pasillo"}
        self.pir = {s["id"]: s["zona"] for s in ed.datos["sensores"]}

    def siguiente_accion(self, numero: int) -> str:
        """Elige qué "botón" se pulsa y actualiza el estado como lo haría el firmware."""
        if numero == 0:
            return "LISTO"
        if not self.emergencia:                            # sin alarma, lo primero es pulsar B0
            self.emergencia = True
            return "B0"
        tirada = self.azar.random()
        if tirada < 0.10:                                  # reinicio: quita alarma y bloqueos
            self.emergencia = False
            self.bloqueada.clear()
            return "B7"
        if tirada < 0.30:                                  # un PIR detecta o deja de detectar
            sensor = self.azar.choice(sorted(self.pir))
            self.ocupada ^= {self.pir[sensor]}             # ^= alterna: añade o quita
            return sensor
        pasillo = self.azar.choice(sorted(self.pulsador))  # pulsador de bloqueo (alterna)
        self.bloqueada ^= {pasillo}
        return self.pulsador[pasillo]

    def linea_json(self, evento: str) -> dict:
        r = motor.calcular(self.bloqueada, self.ocupada)
        self.ms += self.azar.randint(800, 4000)
        return {
            "ms": self.ms,
            "evento": evento,
            "estado": r["estado"] if self.emergencia else "NORMAL",
            "bloqueos": r["bloqueos"],
            "ocupadas": r["ocupadas"],
            "calculo_us": self.azar.randint(640, 760),     # en Wokwi el cálculo tarda unos 700 µs
            "explorados": r["explorados"],
            "aisladas": r["aisladas"],
            "rutas": r["rutas"],
        }


def falsear(linea: dict, azar: random.Random) -> dict:
    """Introduce un error en una ruta para comprobar que el dashboard lo detecta."""
    linea = copy.deepcopy(linea)
    con_ruta = [z for z, r in linea["rutas"].items() if r]
    if con_ruta:
        zona = azar.choice(con_ruta)
        linea["rutas"][zona]["costo_m"] = round(linea["rutas"][zona]["costo_m"] + 1, 2)
    return linea


class Command(BaseCommand):
    help = "Simula un ESP32 que envía eventos JSON a POST /api/eventos/."

    def add_arguments(self, parser):
        parser.add_argument("--url", default="http://127.0.0.1:8000", help="dirección del servidor")
        parser.add_argument("--eventos", type=int, default=30, help="cuántos eventos enviar (0 = sin fin)")
        parser.add_argument("--intervalo", type=float, default=1.0, help="segundos entre eventos")
        parser.add_argument("--discrepancia", type=float, default=0.0,
                            help="probabilidad (0 a 1) de enviar una ruta alterada a propósito")
        parser.add_argument("--semilla", type=int, default=None, help="semilla para repetir la misma secuencia")
        parser.add_argument("--token", default=settings.API_TOKEN, help="valor de X-Token (por defecto el del .env)")

    def handle(self, *args, **op):
        azar = random.Random(op["semilla"])
        esp = EspSimulado(azar)
        self.stdout.write(f"Enviando a {op['url']}/api/eventos/ (Ctrl+C para parar)")
        n = 0
        try:
            while op["eventos"] == 0 or n < op["eventos"]:
                linea = esp.linea_json(esp.siguiente_accion(n))
                if azar.random() < op["discrepancia"]:
                    linea = falsear(linea, azar)
                self._enviar(op["url"], op["token"], linea, n + 1)
                n += 1
                time.sleep(op["intervalo"])
        except KeyboardInterrupt:
            self.stdout.write("\nDetenido.")
        self.stdout.write(self.style.SUCCESS(f"{n} eventos enviados."))

    def _enviar(self, url, token, linea, numero):
        try:
            respuesta = enviar_evento(url, linea, token, origen="simulador")
        except ErrorEnvio as e:
            raise CommandError(str(e))
        marca = self.style.SUCCESS("coincide") if respuesta["coincide"] else self.style.ERROR("NO coincide")
        self.stdout.write(
            f"{numero:>3}  {linea['evento']:<5} {linea['estado']:<12} bloqueos={','.join(linea['bloqueos']) or '-':<12}"
            f" ocupadas={','.join(linea['ocupadas']) or '-':<6} -> #{respuesta['id']} {marca}"
        )
