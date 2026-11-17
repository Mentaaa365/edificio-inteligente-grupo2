"""Pruebas del cálculo de rutas: el servidor debe reproducir la tabla de escenarios de la Fase 1
(docs/Fase_1.md, sección 3) y el formato exacto del firmware."""
import copy
from itertools import combinations

from django.test import SimpleTestCase

from rutas import motor

# nombre: (bloqueos, ocupadas, estado, zonas aisladas, recorrido medio, recorrido máximo)
TABLA_FASE_1 = {
    "S0": ([], [], "RUTA_ACTIVA", 0, 14.88, 23),
    "S1": (["e6"], [], "RUTA_ACTIVA", 0, 15.38, 23),
    "S2": (["e7"], [], "RUTA_ACTIVA", 0, 18.38, 34),
    "S3": (["e2", "e4"], [], "RUTA_ACTIVA", 0, 14.88, 23),
    "S4": (["e1"], [], "RUTA_ACTIVA", 0, 19.88, 31),
    "S5": (["e2", "e3", "e6"], [], "RUTA_PARCIAL", 1, 14.29, 23),
    "S6": (["e1", "e5", "e7"], [], "SIN_RUTA", 8, None, None),
    "S7": ([], ["Z7"], "RUTA_ACTIVA", 0, 15.38, 23),
}


class EscenariosFase1(SimpleTestCase):
    def test_tabla_de_escenarios(self):
        for nombre, (bloq, ocup, estado, aisladas, medio, maximo) in TABLA_FASE_1.items():
            with self.subTest(escenario=nombre):
                r = motor.calcular(bloq, ocup)
                self.assertEqual(r["estado"], estado)
                self.assertEqual(r["aisladas"], aisladas)
                longitudes = [d["longitud_m"] for d in r["detalle"].values() if d["longitud_m"] is not None]
                if medio is None:
                    self.assertEqual(longitudes, [])
                else:
                    self.assertAlmostEqual(sum(longitudes) / len(longitudes), medio, delta=0.0051)  # la tabla redondea a 2 decimales
                    self.assertEqual(max(longitudes), maximo)

    def test_laboratorio_cambia_de_salida_con_e6_bloqueado(self):
        self.assertEqual(motor.calcular()["rutas"]["Z3"], {"costo_m": 19.0, "ruta": "Z3>C2>C5>S2"})
        # Valor medido en Wokwi: Laboratorio a S1 con 30,50 m (Fase 1, sección 5).
        self.assertEqual(motor.calcular(["e6"])["rutas"]["Z3"], {"costo_m": 30.5, "ruta": "Z3>C2>C1>S1"})

    def test_pir_del_auditorio_cambia_la_ruta_del_laboratorio(self):
        r = motor.calcular([], ["Z7"])
        self.assertEqual(r["detalle"]["Z3"]["salida"], "S1")
        self.assertEqual(r["detalle"]["Z3"]["longitud_m"], 23)

    def test_zona_aislada_sale_como_null_y_su_puerta_en_ambar(self):
        r = motor.calcular(["e2", "e3", "e6"])
        self.assertIsNone(r["rutas"]["Z3"])
        self.assertEqual(r["zonas_aisladas"], ["Z3"])
        self.assertEqual(r["aristas_aisladas"], ["p3"])

    def test_alfa_cero_anula_el_efecto_del_pir(self):
        # Con α < 0,25 el sensor no cambia la ruta (Fase 1, sensibilidad a α).
        self.assertEqual(motor.calcular([], ["Z7"], alfa_pct=0)["detalle"]["Z3"]["salida"], "S2")

    def test_orden_de_bloqueos_igual_que_el_firmware(self):
        self.assertEqual(motor.calcular(["e7", "e2"])["bloqueos"], ["e2", "e7"])

    def test_rechaza_pasillos_y_zonas_desconocidos(self):
        with self.assertRaises(ValueError):
            motor.calcular(["e99"])
        with self.assertRaises(ValueError):
            motor.calcular([], ["Z9"])
        with self.assertRaises(ValueError):   # una puerta no tiene pulsador de bloqueo
            motor.calcular(["p1"])


class FormatoEsp32(SimpleTestCase):
    def test_costo_truncado_como_imprimirMetros(self):
        self.assertEqual(motor.costo_esp32(305_000), 30.5)
        self.assertEqual(motor.costo_esp32(472_500), 47.25)
        self.assertEqual(motor.costo_esp32(123_456_7), 123.45)   # trunca, no redondea a 123,46
        self.assertIsNone(motor.costo_esp32(motor.INF))

    def test_dos_decimales_bastan_con_los_parametros_del_firmware(self):
        """Con α = 0,5, β = 1 y riesgo 50 % todo costo es múltiplo de 0,25 m:
        el truncado a 2 decimales no pierde información en las 256 × 4 combinaciones."""
        ed = motor.edificio()
        for k in range(len(ed.pasillos) + 1):
            for bloq in combinations(ed.pasillos, k):
                for ocup in ([], ["Z7"], ["Z1"], ["Z1", "Z7"]):
                    for d in motor.calcular(bloq, ocup)["detalle"].values():
                        if d["costo_m"] is not None:
                            self.assertAlmostEqual((d["costo_m"] * 4) % 1, 0)


class Comparacion(SimpleTestCase):
    def esp32(self, bloqueos=(), ocupadas=(), estado=None):
        """Construye la línea JSON que enviaría un ESP32 correcto."""
        r = motor.calcular(bloqueos, ocupadas)
        # deepcopy: si se compartiera el diccionario, cambiar el del ESP32 cambiaría también el del servidor.
        return {"estado": estado or r["estado"], "explorados": r["explorados"],
                "aisladas": r["aisladas"], "rutas": copy.deepcopy(r["rutas"])}, r

    def test_coinciden(self):
        datos, r = self.esp32(["e6"])
        self.assertEqual(motor.comparar(datos, r), [])

    def test_estado_normal_no_cuenta_como_diferencia(self):
        datos, r = self.esp32(["e2", "e3", "e6"], estado="NORMAL")   # el modelo dice RUTA_PARCIAL
        self.assertEqual(motor.comparar(datos, r), [])

    def test_estado_distinto_en_emergencia(self):
        datos, r = self.esp32(["e2", "e3", "e6"], estado="RUTA_ACTIVA")
        self.assertIn("estado", motor.comparar(datos, r)[0])

    def test_detecta_costo_ruta_y_aislada(self):
        datos, r = self.esp32()
        datos["rutas"]["Z1"] = {"costo_m": 12.0, "ruta": "Z1>C1>S1"}
        datos["rutas"]["Z2"] = {"costo_m": 11.0, "ruta": "Z2>C1>C2>S1"}
        datos["rutas"]["Z3"] = None
        diferencias = " | ".join(motor.comparar(datos, r))
        self.assertIn("Z1: costo", diferencias)
        self.assertIn("Z2: ruta", diferencias)
        self.assertIn("Z3: ESP32 aislada", diferencias)

    def test_detecta_zona_que_falta(self):
        datos, r = self.esp32()
        del datos["rutas"]["Z8"]
        self.assertEqual(motor.comparar(datos, r), ["Z8: el ESP32 no la envió"])
