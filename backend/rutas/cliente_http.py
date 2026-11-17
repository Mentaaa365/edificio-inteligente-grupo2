"""Envío de una línea JSON del ESP32 al servidor por HTTP.

Lo usan los dos comandos que hacen de "ESP32" desde la PC:
    simular_esp32   inventa los eventos
    puente_serial   los lee del ESP32 real conectado por USB

Se envían por HTTP (y no guardándolos directamente en la base de datos) para que pasen
por el mismo camino que usará el ESP32 con WiFi: validación, token y aviso por WebSocket.
Solo usa la biblioteca estándar (urllib), sin instalar nada más.
"""
import json
import urllib.error
import urllib.request


class ErrorEnvio(Exception):
    """El servidor no respondió o rechazó el evento."""


def enviar_evento(url_servidor: str, linea: dict, token: str = "", origen: str = "esp32",
                  tiempo_max: float = 5) -> dict:
    """Hace POST /api/eventos/ y devuelve la respuesta JSON del servidor.

    origen: "esp32" (placa real) o "simulador"; queda guardado en el evento.
    """
    url = url_servidor.rstrip("/") + "/api/eventos/"
    cabeceras = {"Content-Type": "application/json", "X-Origen": origen}
    if token:
        cabeceras["X-Token"] = token
    peticion = urllib.request.Request(url, data=json.dumps(linea).encode("utf-8"),
                                      headers=cabeceras, method="POST")
    try:
        with urllib.request.urlopen(peticion, timeout=tiempo_max) as respuesta:
            return json.loads(respuesta.read())
    except urllib.error.HTTPError as e:
        raise ErrorEnvio(f"el servidor respondió {e.code}: {e.read().decode('utf-8', 'replace')}") from e
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        motivo = getattr(e, "reason", e)
        raise ErrorEnvio(f"no se pudo conectar con {url}: {motivo}. ¿Está arrancado el servidor?") from e
