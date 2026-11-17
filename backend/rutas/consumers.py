"""Consumidor WebSocket: mantiene abierta la conexión con cada pestaña del dashboard.

Flujo: el navegador abre ws://<servidor>/ws/dashboard/ -> connect() lo une al grupo
-> cuando llega un evento, difusion.enviar() manda un mensaje al grupo
-> enviar_mensaje() lo reenvía a cada navegador como JSON.
Referencia: https://channels.readthedocs.io/en/stable/topics/consumers.html
"""
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .difusion import GRUPO


class DashboardConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(GRUPO, self.channel_name)
        await self.accept()
        await self.send_json({"tipo": "hola", "datos": {"mensaje": "Conectado al servidor del Grupo 2"}})

    async def disconnect(self, code):
        await self.channel_layer.group_discard(GRUPO, self.channel_name)

    async def enviar_mensaje(self, mensaje):
        await self.send_json({"tipo": mensaje["tipo"], "datos": mensaje["datos"]})
