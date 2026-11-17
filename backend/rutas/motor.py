"""Puente entre Django y el modelo de la Fase 1.

El servidor NO reimplementa el algoritmo: importa simulacion/modelo.py (el mismo
que se verificó contra el firmware en 65 536 combinaciones) y lee modelo/grafo.json.
Este archivo solo hace tres cosas:

1. Llamar a modelo.calcular_campo() con los bloqueos y zonas ocupadas recibidos.
2. Escribir el resultado con el MISMO formato que imprime el ESP32 por serie.
3. Comparar la respuesta del ESP32 con la del servidor y listar las diferencias.
"""
from __future__ import annotations

import sys
import time
from functools import lru_cache
from pathlib import Path

# simulacion/ no es un paquete instalado: se añade su carpeta a la ruta de búsqueda de Python.
CARPETA_SIMULACION = Path(__file__).resolve().parents[2] / "simulacion"
if str(CARPETA_SIMULACION) not in sys.path:
    sys.path.insert(0, str(CARPETA_SIMULACION))

import modelo  # noqa: E402  (simulacion/modelo.py)

INF = modelo.INF
# Estados que puede enviar el firmware (NOMBRE_ESTADO en evacuacion_esp32.ino).
ESTADOS_ESP32 = ("INICIALIZANDO", "NORMAL", "RUTA_ACTIVA", "RUTA_PARCIAL", "SIN_RUTA")
# Con estos estados el ESP32 no está en emergencia: su estado no se compara con el del modelo.
ESTADOS_SIN_ALARMA = ("INICIALIZANDO", "NORMAL")


@lru_cache(maxsize=1)
def edificio() -> modelo.Edificio:
    """Carga grafo.json una sola vez y lo reutiliza en todas las peticiones."""
    return modelo.cargar()


def validar_entradas(bloqueos, ocupadas) -> None:
    """Lanza ValueError si llega un pasillo o una zona que no existe en grafo.json."""
    ed = edificio()
    desconocidos = [e for e in bloqueos if e not in ed.pasillos]
    if desconocidos:
        raise ValueError(f"Pasillos desconocidos en bloqueos: {desconocidos}. Válidos: {ed.pasillos}")
    desconocidas = [z for z in ocupadas if z not in ed.zonas]
    if desconocidas:
        raise ValueError(f"Zonas desconocidas en ocupadas: {desconocidas}. Válidas: {ed.zonas}")


def costo_esp32(costo_entero: int) -> float | None:
    """Convierte un costo entero (0,0001 m) a metros igual que imprimirMetros() del firmware:
    parte entera, punto y DOS decimales truncados (no redondeados)."""
    if costo_entero == INF:
        return None
    metros = costo_entero // modelo.ESCALA
    centesimas = (costo_entero % modelo.ESCALA) // 100
    return metros + centesimas / 100


def calcular(bloqueos=(), ocupadas=(), alfa_pct: int | None = None, beta_pct: int | None = None) -> dict:
    """Calcula el campo de evacuación y lo devuelve listo para guardar o enviar como JSON.

    - "rutas" tiene exactamente el formato del ESP32: {"Z1": {"costo_m": 11.0, "ruta": "Z1>C1>S1"}, "Z2": None, ...}
    - "detalle" añade lo que el ESP32 no envía: aristas de la ruta, metros reales, tiempo y salida.
    """
    ed = edificio()
    validar_entradas(bloqueos, ocupadas)
    # Mismo orden que el firmware: los pasillos por índice y las zonas por número.
    bloqueos = [e for e in ed.pasillos if e in set(bloqueos)]
    ocupadas = [z for z in ed.zonas if z in set(ocupadas)]
    p = ed.parametros
    alfa = p["alfa_pct"] if alfa_pct is None else int(alfa_pct)
    beta = p["beta_pct"] if beta_pct is None else int(beta_pct)

    inicio = time.perf_counter_ns()
    campo = modelo.calcular_campo(ed, set(bloqueos), set(ocupadas), alfa, beta)
    calculo_us = (time.perf_counter_ns() - inicio) // 1000

    rutas, detalle = {}, {}
    for z in ed.zonas:
        if not campo.rutas[z]:                       # zona aislada: el firmware imprime null
            rutas[z] = None
            detalle[z] = {"aristas": [], "costo_m": None, "longitud_m": None, "tiempo_s": None, "salida": None}
            continue
        rutas[z] = {"costo_m": costo_esp32(campo.dist[z]), "ruta": ">".join(campo.rutas[z])}
        longitud = modelo.longitud_real_m(ed, campo, z)
        detalle[z] = {
            "aristas": campo.aristas_ruta[z],
            "costo_m": campo.dist[z] / modelo.ESCALA,         # costo exacto, sin truncar
            "longitud_m": longitud,                            # metros físicos, sin penalizaciones
            "tiempo_s": round(longitud / p["velocidad_m_s"], 1),
            "salida": campo.salida(z),
        }

    # Aristas libres que no llegan a ninguna salida: en la tira se ven en ámbar
    # (misma regla que pintar() del firmware: los dos extremos tienen costo infinito).
    aristas_aisladas = [
        a["id"] for a in ed.aristas
        if a["id"] not in bloqueos and campo.dist[a["u"]] == INF and campo.dist[a["v"]] == INF
    ]

    return {
        "estado": modelo.estado(campo),
        "bloqueos": bloqueos,
        "ocupadas": ocupadas,
        "alfa_pct": alfa,
        "beta_pct": beta,
        "explorados": campo.explorados,
        "aisladas": len(campo.aisladas),
        "zonas_aisladas": campo.aisladas,
        "rutas": rutas,
        "detalle": detalle,
        "sentido": {e: list(d) for e, d in campo.sentido.items()},  # arista -> [desde, hacia]
        "aristas_aisladas": aristas_aisladas,
        "calculo_us": calculo_us,
    }


def comparar(esp32: dict, servidor: dict) -> list[str]:
    """Compara lo que calculó el ESP32 con lo que calculó el servidor.

    Devuelve la lista de diferencias en texto; si está vacía, coinciden.
    El estado solo se compara en emergencia, porque sin alarma el firmware
    informa NORMAL aunque tenga las rutas calculadas.
    """
    diferencias = []
    if esp32.get("estado") not in ESTADOS_SIN_ALARMA and esp32.get("estado") != servidor["estado"]:
        diferencias.append(f"estado: ESP32 {esp32.get('estado')} / servidor {servidor['estado']}")
    if esp32.get("aisladas") != servidor["aisladas"]:
        diferencias.append(f"aisladas: ESP32 {esp32.get('aisladas')} / servidor {servidor['aisladas']}")
    if esp32.get("explorados") != servidor["explorados"]:
        diferencias.append(f"explorados: ESP32 {esp32.get('explorados')} / servidor {servidor['explorados']}")

    rutas_esp32 = esp32.get("rutas") or {}
    for zona, r_srv in servidor["rutas"].items():
        if zona not in rutas_esp32:
            diferencias.append(f"{zona}: el ESP32 no la envió")
            continue
        r_esp = rutas_esp32[zona]
        if r_esp is None or r_srv is None:
            if (r_esp is None) != (r_srv is None):
                diferencias.append(f"{zona}: ESP32 {r_esp and r_esp.get('ruta') or 'aislada'}"
                                   f" / servidor {r_srv and r_srv['ruta'] or 'aislada'}")
            continue
        if r_esp.get("ruta") != r_srv["ruta"]:
            diferencias.append(f"{zona}: ruta ESP32 {r_esp.get('ruta')} / servidor {r_srv['ruta']}")
        costo = r_esp.get("costo_m")
        if not isinstance(costo, (int, float)) or abs(costo - r_srv["costo_m"]) > 0.001:
            diferencias.append(f"{zona}: costo ESP32 {costo} / servidor {r_srv['costo_m']}")
    return diferencias


def grafo_para_dashboard() -> dict:
    """Datos de grafo.json que necesita el navegador para dibujar el plano."""
    datos = edificio().datos
    return {
        "maqueta": datos["maqueta"],
        "parametros": datos["parametros"],
        "nodos": datos["nodos"],
        "aristas": datos["aristas"],
        "sensores": datos["sensores"],
    }
