"""Modelo del edificio: grafo ponderado dinámico y cálculo del campo de evacuación.

Este módulo es la referencia en Python del mismo algoritmo que ejecuta el ESP32
(firmware/evacuacion_esp32/rutas.h). Los dos trabajan con costos ENTEROS para que
los resultados se puedan comparar bit a bit.

Peso de una arista e en el instante t (unidad: 0,0001 m):

    w_e = d_e * (100 + ALFA_PCT * o_e) * (100 + BETA_PCT * r_e_pct // 100)

    d_e      longitud en metros (= número de LED del pasillo)
    o_e      1 si el pasillo toca la intersección de una zona ocupada (PIR), si no 0
    r_e_pct  RIESGO_ADY_PCT si la arista comparte un nodo con un pasillo bloqueado, si no 0
    bloqueada -> la arista se elimina (peso infinito)
"""
from __future__ import annotations

import heapq
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx

RAIZ = Path(__file__).resolve().parent.parent
INF = 0xFFFFFFFF
ESCALA = 10_000  # unidades enteras por metro


@dataclass
class Edificio:
    nodos: list[str]
    tipo: dict[str, str]
    pos: dict[str, tuple[float, float]]
    aristas: list[dict]
    parametros: dict
    datos: dict

    @property
    def salidas(self) -> list[str]:
        return [n for n in self.nodos if self.tipo[n] == "salida"]

    @property
    def zonas(self) -> list[str]:
        return [n for n in self.nodos if self.tipo[n] == "zona"]

    @property
    def pasillos(self) -> list[str]:
        return [a["id"] for a in self.aristas if a["tipo"] == "pasillo"]

    def interseccion_de(self, zona: str) -> str:
        for a in self.aristas:
            if a["tipo"] == "puerta" and a["u"] == zona:
                return a["v"]
        raise KeyError(zona)


def cargar(ruta: Path | None = None) -> Edificio:
    datos = json.loads((ruta or RAIZ / "modelo" / "grafo.json").read_text(encoding="utf-8"))
    return Edificio(
        nodos=[n["id"] for n in datos["nodos"]],
        tipo={n["id"]: n["tipo"] for n in datos["nodos"]},
        pos={n["id"]: (n["x_m"], n["y_m"]) for n in datos["nodos"]},
        aristas=datos["aristas"],
        parametros=dict(datos["parametros"]),
        datos=datos,
    )


@dataclass
class Campo:
    """Resultado de un cálculo: para cada nodo, su costo y su siguiente arista hacia la salida."""
    peso: dict[str, int]
    dist: dict[str, int]
    sig: dict[str, str | None]
    explorados: int
    rutas: dict[str, list[str]] = field(default_factory=dict)      # zona -> lista de nodos
    aristas_ruta: dict[str, list[str]] = field(default_factory=dict)  # zona -> lista de aristas
    sentido: dict[str, tuple[str, str]] = field(default_factory=dict)  # arista -> (desde, hacia)

    def costo_m(self, zona: str) -> float | None:
        return None if self.dist[zona] == INF else self.dist[zona] / ESCALA

    def salida(self, zona: str) -> str | None:
        return self.rutas[zona][-1] if self.rutas.get(zona) else None

    @property
    def aisladas(self) -> list[str]:
        return [z for z, r in self.rutas.items() if not r]


def pesos(ed: Edificio, bloqueados: set[str], ocupadas: set[str],
          alfa_pct: int | None = None, beta_pct: int | None = None) -> dict[str, int]:
    p = ed.parametros
    alfa = p["alfa_pct"] if alfa_pct is None else alfa_pct
    beta = p["beta_pct"] if beta_pct is None else beta_pct
    nodos_riesgo = set()
    for a in ed.aristas:
        if a["id"] in bloqueados:
            nodos_riesgo.update((a["u"], a["v"]))
    nodos_congestion = {ed.interseccion_de(z) for z in ocupadas}
    w = {}
    for a in ed.aristas:
        if a["id"] in bloqueados:
            w[a["id"]] = INF
            continue
        o = 1 if a["tipo"] == "pasillo" and (a["u"] in nodos_congestion or a["v"] in nodos_congestion) else 0
        r = p["riesgo_adyacente_pct"] if (a["u"] in nodos_riesgo or a["v"] in nodos_riesgo) else 0
        w[a["id"]] = a["longitud_m"] * (100 + alfa * o) * (100 + beta * r // 100)
    return w


def calcular_campo(ed: Edificio, bloqueados: set[str] = frozenset(), ocupadas: set[str] = frozenset(),
                   alfa_pct: int | None = None, beta_pct: int | None = None) -> Campo:
    """Dijkstra multi-fuente desde las salidas (versión O(V^2), idéntica a la del ESP32)."""
    w = pesos(ed, set(bloqueados), set(ocupadas), alfa_pct, beta_pct)
    dist = {n: INF for n in ed.nodos}
    visto = {n: False for n in ed.nodos}
    for s in ed.salidas:
        dist[s] = 0
    explorados = 0
    while True:
        u, mejor = None, INF
        for n in ed.nodos:                       # mismo orden de nodos que el firmware
            if not visto[n] and dist[n] < mejor:
                u, mejor = n, dist[n]
        if u is None:
            break
        visto[u] = True
        explorados += 1
        for a in ed.aristas:
            if w[a["id"]] == INF:
                continue
            v = a["v"] if a["u"] == u else a["u"] if a["v"] == u else None
            if v is not None and dist[u] + w[a["id"]] < dist[v]:
                dist[v] = dist[u] + w[a["id"]]

    # Siguiente arista: la primera (en orden de índice) que conserva el costo mínimo.
    # Esta regla fija el desempate y es la misma en el firmware.
    sig: dict[str, str | None] = {n: None for n in ed.nodos}
    for n in ed.nodos:
        if ed.tipo[n] == "salida" or dist[n] == INF:
            continue
        for a in ed.aristas:
            if w[a["id"]] == INF:
                continue
            v = a["v"] if a["u"] == n else a["u"] if a["v"] == n else None
            if v is not None and dist[v] != INF and dist[v] + w[a["id"]] == dist[n]:
                sig[n] = a["id"]
                break

    campo = Campo(peso=w, dist=dist, sig=sig, explorados=explorados)
    por_id = {a["id"]: a for a in ed.aristas}
    for z in ed.zonas:
        nodos_r, aristas_r = [], []
        if dist[z] != INF:
            n = z
            nodos_r.append(n)
            while ed.tipo[n] != "salida":
                a = por_id[sig[n]]
                m = a["v"] if a["u"] == n else a["u"]
                aristas_r.append(a["id"])
                campo.sentido[a["id"]] = (n, m)
                nodos_r.append(m)
                n = m
        campo.rutas[z] = nodos_r
        campo.aristas_ruta[z] = aristas_r
    return campo


def longitud_real_m(ed: Edificio, campo: Campo, zona: str) -> float | None:
    """Metros físicos de la ruta (sin penalizaciones), para estimar el tiempo de evacuación."""
    if not campo.rutas[zona]:
        return None
    por_id = {a["id"]: a for a in ed.aristas}
    return float(sum(por_id[e]["longitud_m"] for e in campo.aristas_ruta[zona]))


def estado(campo: Campo) -> str:
    n = len(campo.aisladas)
    if n == 0:
        return "RUTA_ACTIVA"
    return "SIN_RUTA" if n == len(campo.rutas) else "RUTA_PARCIAL"


# --------------------------------------------------------------------------- NetworkX
def grafo_nx(ed: Edificio, w: dict[str, int]) -> nx.Graph:
    g = nx.Graph()
    for n in ed.nodos:
        g.add_node(n, tipo=ed.tipo[n], pos=ed.pos[n])
    for a in ed.aristas:
        g.add_edge(a["u"], a["v"], id=a["id"], longitud=a["longitud_m"],
                   peso=None if w[a["id"]] == INF else w[a["id"]])
    return g


def distancias_nx(ed: Edificio, w: dict[str, int]) -> dict[str, int]:
    """Validación independiente con NetworkX: una arista con peso None queda oculta (bloqueada)."""
    g = grafo_nx(ed, w)
    d = nx.multi_source_dijkstra_path_length(g, set(ed.salidas), weight=lambda u, v, datos: datos["peso"])
    return {n: d.get(n, INF) for n in ed.nodos}


# ------------------------------------------------- comparación de algoritmos (un origen)
def _vecinos(ed: Edificio, w: dict[str, int]) -> dict[str, list[tuple[str, int]]]:
    ady = {n: [] for n in ed.nodos}
    for a in ed.aristas:
        if w[a["id"]] != INF:
            ady[a["u"]].append((a["v"], w[a["id"]]))
            ady[a["v"]].append((a["u"], w[a["id"]]))
    return ady


def heuristica(ed: Edificio, n: str) -> int:
    """Distancia en línea recta a la salida más cercana. Nunca sobreestima (admisible)."""
    return int(min(math.dist(ed.pos[n], ed.pos[s]) for s in ed.salidas) * ESCALA * 0.999)


def buscar(ed: Edificio, w: dict[str, int], origen: str, metodo: str) -> dict:
    """Ruta de un origen a la salida más cercana. metodo: 'dijkstra', 'astar' o 'bfs'.
    Devuelve costo real de la ruta hallada y cuántos nodos se expandieron."""
    ady = _vecinos(ed, w)
    salidas = set(ed.salidas)
    explorados = 0
    if metodo == "bfs":                      # minimiza número de tramos, ignora los pesos
        cola, padre = [origen], {origen: None}
        i = 0
        hallado = None
        while i < len(cola):
            u = cola[i]; i += 1
            explorados += 1
            if u in salidas:
                hallado = u
                break
            for v, _ in ady[u]:
                if v not in padre:
                    padre[v] = u
                    cola.append(v)
    else:
        h = (lambda n: heuristica(ed, n)) if metodo == "astar" else (lambda n: 0)
        g = {origen: 0}
        padre = {origen: None}
        cerrados = set()
        monton = [(h(origen), 0, origen)]
        hallado = None
        while monton:
            _, gu, u = heapq.heappop(monton)
            if u in cerrados:
                continue
            cerrados.add(u)
            explorados += 1
            if u in salidas:
                hallado = u
                break
            for v, peso in ady[u]:
                if v not in cerrados and gu + peso < g.get(v, INF):
                    g[v] = gu + peso
                    padre[v] = u
                    heapq.heappush(monton, (g[v] + h(v), g[v], v))
    if hallado is None:
        return {"ruta": [], "costo": None, "explorados": explorados}
    ruta = []
    n = hallado
    while n is not None:
        ruta.append(n)
        n = padre[n]
    ruta.reverse()
    costo = 0
    for a, b in zip(ruta, ruta[1:]):
        costo += min(p for v, p in ady[a] if v == b)
    return {"ruta": ruta, "costo": costo, "explorados": explorados}
