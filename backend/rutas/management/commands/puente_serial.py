"""Puente entre el ESP32 conectado por USB y el servidor.

El firmware imprime una línea JSON por evento en el puerto serie (informar() en
evacuacion_esp32.ino). Este comando abre ese puerto, separa las líneas y reenvía
cada JSON a POST /api/eventos/, igual que hará el ESP32 por WiFi en la Fase 4.
Así la maqueta real se ve en el dashboard SIN cambiar el firmware.

Uso (con el servidor ya arrancado en otra terminal y el Monitor serie de Arduino CERRADO):
    python manage.py puente_serial --listar          muestra los puertos COM disponibles
    python manage.py puente_serial --puerto COM5

Referencia de pyserial: https://pyserial.readthedocs.io/en/latest/pyserial_api.html
"""
import json
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from rutas.cliente_http import ErrorEnvio, enviar_evento

BAUDIOS = 115200            # los mismos de Serial.begin() en el firmware
MAX_LINEA = 8192            # una línea del firmware ocupa unos 600 bytes; más es ruido


def separar_lineas(pendiente: bytes, nuevos: bytes) -> tuple[list[bytes], bytes]:
    """Junta lo que quedaba con lo recién leído y devuelve (líneas completas, resto sin '\\n').

    El puerto entrega bytes en trozos de cualquier tamaño: una línea puede llegar
    partida en dos lecturas, por eso se guarda el resto hasta que llegue su '\\n'.
    """
    datos = pendiente + nuevos
    *lineas, resto = datos.split(b"\n")
    if len(resto) > MAX_LINEA:  # nunca llegó el fin de línea: se descarta para no crecer sin límite
        resto = b""
    return lineas, resto


def extraer_json(linea: bytes) -> dict | None:
    """Devuelve el evento si la línea es un JSON del firmware; si no (arranque, saludo, ruido), None."""
    texto = linea.decode("utf-8", errors="replace").strip()
    if not (texto.startswith("{") and texto.endswith("}")):
        return None
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError:
        return None
    return datos if isinstance(datos, dict) and "evento" in datos else None


def abrir_puerto(puerto: str, baudios: int):
    """Abre el puerto sin reiniciar el ESP32.

    En las placas ESP32 DevKit, las líneas DTR y RTS del USB están conectadas a EN y BOOT:
    si se activan al abrir, la placa se reinicia. Se dejan apagadas para no perder el estado.
    """
    import serial   # se importa aquí para que el resto del servidor funcione aunque falte pyserial

    conexion = serial.Serial()
    conexion.port = puerto
    conexion.baudrate = baudios
    conexion.timeout = 0.2
    conexion.dtr = False
    conexion.rts = False
    conexion.open()
    return conexion


class Command(BaseCommand):
    help = "Lee el JSON del ESP32 por el puerto USB y lo reenvía a POST /api/eventos/."

    def add_arguments(self, parser):
        parser.add_argument("--puerto", help="puerto del ESP32, por ejemplo COM5")
        parser.add_argument("--listar", action="store_true", help="muestra los puertos disponibles y termina")
        parser.add_argument("--baudios", type=int, default=BAUDIOS)
        parser.add_argument("--url", default="http://127.0.0.1:8000", help="dirección del servidor")
        parser.add_argument("--token", default=settings.API_TOKEN, help="valor de X-Token (por defecto el del .env)")

    def handle(self, *args, **op):
        try:
            import serial  # noqa: F401
        except ImportError:
            raise CommandError("Falta pyserial: .\\.venv\\Scripts\\python.exe -m pip install -r backend\\requirements.txt")

        if op["listar"]:
            self.listar_puertos()
            return
        if not op["puerto"]:
            raise CommandError("Indica el puerto con --puerto COMx (usa --listar para verlos).")

        self.url, self.token = op["url"], op["token"]
        self.enviados = self.perdidos = 0
        self.stdout.write(f"Puente {op['puerto']} ({op['baudios']} baudios) -> {self.url}/api/eventos/  (Ctrl+C para parar)")
        try:
            self.bucle(op["puerto"], op["baudios"])
        except KeyboardInterrupt:
            self.stdout.write("\nDetenido.")
        self.stdout.write(self.style.SUCCESS(f"{self.enviados} eventos reenviados, {self.perdidos} no llegaron al servidor."))

    def listar_puertos(self):
        from serial.tools import list_ports

        puertos = list(list_ports.comports())
        if not puertos:
            self.stdout.write("No hay puertos serie. ¿Está conectado el ESP32 con un cable USB de datos?")
        for p in puertos:
            self.stdout.write(f"{p.device:<8} {p.description}")

    def bucle(self, puerto, baudios):
        """Lee para siempre. Si se desconecta el cable, espera y vuelve a intentarlo."""
        import serial

        while True:
            try:
                conexion = abrir_puerto(puerto, baudios)
            except serial.SerialException as e:
                self.stdout.write(self.style.WARNING(
                    f"No se pudo abrir {puerto}: {e}\n"
                    f"  ¿Está conectado el ESP32, es el puerto correcto (--listar) y está cerrado el Monitor serie "
                    f"de Arduino? Reintento en 2 s."))
                time.sleep(2)
                continue
            self.stdout.write(self.style.SUCCESS(f"Conectado a {puerto}. Esperando eventos de la maqueta..."))
            pendiente = b""
            try:
                with conexion:
                    while True:
                        # Lee lo que haya llegado (al menos 1 byte, o nada tras 0,2 s).
                        nuevos = conexion.read(conexion.in_waiting or 1)
                        lineas, pendiente = separar_lineas(pendiente, nuevos)
                        for linea in lineas:
                            self.procesar(linea)
            except serial.SerialException as e:
                self.stdout.write(self.style.WARNING(f"Se perdió la conexión con {puerto} ({e}). Reintento en 2 s."))
                time.sleep(2)

    def procesar(self, linea: bytes):
        """Reenvía la línea si es un evento; si no, la muestra como texto del ESP32."""
        evento = extraer_json(linea)
        if evento is None:
            texto = linea.decode("utf-8", errors="replace").strip()
            if texto:
                self.stdout.write(f"  [ESP32] {texto}")
            return
        try:
            respuesta = enviar_evento(self.url, evento, self.token, origen="esp32")
        except ErrorEnvio as e:
            self.perdidos += 1
            self.stdout.write(self.style.ERROR(f"  {evento.get('evento')}: {e}"))
            return
        self.enviados += 1
        marca = self.style.SUCCESS("coincide") if respuesta["coincide"] else self.style.ERROR(
            "NO coincide: " + "; ".join(respuesta["diferencias"]))
        self.stdout.write(f"{evento.get('evento', '?'):<5} {evento.get('estado', '?'):<12} "
                          f"bloqueos={','.join(evento.get('bloqueos', [])) or '-':<12} -> #{respuesta['id']} {marca}")
