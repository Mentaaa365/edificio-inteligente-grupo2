"""Envío de mensajes a todos los navegadores conectados por WebSocket.

Cada pestaña del dashboard se une al grupo "dashboard" (ver consumers.py).
Desde código normal (síncrono) se usa async_to_sync para hablar con la capa de canales.
Referencia: https://channels.readthedocs.io/en/stable/topics/channel_layers.html#using-outside-of-consumers
"""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

GRUPO = "dashboard"


def enviar(tipo: str, datos: dict) -> None:
    capa = get_channel_layer()
    if capa is None:        # sin CHANNEL_LAYERS configurado: el dashboard usará el sondeo
        return
    # "type" indica qué método del consumidor atiende el mensaje: enviar.mensaje -> enviar_mensaje()
    async_to_sync(capa.group_send)(GRUPO, {"type": "enviar.mensaje", "tipo": tipo, "datos": datos})
