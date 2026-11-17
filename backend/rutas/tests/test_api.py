"""Pruebas de la API HTTP con el cliente de pruebas de Django.
Referencia: https://docs.djangoproject.com/en/5.2/topics/testing/tools/"""
import json

from django.test import Client, TestCase, override_settings

from rutas import motor
from rutas.models import Escenario, Evento, Medicion, RutaCalculada


def linea_esp32(bloqueos=(), ocupadas=(), evento="B0", estado=None, ms=10_000):
    """La línea JSON que imprimiría un ESP32 que calcula bien."""
    r = motor.calcular(bloqueos, ocupadas)
    return {
        "ms": ms, "evento": evento, "estado": estado or r["estado"],
        "bloqueos": r["bloqueos"], "ocupadas": r["ocupadas"], "calculo_us": 700,
        "explorados": r["explorados"], "aisladas": r["aisladas"], "rutas": r["rutas"],
    }


class ApiEventos(TestCase):
    def enviar(self, datos, **cabeceras):
        return self.client.post("/api/eventos/", json.dumps(datos), content_type="application/json", **cabeceras)

    def test_linea_real_del_monitor_serie(self):
        # Copiada tal cual del formato de informar() en evacuacion_esp32.ino (escenario S0 tras LISTO).
        texto = ('{"ms":3001,"evento":"LISTO","estado":"NORMAL","bloqueos":[],"ocupadas":[],"calculo_us":702,'
                 '"explorados":16,"aisladas":0,"rutas":{"Z1":{"costo_m":11.00,"ruta":"Z1>C1>S1"},'
                 '"Z2":{"costo_m":11.00,"ruta":"Z2>C1>S1"},"Z3":{"costo_m":19.00,"ruta":"Z3>C2>C5>S2"},'
                 '"Z4":{"costo_m":23.00,"ruta":"Z4>C3>C4>S3"},"Z5":{"costo_m":23.00,"ruta":"Z5>C3>C4>S3"},'
                 '"Z6":{"costo_m":11.00,"ruta":"Z6>C4>S3"},"Z7":{"costo_m":10.00,"ruta":"Z7>C5>S2"},'
                 '"Z8":{"costo_m":11.00,"ruta":"Z8>C4>S3"}}}')
        r = self.client.post("/api/eventos/", texto, content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(r.json()["coincide"], r.json()["diferencias"])

    def test_guarda_evento_ruta_y_mediciones(self):
        r = self.enviar(linea_esp32(["e6"]))
        self.assertEqual(r.status_code, 201)
        cuerpo = r.json()
        self.assertTrue(cuerpo["coincide"])
        self.assertEqual(cuerpo["diferencias"], [])
        evento = Evento.objects.get(pk=cuerpo["id"])
        self.assertEqual(evento.bloqueos, ["e6"])
        self.assertEqual(evento.ruta.estado, "RUTA_ACTIVA")
        self.assertEqual(Medicion.objects.filter(ruta=evento.ruta).count(), 8)
        self.assertEqual(Medicion.objects.get(ruta=evento.ruta, zona="Z3").salida, "S1")

    def test_registra_discrepancia(self):
        datos = linea_esp32()
        datos["rutas"]["Z7"]["ruta"] = "Z7>C5>C2>C1>S1"
        cuerpo = self.enviar(datos).json()
        self.assertFalse(cuerpo["coincide"])
        self.assertFalse(RutaCalculada.objects.get(evento_id=cuerpo["id"]).coincide_esp32)

    def test_json_invalido(self):
        r = self.client.post("/api/eventos/", "{no es json", content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Evento.objects.count(), 0)

    def test_campos_que_faltan_o_con_tipo_incorrecto(self):
        datos = linea_esp32()
        del datos["rutas"]
        datos["ms"] = "diez"
        r = self.enviar(datos)
        self.assertEqual(r.status_code, 400)
        detalles = " ".join(r.json()["detalles"])
        self.assertIn("rutas", detalles)
        self.assertIn("ms", detalles)

    def test_pasillo_o_estado_desconocido(self):
        datos = linea_esp32()
        datos["bloqueos"] = ["e42"]
        self.assertEqual(self.enviar(datos).status_code, 400)
        datos = linea_esp32(estado="EN_LLAMAS")
        self.assertEqual(self.enviar(datos).status_code, 400)

    def test_solo_acepta_post(self):
        self.assertEqual(self.client.get("/api/eventos/").status_code, 405)

    @override_settings(API_TOKEN="clave-del-esp32")
    def test_token(self):
        self.assertEqual(self.enviar(linea_esp32()).status_code, 401)
        self.assertEqual(self.enviar(linea_esp32(), HTTP_X_TOKEN="otra").status_code, 401)
        self.assertEqual(self.enviar(linea_esp32(), HTTP_X_TOKEN="clave-del-esp32").status_code, 201)

    def test_csrf_no_bloquea_al_esp32(self):
        cliente = Client(enforce_csrf_checks=True)
        r = cliente.post("/api/eventos/", json.dumps(linea_esp32()), content_type="application/json")
        self.assertEqual(r.status_code, 201)


class ApiEscenariosYComandos(TestCase):
    def test_escenarios_de_la_fase_1_creados_por_la_migracion(self):
        nombres = [e["nombre"] for e in self.client.get("/api/escenarios/").json()["escenarios"]]
        self.assertEqual(nombres, [f"S{i}" for i in range(8)])

    def test_ejecutar_y_recoger_comando(self):
        s5 = Escenario.objects.get(nombre="S5")
        r = self.client.post(f"/api/escenarios/{s5.id}/ejecutar/")
        self.assertEqual(r.status_code, 200)
        cuerpo = r.json()
        self.assertEqual(cuerpo["escenario"]["estado_envio"], "pendiente")
        self.assertEqual(cuerpo["ruta"]["estado"], "RUTA_PARCIAL")
        self.assertIsNone(cuerpo["ruta"]["coincide_esp32"])
        self.assertEqual(RutaCalculada.objects.filter(escenario=s5).count(), 1)

        # El ESP32 pregunta: recibe S5 una sola vez.
        comandos = self.client.get("/api/comandos/").json()["comandos"]
        self.assertEqual([c["nombre"] for c in comandos], ["S5"])
        self.assertEqual(comandos[0]["bloqueos"], ["e2", "e3", "e6"])
        self.assertEqual(self.client.get("/api/comandos/").json()["comandos"], [])
        s5.refresh_from_db()
        self.assertEqual(s5.estado_envio, "enviado")
        self.assertIsNotNone(s5.enviado_en)

    def test_ejecutar_usa_alfa_y_beta_del_escenario(self):
        esc = Escenario.objects.create(nombre="PIR sin efecto", ocupadas=["Z7"], alfa_pct=0)
        ruta = self.client.post(f"/api/escenarios/{esc.id}/ejecutar/").json()["ruta"]
        self.assertEqual(ruta["detalle"]["Z3"]["salida"], "S2")

    def test_escenario_inexistente(self):
        self.assertEqual(self.client.post("/api/escenarios/9999/ejecutar/").status_code, 404)

    def test_ejecutar_exige_csrf_desde_el_navegador(self):
        cliente = Client(enforce_csrf_checks=True)
        s0 = Escenario.objects.get(nombre="S0")
        self.assertEqual(cliente.post(f"/api/escenarios/{s0.id}/ejecutar/").status_code, 403)

    @override_settings(API_TOKEN="clave")
    def test_comandos_con_token(self):
        self.assertEqual(self.client.get("/api/comandos/").status_code, 401)
        self.assertEqual(self.client.get("/api/comandos/", HTTP_X_TOKEN="clave").status_code, 200)


class ApiHistorico(TestCase):
    def setUp(self):
        def enviar(datos):
            self.client.post("/api/eventos/", json.dumps(datos), content_type="application/json")
        enviar(linea_esp32(evento="LISTO", estado="NORMAL", ms=3000))
        enviar(linea_esp32(evento="B0", ms=5000))
        enviar(linea_esp32(["e2", "e3", "e6"], evento="B4", ms=7000))
        malo = linea_esp32(["e6"], evento="B2", ms=9000)
        malo["rutas"]["Z1"]["costo_m"] = 99.0
        enviar(malo)

    def pedir(self, consulta=""):
        r = self.client.get(f"/api/historico/{consulta}")
        self.assertEqual(r.status_code, 200)
        return r.json()

    def test_todo_ordenado_del_mas_nuevo_al_mas_antiguo(self):
        datos = self.pedir()
        self.assertEqual(datos["total"], 4)
        self.assertEqual([e["esp32"]["evento"] for e in datos["eventos"]], ["B2", "B4", "B0", "LISTO"])
        self.assertIn("detalle", datos["eventos"][0]["servidor"])

    def test_filtros(self):
        self.assertEqual(self.pedir("?estado=RUTA_PARCIAL")["total"], 1)
        self.assertEqual(self.pedir("?evento=LISTO")["total"], 1)
        self.assertEqual(self.pedir("?coincide=no")["eventos"][0]["esp32"]["evento"], "B2")
        self.assertEqual(self.pedir("?coincide=si")["total"], 3)
        self.assertEqual(len(self.pedir("?limite=2")["eventos"]), 2)
        self.assertEqual(self.pedir("?desde=2000-01-01&hasta=2999-12-31")["total"], 4)
        self.assertEqual(self.pedir("?hasta=2000-01-01")["total"], 0)

    def test_despues_de_para_el_sondeo(self):
        ids = [e["id"] for e in self.pedir()["eventos"]]
        nuevos = self.pedir(f"?despues_de={ids[1]}")["eventos"]
        self.assertEqual([e["id"] for e in nuevos], [ids[0]])

    def test_parametros_invalidos(self):
        self.assertEqual(self.client.get("/api/historico/?desde=ayer").status_code, 400)
        self.assertEqual(self.client.get("/api/historico/?limite=muchos").status_code, 400)


class ApiDashboard(TestCase):
    def test_pagina_del_dashboard(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="plano"')
        self.assertIn("csrftoken", r.cookies)

    def test_grafo(self):
        datos = self.client.get("/api/grafo/").json()
        self.assertEqual(len(datos["nodos"]), 16)
        self.assertEqual(len(datos["aristas"]), 16)

    def test_simular_no_guarda(self):
        r = self.client.post("/api/simular/", json.dumps({"bloqueos": ["e7"], "alfa_pct": 50, "beta_pct": 100}),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["detalle"]["Z7"]["longitud_m"], 34)   # escenario S2
        self.assertEqual(RutaCalculada.objects.count(), 0)

    def test_simular_valida_parametros(self):
        for cuerpo in ({"alfa_pct": -5}, {"beta_pct": "mucho"}, {"bloqueos": ["x"]}):
            r = self.client.post("/api/simular/", json.dumps(cuerpo), content_type="application/json")
            self.assertEqual(r.status_code, 400, cuerpo)
