"""Pruebas del puente USB -> servidor sin placa: se sustituye el puerto serie por uno falso
que entrega los mismos bytes que imprime el firmware, partidos en trozos como en la realidad."""
import io
from unittest import mock

from django.core.management import call_command
from django.test import LiveServerTestCase, SimpleTestCase

from rutas import motor
from rutas.cliente_http import ErrorEnvio
from rutas.management.commands import puente_serial
from rutas.models import Evento


def linea_firmware(bloqueos=(), ocupadas=(), evento="B0", estado=None, ms=5000) -> bytes:
    """Escribe la línea exactamente como informar() del firmware: costos con dos decimales
    (11.00, no 11.0), sin espacios y terminada en \\r\\n por Serial.println()."""
    r = motor.calcular(bloqueos, ocupadas)
    estado = estado or r["estado"]
    lista = lambda xs: ",".join(f'"{x}"' for x in xs)  # noqa: E731
    rutas = ",".join(
        f'"{z}":null' if v is None else f'"{z}":{{"costo_m":{v["costo_m"]:.2f},"ruta":"{v["ruta"]}"}}'
        for z, v in r["rutas"].items()
    )
    texto = (f'{{"ms":{ms},"evento":"{evento}","estado":"{estado}","bloqueos":[{lista(r["bloqueos"])}],'
             f'"ocupadas":[{lista(r["ocupadas"])}],"calculo_us":702,"explorados":{r["explorados"]},'
             f'"aisladas":{r["aisladas"]},"rutas":{{{rutas}}}}}')
    return texto.encode() + b"\r\n"


class SepararLineas(SimpleTestCase):
    def test_linea_partida_en_dos_lecturas(self):
        linea = linea_firmware()
        lineas, resto = puente_serial.separar_lineas(b"", linea[:100])
        self.assertEqual(lineas, [])
        lineas, resto = puente_serial.separar_lineas(resto, linea[100:])
        self.assertEqual(lineas, [linea[:-1]])     # sin el \n
        self.assertEqual(resto, b"")

    def test_varias_lineas_en_una_lectura(self):
        lineas, resto = puente_serial.separar_lineas(b"", b"uno\r\ndos\r\ntr")
        self.assertEqual(lineas, [b"uno\r", b"dos\r"])
        self.assertEqual(resto, b"tr")

    def test_ruido_sin_fin_de_linea_se_descarta(self):
        _, resto = puente_serial.separar_lineas(b"", b"x" * (puente_serial.MAX_LINEA + 1))
        self.assertEqual(resto, b"")


class ExtraerJson(SimpleTestCase):
    def test_linea_del_firmware(self):
        datos = puente_serial.extraer_json(linea_firmware(["e6"], evento="B4"))
        self.assertEqual(datos["evento"], "B4")
        self.assertEqual(datos["rutas"]["Z3"], {"costo_m": 30.5, "ruta": "Z3>C2>C1>S1"})

    def test_ignora_lo_que_no_es_un_evento(self):
        for texto in (b"Grupo 2 - Edificio inteligente. Esperando a que los PIR se estabilicen...\r\n",
                      b"ets Jun  8 2016 00:22:57\r\n",       # mensaje de arranque del ESP32
                      b"\xff\xfe\x00basura\r\n",
                      b'{"ms":1,"evento":"B0"\r\n',          # JSON cortado
                      b'{"hola":1}\r\n',                     # JSON que no es del firmware
                      b"\r\n"):
            self.assertIsNone(puente_serial.extraer_json(texto), texto)


class PuertoFalso:
    """Imita serial.Serial: entrega los bytes en trozos de 64 y luego simula Ctrl+C."""

    def __init__(self, datos: bytes):
        self.trozos = [datos[i:i + 64] for i in range(0, len(datos), 64)]

    @property
    def in_waiting(self):
        return len(self.trozos[0]) if self.trozos else 0

    def read(self, _n):
        if not self.trozos:
            raise KeyboardInterrupt
        return self.trozos.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class PuenteCompleto(LiveServerTestCase):
    """Puerto falso -> comando puente_serial -> HTTP real -> servidor de pruebas -> base de datos."""

    def test_reenvia_los_eventos_de_la_maqueta(self):
        salida_serie = (
            b"ets Jun  8 2016 00:22:57\r\nrst:0x1 (POWERON_RESET)\r\n"
            b"Grupo 2 - Edificio inteligente. Esperando a que los PIR se estabilicen...\r\n"
            + linea_firmware(evento="LISTO", estado="NORMAL", ms=3001)
            + linea_firmware(evento="B0", ms=8000)
            + linea_firmware(["e6"], evento="B4", ms=9500)
            + linea_firmware(["e2", "e3", "e6"], evento="B2", ms=12000)
        )
        salida = io.StringIO()
        # 127.0.0.1 y no "localhost": en Windows "localhost" prueba antes IPv6 y cada envío tarda ~2 s más.
        url = self.live_server_url.replace("localhost", "127.0.0.1")
        with mock.patch.object(puente_serial, "abrir_puerto", return_value=PuertoFalso(salida_serie)):
            call_command("puente_serial", puerto="COM9", url=url, token="", stdout=salida)

        texto = salida.getvalue()
        self.assertIn("[ESP32] Grupo 2 - Edificio inteligente", texto)
        self.assertIn("4 eventos reenviados, 0 no llegaron", texto)
        self.assertNotIn("NO coincide", texto)
        eventos = list(Evento.objects.order_by("id"))
        self.assertEqual([e.evento for e in eventos], ["LISTO", "B0", "B4", "B2"])
        self.assertTrue(all(e.origen == "esp32" and e.ruta.coincide_esp32 for e in eventos))
        self.assertEqual(eventos[-1].ruta.estado, "RUTA_PARCIAL")



class Argumentos(SimpleTestCase):
    def test_servidor_apagado_no_detiene_el_puente(self):
        salida = io.StringIO()
        datos = linea_firmware(evento="B0") + linea_firmware(["e1"], evento="B5")
        caido = ErrorEnvio("no se pudo conectar con el servidor")
        with mock.patch.object(puente_serial, "abrir_puerto", return_value=PuertoFalso(datos)),                 mock.patch.object(puente_serial, "enviar_evento", side_effect=caido) as enviar:
            call_command("puente_serial", puerto="COM9", token="", stdout=salida)
        self.assertEqual(enviar.call_count, 2)     # siguió leyendo tras el primer fallo
        self.assertIn("0 eventos reenviados, 2 no llegaron", salida.getvalue())

    def test_pide_el_puerto(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command("puente_serial", stdout=io.StringIO())

    def test_listar_puertos(self):
        salida = io.StringIO()
        call_command("puente_serial", listar=True, stdout=salida)
        self.assertTrue(salida.getvalue())   # lista los puertos o explica que no hay ninguno
