"""Genera docs/Plano_montaje_60x60.png: plano de replanteo de la maqueta con medidas en cm.

    python herramientas/plano_montaje.py

Lee nodos y pasillos de modelo/grafo.json. Los recintos (rectángulos de las zonas), el área de la
electrónica y el panel de control se definen aquí, en metros del modelo (1 m = 1 LED = 1,667 cm).
El script comprueba que cada pasillo mide en la base exactamente su número de LED, que cada puerta
cae dentro de su recinto y que ningún pasillo atraviesa un recinto.
"""
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

RAIZ = Path(__file__).resolve().parent.parent
g = json.loads((RAIZ / "modelo" / "grafo.json").read_text(encoding="utf-8"))
U = g["maqueta"]["cm_por_m"]
ANCHO_CM, ALTO_CM = g["maqueta"]["base_cm"]
pos = {n["id"]: (n["x_m"], n["y_m"]) for n in g["nodos"]}
nombre = {n["id"]: n["nombre"] for n in g["nodos"]}
pasillos = sorted((a for a in g["aristas"] if a["tipo"] == "pasillo"), key=lambda a: a["led_ini"])
puertas = {a["u"]: a for a in g["aristas"] if a["tipo"] == "puerta"}
pir = {s["zona"]: s["id"] for s in g["sensores"]}

# ---- Recintos en metros del modelo (x, y desde la esquina inferior izquierda de la base)
H = 0.6  # holgura de 1 cm a cada lado de la tira
X0, X1 = pos["S1"][0], pos["S3"][0]          # muros oeste y este, en las salidas S1 y S3
YB = pos["C1"][1]                             # pasillo inferior (e1 y e5)
YM = pos["C2"][1]                             # pasillo central (e3)
YT = pos["C5"][1]                             # muro norte, en la salida S2
Y0 = YB - 5.5                                 # muro sur
XC = (pos["C2"][0] + pos["C3"][0]) / 2        # división Laboratorio / Oficina
YR = (YB + YM) / 2                            # división Baños / Bodega
r = lambda x0, y0, x1, y1: [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
recintos = {
    "Z1": r(X0, YB + H, pos["C1"][0] - H, YM - H),
    "Z2": r(X0, Y0, pos["C1"][0] - H, YB - H),
    "Z3": r(pos["C2"][0] + H, Y0, XC - 0.1, YM - H),
    "Z4": r(XC + 0.1, Y0, pos["C3"][0] - H, YM - H),
    "Z5": r(pos["C3"][0] + H, YR + 0.1, X1, YM - H),
    "Z6": r(pos["C4"][0] + H, YB + H, X1, YR - 0.1),
    "Z8": r(pos["C4"][0] + H, Y0, X1, YB - H),
}
(xa, ya), (xb, yb) = pos["C5"], pos["C3"]
x_e8 = lambda y: xa + (xb - xa) * (ya - y) / (ya - yb)
recintos["Z7"] = [(x_e8(YT - 0.5) + 0.7, YT - 0.5), (X1, YT - 0.5), (X1, YM + H), (x_e8(YM + H) + 0.7, YM + H)]


def dentro(p, poly):
    x, y = p
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


# ---- Comprobaciones
for a in pasillos:
    d = math.dist(pos[a["u"]], pos[a["v"]])
    assert abs(d - a["longitud_m"]) < 0.01, f"{a['id']}: mide {d:.2f} m en la base y tiene {a['longitud_m']} LED"
for z, poly in recintos.items():
    assert dentro(pos[z], poly), f"la puerta de {z} no cae en su recinto"
    assert math.dist(pos[z], pos[puertas[z]["v"]]) <= puertas[z]["longitud_m"] + 0.01, z
    for a in pasillos:
        (x1, y1), (x2, y2) = pos[a["u"]], pos[a["v"]]
        for k in range(1, 200):
            t = k / 200
            assert not dentro((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t), poly), f"{a['id']} atraviesa {z}"
    for x, y in poly:
        assert 0 <= x * U <= ANCHO_CM and 0 <= y * U <= ALTO_CM, z

# ---- Dibujo en cm
cm = lambda p: (p[0] * U, p[1] * U)
VERDE, TINTA, GRIS, MORADO, AZUL, NARANJA = "#12805c", "#1b2438", "#5b6476", "#6b2fa0", "#1f5fa8", "#b04a00"
fig, ax = plt.subplots(figsize=(11, 12.4), dpi=150)
ax.set_aspect("equal")
ax.set_xlim(-4, ANCHO_CM + 4)
ax.set_ylim(-7, ALTO_CM + 5)
ax.axis("off")
ax.add_patch(Rectangle((0, 0), ANCHO_CM, ALTO_CM, fc="#fbfaf6", ec=TINTA, lw=2))
for v in range(0, int(max(ANCHO_CM, ALTO_CM)) + 1, 5):
    if v <= ANCHO_CM:
        ax.plot([v, v], [0, ALTO_CM], color="#e4e1d8", lw=0.6, zorder=0)
        ax.text(v, -1.6, f"{v}", ha="center", fontsize=7, color=GRIS)
    if v <= ALTO_CM:
        ax.plot([0, ANCHO_CM], [v, v], color="#e4e1d8", lw=0.6, zorder=0)
        ax.text(-1.4, v, f"{v}", va="center", ha="right", fontsize=7, color=GRIS)
ax.text(ANCHO_CM / 2, -4.0, "cm desde la esquina inferior izquierda de la base", ha="center", fontsize=8, color=GRIS)

ax.add_patch(Rectangle((X0 * U, Y0 * U), (X1 - X0) * U, (YT - Y0) * U, fc="none", ec="#8b93a3", lw=1.2, ls=(0, (4, 2))))
for z, poly in recintos.items():
    ax.add_patch(Polygon([cm(p) for p in poly], closed=True, fc="#ffffff", ec="#c5ccd8", lw=1, zorder=1))
    cx = (min(p[0] for p in poly) + max(p[0] for p in poly)) / 2 * U
    ytop = max(p[1] for p in poly) * U
    ax.text(cx, ytop - 2.0, f"{z} {nombre[z]}", ha="center", va="center", fontsize=8, fontweight="bold", color=TINTA, zorder=3)
    if z in pir:
        ax.text(cx, ytop - 4.6, pir[z], ha="center", va="center", fontsize=7.5, fontweight="bold", color="white",
                zorder=4, bbox=dict(boxstyle="round,pad=0.3", fc=MORADO, ec="none"))
    (px, py), (qx, qy) = cm(pos[z]), cm(pos[puertas[z]["v"]])
    ax.plot([qx, px], [qy, py], ls="--", lw=1, color="#8791a5", zorder=2)
    ax.scatter([px], [py], s=14, color="#8791a5", zorder=3)

etiqueta = {"e1": (0, 2.2), "e2": (-3.4, 0), "e3": (0, 2.0), "e4": (-3.4, 0), "e5": (0, 2.2),
            "e6": (-3.6, 0), "e7": (-8.2, -3.4), "e8": (3.0, 1.8)}
for a in pasillos:
    desde = a["led_desde"]
    hacia = a["v"] if a["u"] == desde else a["u"]
    (xa, ya), (xb, yb) = cm(pos[desde]), cm(pos[hacia])
    n = a["longitud_m"]
    ax.plot([xa, xb], [ya, yb], lw=9, color=VERDE, alpha=0.18, solid_capstyle="butt", zorder=2)
    xs = [xa + (xb - xa) * (k + 0.5) / n for k in range(n)]
    ys = [ya + (yb - ya) * (k + 0.5) / n for k in range(n)]
    ax.scatter(xs, ys, s=10, color=VERDE, zorder=3)
    ax.scatter(xs[:1], ys[:1], s=26, color="white", edgecolor=VERDE, lw=1.4, zorder=4)
    xm, ym = (xa + xb) / 2, (ya + yb) / 2
    dx, dy = (xb - xa) / n, (yb - ya) / n
    ax.annotate("", xy=(xm + 1.2 * dx, ym + 1.2 * dy), xytext=(xm - 1.2 * dx, ym - 1.2 * dy),
                arrowprops=dict(arrowstyle="-|>", color=VERDE, lw=1.6, mutation_scale=12), zorder=5)
    ox, oy = etiqueta[a["id"]]
    ax.text(xm + ox, ym + oy, f"{a['id']} · {n} LED · {a['pulsador']}\n[{a['led_ini']}–{a['led_fin']}]",
            ha="center", va="center", fontsize=7, color="#0f5a45", fontweight="bold", zorder=6, linespacing=1.1)

coord = {"S1": (0, -2.4), "S3": (0, -2.4), "S2": (-5.4, -0.3), "C5": (5.4, -0.6), "C1": (2.6, -1.6),
         "C4": (-2.6, -1.6), "C2": (-3.8, 1.2), "C3": (4.0, -2.4)}
for nid, (ox, oy) in coord.items():
    x, y = cm(pos[nid])
    if nid.startswith("S"):
        ax.add_patch(FancyBboxPatch((x - 2.1, y - 1.2), 4.2, 2.4, boxstyle="round,pad=0.1,rounding_size=0.4",
                                    fc="#1f7a4d", ec="none", zorder=7))
        ax.text(x, y, nid, ha="center", va="center", fontsize=8.5, color="white", fontweight="bold", zorder=8)
    else:
        ax.scatter([x], [y], s=55, color=TINTA, edgecolor="white", lw=1.2, zorder=7)
        ax.text(x + 1.3, y + 1.2, nid, fontsize=8, fontweight="bold", color=TINTA, zorder=8)
    ax.text(x + ox, y + oy, f"({x:.1f}; {y:.1f})".replace(".", ","), ha="center", fontsize=6.5, color=GRIS, zorder=8)

# Esquinas que se doblan y puentes de 3 hilos
for nid, (ox, oy) in {"C1": (-2.4, -1.9), "C2": (-2.4, -1.9), "C3": (-2.7, -1.9), "C4": (0.9, -2.2), "C5": (-3.4, -2.4)}.items():
    x, y = cm(pos[nid])
    ax.text(x + ox, y + oy, "D", fontsize=7, color=NARANJA, fontweight="bold", zorder=9)
for j, a, b, rad in (("J5", "S3", "C2", -0.25), ("J7", "S2", "C5", 0.5)):
    (xa, ya), (xb, yb) = cm(pos[a]), cm(pos[b])
    ax.annotate("", xy=(xb, yb), xytext=(xa, ya), arrowprops=dict(arrowstyle="-|>", color=NARANJA, lw=1,
                ls=(0, (3, 2)), connectionstyle=f"arc3,rad={rad}"), zorder=2)
    largo = math.dist((xa, ya), (xb, yb))
    lx, ly = ((xa + xb) / 2 - 7, (ya + yb) / 2) if j == "J5" else ((xa + xb) / 2, (ya + yb) / 2 - 3.6)
    ax.text(lx, ly, f"{j} (~{math.ceil(round(largo) / 5) * 5 + 5} cm)", fontsize=7, color=NARANJA, fontweight="bold")

ax.add_patch(Rectangle((1, 0.6), 25, 5.4, fc="#eef3fb", ec=AZUL, lw=1.2, zorder=1))
ax.text(13.5, 3.3, "ELECTRÓNICA: protoboard + ESP32 + 74AHCT125 + transistor del zumbador\n"
        "jack de 5 V en el borde izquierdo · datos a S1 (LED 0)", ha="center", va="center", fontsize=6.4,
        color=AZUL, fontweight="bold")
ax.add_patch(Rectangle((2, ALTO_CM - 6), ANCHO_CM - 4, 5.4, fc="#eef3fb", ec=AZUL, lw=1.2, zorder=1))
ax.text(ANCHO_CM / 2, ALTO_CM - 1.9, "PANEL DE CONTROL", ha="center", fontsize=7.5, fontweight="bold", color=AZUL)
botones = [(c["id"], c["funcion"].capitalize()) for c in g["controles"]]
botones += [(a["pulsador"], a["id"]) for a in pasillos]
botones.sort(key=lambda b: int(b[0][1:]))
for k, (b, f) in enumerate(botones):
    x = 2 + 2.8 + k * (ANCHO_CM - 4) / len(botones)
    color = "#d03b2f" if b == "B0" else "#2c63b5" if b == "B7" else TINTA
    ax.add_patch(Rectangle((x - 0.6, ALTO_CM - 4.2), 1.2, 1.2, fc=color, ec="none", zorder=2))
    ax.text(x, ALTO_CM - 5.7, f"{b}\n{f}", ha="center", va="bottom", fontsize=6.2, color=TINTA, linespacing=1.0)

ax.text(-3.6, ALTO_CM + 3.6, f"Plano de replanteo · base de {ANCHO_CM} × {ALTO_CM} cm", fontsize=15,
        fontweight="bold", color=TINTA)
ax.text(-3.6, ALTO_CM + 1.6, "Grupo 2 · 8 pasillos y 82 LED (1 LED = 1 m del modelo = 1,667 cm, tira de 60 LED/m). "
        "Generado desde modelo/grafo.json.", fontsize=8.2, color=GRIS)
ax.text(-3.6, -6.6, "Círculo blanco: primer LED de cada tramo · flecha verde: sentido de los datos · [a–b]: índices LED · "
        "D: esquina que se dobla sin cortar · J5, J7: puentes de 3 hilos soldados (5 V, datos, GND)",
        fontsize=7, color=GRIS)
fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
destino = RAIZ / "docs" / "Plano_montaje_60x60.png"
fig.savefig(destino, facecolor="white")
print("Plano de replanteo:", destino.relative_to(RAIZ))
for nid in ("S1", "C1", "C4", "S3", "C2", "C3", "C5", "S2"):
    print(f"  {nid}: x = {pos[nid][0] * U:5.1f} cm, y = {pos[nid][1] * U:5.1f} cm")
