"""Genera docs/Plano_montaje_60x60.png: plano de replanteo de la maqueta con medidas en cm.

    python herramientas/plano_montaje.py

Todo sale de modelo/grafo.json: muros del edificio, salas y puertas de cada zona, intersecciones, salidas y el
recorrido de cada pasillo (con sus quiebres en ángulo recto). Aquí solo se definen las áreas fuera del edificio
(electrónica, panel de control y punto de encuentro) y la posición de los rótulos. El script comprueba que cada
pasillo mide en la base exactamente su número de LED, que cada puerta queda a la distancia del modelo, que ninguna
tira atraviesa una sala y que las salidas están en un muro exterior.
"""
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, FancyBboxPatch, Polygon, Rectangle

RAIZ = Path(__file__).resolve().parent.parent
g = json.loads((RAIZ / "modelo" / "grafo.json").read_text(encoding="utf-8"))
U = g["maqueta"]["cm_por_m"]
ANCHO_CM, ALTO_CM = g["maqueta"]["base_cm"]
EDIFICIO = [tuple(p) for p in g["maqueta"]["edificio"]]
MUROS = list(zip(EDIFICIO, EDIFICIO[1:] + EDIFICIO[:1]))
nodo = {n["id"]: n for n in g["nodos"]}
pos = {n["id"]: (n["x_m"], n["y_m"]) for n in g["nodos"]}
pasillos = sorted((a for a in g["aristas"] if a["tipo"] == "pasillo"), key=lambda a: a["led_ini"])
puerta_de = {a["u"]: a for a in g["aristas"] if a["tipo"] == "puerta"}
pir = {s["zona"]: s["id"] for s in g["sensores"]}
zonas = [n["id"] for n in g["nodos"] if n["tipo"] == "zona"]
salidas = [n["id"] for n in g["nodos"] if n["tipo"] == "salida"]


def recorrido(a):
    """Puntos del pasillo desde su primer LED (led_desde) hasta el otro extremo."""
    pts = [pos[a["u"]], *[tuple(p) for p in a.get("trazo", [])], pos[a["v"]]]
    return pts if a["led_desde"] == a["u"] else pts[::-1]


def dentro(p, poly):
    x, y = p
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def rect(z):
    x0, y0, x1, y1 = nodo[z]["sala"]
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def en_muro(p):
    x, y = p
    return [((x1, y1), (x2, y2)) for (x1, y1), (x2, y2) in MUROS
            if (x1 == x2 == x and min(y1, y2) <= y <= max(y1, y2)) or (y1 == y2 == y and min(x1, x2) <= x <= max(x1, x2))]


# ---- Comprobaciones
for a in pasillos:
    pts = recorrido(a)
    largo = sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))
    assert abs(largo - a["longitud_m"]) < 1e-6, f"{a['id']}: mide {largo:.2f} m en la base y tiene {a['longitud_m']} LED"
    for p, q in zip(pts, pts[1:]):
        assert p[0] == q[0] or p[1] == q[1], f"{a['id']}: los tramos deben ser horizontales o verticales"
        for z in zonas:
            for k in range(1, 100):
                t = k / 100
                assert not dentro((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t), rect(z)), f"{a['id']} cruza {z}"
for z in zonas:
    assert dentro(pos[z], rect(z)), f"la puerta de {z} no cae en su sala"
    assert math.dist(pos[z], pos[puerta_de[z]["v"]]) <= puerta_de[z]["longitud_m"] + 1e-3, z
    x0, y0, x1, y1 = nodo[z]["sala"]
    assert dentro(((x0 + x1) / 2, (y0 + y1) / 2), EDIFICIO), f"{z} queda fuera del edificio"
for s in salidas:
    assert en_muro(pos[s]), f"{s} no está en un muro exterior"

# ---- Dibujo en cm
cm = lambda p: (p[0] * U, p[1] * U)
VERDE, TINTA, GRIS, MORADO, AZUL, NARANJA, ROJO = "#12805c", "#1b2438", "#5b6476", "#6b2fa0", "#1f5fa8", "#b04a00", "#c8372d"
PASILLO, FONDO = "#e4f4ea", "#fbfaf6"
fig, ax = plt.subplots(figsize=(11, 12.6), dpi=150)
ax.set_aspect("equal")
ax.set_xlim(-4, ANCHO_CM + 4)
ax.set_ylim(-8, ALTO_CM + 6)
ax.axis("off")
ax.add_patch(Rectangle((0, 0), ANCHO_CM, ALTO_CM, fc=FONDO, ec=TINTA, lw=2))
for v in range(0, int(max(ANCHO_CM, ALTO_CM)) + 1, 5):
    ax.plot([v, v], [0, ALTO_CM], color="#ece9e1", lw=0.5, zorder=0)
    ax.plot([0, ANCHO_CM], [v, v], color="#ece9e1", lw=0.5, zorder=0)
    ax.text(v, -1.6, f"{v}", ha="center", fontsize=7, color=GRIS)
    ax.text(-1.4, v, f"{v}", va="center", ha="right", fontsize=7, color=GRIS)
ax.text(ANCHO_CM / 2, -4.0, "cm desde la esquina inferior izquierda de la base", ha="center", fontsize=8, color=GRIS)

# Edificio: fondo de pasillo, salas encima y muro exterior
ax.add_patch(Polygon([cm(p) for p in EDIFICIO], closed=True, fc=PASILLO, ec="none", zorder=1))
for z in zonas:
    x0, y0, x1, y1 = nodo[z]["sala"]
    ax.add_patch(Rectangle(cm((x0, y0)), (x1 - x0) * U, (y1 - y0) * U, fc="white", ec=TINTA, lw=1.4, zorder=2))
    alto_sala = (y1 - y0) * U
    ytxt = y1 * U - (3.6 if alto_sala < 10 else 2.0)
    ax.text((x0 + x1) / 2 * U, ytxt, f"{z}\n{nodo[z]['nombre']}", ha="center", va="top", fontsize=8,
            fontweight="bold", color=TINTA, zorder=6, linespacing=1.15)
    if z in pir:
        corto = alto_sala < 10
        ax.text((x0 + x1) / 2 * U + (7.5 if corto else 0), (y0 + y1) / 2 * U - (0 if corto else 2), pir[z], ha="center",
                va="center", fontsize=7, fontweight="bold", color="white", zorder=12,
                bbox=dict(boxstyle="round,pad=0.3", fc=MORADO, ec="none"))
ax.add_patch(Polygon([cm(p) for p in EDIFICIO], closed=True, fc="none", ec=TINTA, lw=3.2, zorder=3, joinstyle="miter"))

# Puertas: abertura en el muro y hoja que gira hacia dentro de la sala
for z in zonas:
    (hx, hy), (ex, ey) = cm(nodo[z]["puerta"][0]), cm(nodo[z]["puerta"][1])
    ax.plot([hx, ex], [hy, ey], color=PASILLO, lw=3.4, zorder=4, solid_capstyle="butt")
    x0, y0, x1, y1 = nodo[z]["sala"]
    cx, cy = (x0 + x1) / 2 * U, (y0 + y1) / 2 * U
    r = math.dist((hx, hy), (ex, ey))
    normal = (-(ey - hy) / r, (ex - hx) / r)
    if normal[0] * (cx - hx) + normal[1] * (cy - hy) < 0:
        normal = (-normal[0], -normal[1])
    a_muro = math.degrees(math.atan2(ey - hy, ex - hx))
    a_hoja = math.degrees(math.atan2(normal[1], normal[0]))
    t1, t2 = sorted([a_muro, a_hoja])
    if t2 - t1 > 180:
        t1, t2 = t2, t1 + 360
    ax.add_patch(Arc((hx, hy), 2 * r, 2 * r, theta1=t1, theta2=t2, color=TINTA, lw=0.9, zorder=5))
    ax.plot([hx, hx + r * normal[0]], [hy, hy + r * normal[1]], color=TINTA, lw=0.9, zorder=5)

# Salidas: abertura en el muro exterior y cartel hacia fuera
for s in salidas:
    x, y = cm(pos[s])
    (x1, y1), (x2, y2) = en_muro(pos[s])[0]
    w = 0.95 * U
    if y1 == y2:   # muro horizontal: la salida mira hacia arriba o hacia abajo
        ax.plot([x - w, x + w], [y, y], color=FONDO, lw=4, zorder=4)
        fuera = 1 if not dentro((pos[s][0], pos[s][1] + 0.5), EDIFICIO) else -1
        bx, by = x, y + 2.3 * fuera
        cx, cy = x + 5.5, y - 1.5
    else:          # muro vertical: la salida mira a la izquierda o a la derecha
        ax.plot([x, x], [y - w, y + w], color=FONDO, lw=4, zorder=4)
        fuera = 1 if not dentro((pos[s][0] + 0.5, pos[s][1]), EDIFICIO) else -1
        bx, by = x + 3.3 * fuera, y
        cx, cy = bx, y - 2.6
    ax.add_patch(FancyBboxPatch((bx - 2.3, by - 1.0), 4.6, 2.0, boxstyle="round,pad=0.1,rounding_size=0.3",
                                fc="#1f7a4d", ec="none", zorder=7))
    ax.text(bx, by, f"SALIDA {s}", ha="center", va="center", fontsize=6.3, color="white", fontweight="bold", zorder=8)
    ax.text(cx, cy, f"({x:.1f}; {y:.1f})".replace(".", ","), ha="center", fontsize=6.0, color=GRIS, zorder=8)

# Tira LED
etiqueta = {"e1": (13.3, 17.6), "e2": (15.6, 25.0), "e3": (30.0, 32.6), "e4": (44.6, 28.2), "e5": (46.7, 17.6),
            "e6": (16.3, 40.5), "e7": (22.6, 52.0), "e8": (35.0, 48.3)}
for a in pasillos:
    q = [cm(p) for p in recorrido(a)]
    n = a["longitud_m"]
    ax.plot([p[0] for p in q], [p[1] for p in q], color="#24303f", lw=4.2, zorder=8, solid_capstyle="butt",
            solid_joinstyle="miter")
    tramos = list(zip(q, q[1:]))
    largos = [math.dist(p, r) for p, r in tramos]
    total = sum(largos)

    def en(t):
        for (p, r), l in zip(tramos, largos):
            if t <= l:
                return p[0] + (r[0] - p[0]) * t / l, p[1] + (r[1] - p[1]) * t / l
            t -= l
        return q[-1]

    leds = [en((k + 0.5) / n * total) for k in range(n)]
    ax.scatter([p[0] for p in leds], [p[1] for p in leds], s=7, color="#7cfc9a", zorder=9)
    ax.scatter([leds[0][0]], [leds[0][1]], s=22, color="white", edgecolor=VERDE, lw=1.3, zorder=10)
    x, y = etiqueta.get(a["id"], en(total / 2))
    ax.text(x, y, f"{a['id']} · {n} LED · {a['pulsador']}\n[{a['led_ini']}–{a['led_fin']}]", ha="center", va="center",
            fontsize=6.6, color="#0f5a45", fontweight="bold", zorder=11, linespacing=1.05,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
desfase = {"C1": (1.0, 1.0), "C2": (-2.9, 1.0), "C3": (1.0, 1.0), "C4": (-2.9, 1.0), "C5": (-4.2, 1.2)}
for c, (dx, dy) in desfase.items():
    x, y = cm(pos[c])
    ax.scatter([x], [y], s=30, color=TINTA, edgecolor="white", lw=1, zorder=11)
    ax.text(x + dx, y + dy, c, fontsize=7.5, fontweight="bold", color=TINTA, zorder=12,
            bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.8))

# Pliegues (D): cada cambio de dirección dentro de una misma pieza de tira
PIEZAS = [["e1", "e2", "e3", "e4", "e5"], ["e6", "e7"], ["e8"]]
por_id = {a["id"]: a for a in pasillos}
pliegues = []
for pieza in PIEZAS:
    pts = []
    for pid in pieza:
        r = recorrido(por_id[pid])
        assert not pts or pts[-1] == r[0], f"{pid} no continúa la pieza {pieza}"
        pts += r if not pts else r[1:]
    for p, q, r in zip(pts, pts[1:], pts[2:]):
        if (q[0] - p[0]) * (r[1] - q[1]) - (q[1] - p[1]) * (r[0] - q[0]) != 0:
            pliegues.append(q)
for p in pliegues:
    x, y = cm(p)
    ax.text(x - 1.5, y - 1.7, "D", fontsize=6.3, color=NARANJA, fontweight="bold", zorder=12)
for j, a, b, rad, lab, texto in (("J5", "S3", "C2", -0.3, (25.5, 12.0), "~45 cm,\npor debajo de la base"),
                                 ("J7", "S2", "C5", -0.6, (29.5, 50.5), "~15 cm")):
    (xa, ya), (xb, yb) = cm(pos[a]), cm(pos[b])
    ax.annotate("", xy=(xb, yb), xytext=(xa, ya), arrowprops=dict(arrowstyle="-|>", color=NARANJA, lw=1,
                ls=(0, (3, 2)), connectionstyle=f"arc3,rad={rad}"), zorder=6)
    ax.text(*lab, f"{j} ({texto})", fontsize=6.8, color=NARANJA, fontweight="bold", zorder=12)

# Extintores (adhesivos decorativos)
for p in [(5, 19.8), (31, 19.8), (13.4, 25.6), (31, 4.8)]:
    x, y = cm(p)
    ax.add_patch(Rectangle((x - 0.55, y - 0.75), 1.1, 1.5, fc=ROJO, ec="none", zorder=12))

# Áreas fuera del edificio
ax.add_patch(Rectangle((1, 0.6), 25, 5.4, fc="#eef3fb", ec=AZUL, lw=1.2, zorder=1))
ax.text(13.5, 3.3, "ELECTRÓNICA: protoboard, ESP32, 74AHCT125, transistor del zumbador\n"
        "jack de 5 V en el borde izquierdo · datos a S1 (LED 0)", ha="center", va="center", fontsize=6.2,
        color=AZUL, fontweight="bold")
ax.add_patch(Rectangle((42.5, 37.5), 16.5, 21.5, fc="#eef3fb", ec=AZUL, lw=1.2, zorder=1))
ax.text(50.75, 57.3, "PANEL DE CONTROL", ha="center", fontsize=7.5, fontweight="bold", color=AZUL)
botones = [(c["id"], c["funcion"].capitalize()) for c in g["controles"]] + [(a["pulsador"], a["id"]) for a in pasillos]
botones.sort(key=lambda b: int(b[0][1:]))
for k, (b, f) in enumerate(botones):
    x, y = 45.5 + (k // 5) * 8.5, 53.5 - (k % 5) * 3.6
    ax.add_patch(Rectangle((x - 0.6, y - 0.6), 1.2, 1.2, fc=ROJO if b == "B0" else "#2c63b5" if b == "B7" else TINTA,
                           ec="none"))
    ax.text(x + 1.2, y, f"{b} · {f}", va="center", fontsize=6.8, color=TINTA)
ax.add_patch(Rectangle((1.5, 49), 15, 9.5, fc=PASILLO, ec=VERDE, lw=1.2, zorder=1))
ax.text(9, 53.8, "PUNTO DE\nENCUENTRO", ha="center", va="center", fontsize=8.5, fontweight="bold", color=VERDE)
leyenda = [("#24303f", "Tira LED (círculo blanco:\nprimer LED del tramo)"), (PASILLO, "Pasillo"),
           ("#1f7a4d", "Salida de emergencia"), (MORADO, "Sensor PIR"), (ROJO, "Extintor (adhesivo)"),
           (NARANJA, "D: pliegue · J5, J7: puentes")]
ax.text(1.5, 46.6, "LEYENDA", fontsize=7.5, fontweight="bold", color=TINTA)
for k, (c, t) in enumerate(leyenda):
    y = 44.6 - k * 1.65
    ax.add_patch(Rectangle((1.5, y - 0.5), 1.4, 1.0, fc=c, ec="#c5ccd8", lw=0.5))
    ax.text(3.4, y, t, va="center", fontsize=6.0, color=TINTA, linespacing=1.0)

ax.text(-3.6, ALTO_CM + 4.2, f"Plano de replanteo · base de {ANCHO_CM} × {ALTO_CM} cm", fontsize=15,
        fontweight="bold", color=TINTA)
ax.text(-3.6, ALTO_CM + 2.0, "Grupo 2 · 8 pasillos, 82 LED (1 LED = 1 m del modelo = 1,667 cm, tira de 60 LED/m). "
        "Generado desde modelo/grafo.json.", fontsize=8, color=GRIS)
ax.text(-3.6, -7.0, "Puertas: el arco marca el giro de la hoja. Cada pasillo mide en la base su número de LED × 1,667 cm. "
        "Entre paréntesis, coordenadas de las salidas en cm.", fontsize=7, color=GRIS)
fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
destino = RAIZ / "docs" / "Plano_montaje_60x60.png"
fig.savefig(destino, facecolor="white")
print("Plano de replanteo:", destino.relative_to(RAIZ), "·", len(pliegues), "pliegues")
for nid in ("S1", "C1", "C4", "S3", "C2", "C3", "C5", "S2"):
    print(f"  {nid}: x = {pos[nid][0] * U:5.1f} cm, y = {pos[nid][1] * U:5.1f} cm")
