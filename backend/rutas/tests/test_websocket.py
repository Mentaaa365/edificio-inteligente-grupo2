"""Pruebas del tiempo real con el comunicador de pruebas de Channels.
Referencia: https://channels.readthedocs.io/en/stable/topics/testing.html"""
import json

from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import Client, TransactionTestCase

from edificio.asgi import application
from rutas import motor
from rutas.tests.test_api import linea_esp32


class TiempoReal(TransactionTestCase):
    # TransactionTestCase: los datos se confirman de verdad, así se ejecuta transaction.on_commit().
    # Ojo: al terminar vacía la base de datos, por eso cada prueba crea lo que necesita.

    async def conectar(self):
        # El navegador siempre envía la cabecera Origin; sin ella AllowedHostsOriginValidator rechaza la conexión.
        com = WebsocketCommunicator(application, "/ws/dashboard/",
                                    headers=[(b"host", b"localhost"), (b"origin", b"http://localhost:8000")])
        conectado, _ = await com.connect()
        self.assertTrue(conectado)
        self.assertEqual((await com.receive_json_from())["tipo"], "hola")
        return com

    async def test_evento_llega_al_navegador(self):
        com = await self.conectar()
        datos = linea_esp32(["e6"], evento="B4")
        cliente = Client()
        respuesta = await sync_to_async(cliente.post)(
            "/api/eventos/", json.dumps(datos), content_type="application/json")
        self.assertEqual(respuesta.status_code, 201)

        mensaje = await com.receive_json_from(timeout=2)
        self.assertEqual(mensaje["tipo"], "evento")
        self.assertEqual(mensaje["datos"]["esp32"]["evento"], "B4")
        self.assertTrue(mensaje["datos"]["servidor"]["coincide_esp32"])
        self.assertEqual(mensaje["datos"]["servidor"]["rutas"], motor.calcular(["e6"])["rutas"])
        await com.disconnect()

    async def test_escenario_ejecutado_llega_al_navegador(self):
        from rutas.models import Escenario
        com = await self.conectar()
        s2, _ = await Escenario.objects.aget_or_create(nombre="S2", defaults={"bloqueos": ["e7"]})
        await sync_to_async(Client().post)(f"/api/escenarios/{s2.id}/ejecutar/")
        mensaje = await com.receive_json_from(timeout=2)
        self.assertEqual(mensaje["tipo"], "escenario")
        self.assertEqual(mensaje["datos"]["escenario"], "S2")
        await com.disconnect()

    async def test_rechaza_origen_no_permitido(self):
        com = WebsocketCommunicator(application, "/ws/dashboard/",
                                    headers=[(b"host", b"localhost"), (b"origin", b"http://sitio-ajeno.com")])
        conectado, _ = await com.connect()
        self.assertFalse(conectado)
