"""Dibujo del plano del edificio con Matplotlib (plano base y resultado de un escenario)."""
from __future__ import annotations

import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

from modelo import Campo, Edificio

VERDE, ROJO, AMBAR, GRIS, TINTA = "#12805c", "#c8372d", "#c98500", "#b9c0cc", "#1b2438"
MORADO = "#6b2fa0"


def puntos(ed: Edificio, a: dict, desde: str | None = None) -> list[tuple[float, float]]:
    """Recorrido de un pasillo (con sus quiebres en ángulo recto), de u a v o desde el extremo indicado."""
    pts = [ed.pos[a["u"]], *[tuple(p) for p in a.get("trazo", [])], ed.pos[a["v"]]]
    return pts[::-1] if desde == a["v"] else pts


def a_lo_largo(pts, t: float):
    """Punto a la distancia t (en metros del modelo) desde el inicio del recorrido, y el tramo en que cae."""
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        largo = math.dist((x1, y1), (x2, y2))
        if t <= largo:
            return (x1 + (x2 - x1) * t / largo, y1 + (y2 - y1) * t / largo), ((x1, y1), (x2, y2))
        t -= largo
    return pts[-1], (pts[-2], pts[-1])


def dibujar(ax, ed: Edificio, campo: Campo | None = None, bloqueados=frozenset(), ocupadas=frozenset(),
            titulo: str = "", detalle: bool = True):
    maq = ed.datos["maqueta"]
    ax.set_aspect("equal")
    ax.set_xlim(0, maq["ancho_m"])
    ax.set_ylim(0, maq["alto_m"])
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), maq["ancho_m"], maq["alto_m"], fc="none", ec="#d5d9e2", lw=1, zorder=0))
    if "edificio" in maq:
        ax.add_patch(Polygon(maq["edificio"], closed=True, fc="#f1f7f3", ec="none", zorder=0.5))
        ax.add_patch(Polygon(maq["edificio"], closed=True, fc="none", ec=TINTA, lw=2.2, zorder=3.5))
    datos_nodo = {d["id"]: d for d in ed.datos["nodos"]}
    for a in ed.aristas:
        if a["tipo"] == "puerta":
            (x1, y1), (x2, y2) = ed.pos[a["u"]], ed.pos[a["v"]]
            usada = campo is not None and a["id"] in campo.sentido
            ax.plot([x1, x2], [y1, y2], ls="--", lw=1.2, color=VERDE if usada else "#8791a5", zorder=3)
            continue
        n = a["longitud_m"]
        color, ancho = GRIS, 5
        if a["id"] in bloqueados:
            color = ROJO
        elif campo is not None and a["id"] in campo.sentido:
            color = VERDE
        elif campo is not None and campo.dist[a["u"]] == 0xFFFFFFFF and campo.dist[a["v"]] == 0xFFFFFFFF:
            color = AMBAR
        pts = puntos(ed, a)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], lw=ancho, color=color, alpha=0.35,
                solid_capstyle="round", solid_joinstyle="round", zorder=1)
        leds = [a_lo_largo(pts, k + 0.5)[0] for k in range(n)]
        ax.scatter([p[0] for p in leds], [p[1] for p in leds], s=9, color=color, zorder=2)
        if campo is not None and a["id"] in campo.sentido:
            ruta = puntos(ed, a, desde=campo.sentido[a["id"]][0])
            (xm, ym), ((xa, ya), (xb, yb)) = a_lo_largo(ruta, n / 2)
            largo = math.dist((xa, ya), (xb, yb))
            dx, dy = (xb - xa) / largo, (yb - ya) / largo
            ax.annotate("", xy=(xm + dx, ym + dy), xytext=(xm - dx, ym - dy),
                        arrowprops=dict(arrowstyle="-|>", color=VERDE, lw=2.2, mutation_scale=16), zorder=5)
        if detalle:
            (xm, ym), ((xa, ya), (xb, yb)) = a_lo_largo(pts, n / 2)
            # Rótulo encima de los tramos horizontales y hacia el borde más cercano en los verticales.
            ox, oy = (0, 1.1) if abs(yb - ya) < 0.1 else ((-2.0 if xm < maq["ancho_m"] / 2 else 2.0), 0)
            texto = f"{a['id']} · {n}" + (f" · {a['pulsador']}" if a.get("pulsador") else "")
            ax.text(xm + ox, ym + oy, texto, ha="center", va="center", fontsize=7.5, zorder=6,
                    color="#0f5a45" if color != ROJO else ROJO, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.8))
    for n in ed.nodos:
        x, y = ed.pos[n]
        t = ed.tipo[n]
        if t == "interseccion":
            ax.scatter([x], [y], s=70, color=TINTA, edgecolor="white", linewidth=1.2, zorder=4)
            ax.text(x - 0.8, y + 0.7, n, ha="right", fontsize=7.5, color=TINTA, fontweight="bold", zorder=6,
                    bbox=dict(boxstyle="round,pad=0.08", fc="white", ec="none", alpha=0.8))
        elif t == "salida":
            ax.add_patch(FancyBboxPatch((x - 1.5, y - 0.9), 3, 1.8, boxstyle="round,pad=0.1,rounding_size=0.3",
                                        fc="#1f7a4d", ec="none", zorder=4))
            ax.text(x, y, n, ha="center", va="center", fontsize=8.5, color="white", fontweight="bold", zorder=5)
        else:
            ocupada = n in ocupadas
            aislada = campo is not None and not campo.rutas[n]
            x0, y0, x1, y1 = datos_nodo[n]["sala"]
            ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, zorder=2.5, lw=1.2,
                                       fc="#fff1d6" if aislada else "#f3e8ff" if ocupada else "white",
                                       ec=AMBAR if aislada else MORADO if ocupada else "#9aa3b2"))
            ax.scatter([x], [y], s=10, color="#8791a5", zorder=4)
            pir = next((s["id"] for s in ed.datos["sensores"] if s["zona"] == n), None)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            ax.text(cx, cy + 0.6, n + (f" {pir}" if pir and detalle else ""), ha="center", va="center", fontsize=7.5,
                    fontweight="bold", color=MORADO if pir else TINTA, zorder=5,
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))
            sub = datos_nodo[n]["nombre"]
            if campo is not None:
                c = campo.costo_m(n)
                sub = "aislada" if c is None else f"{campo.salida(n)} · {c:g} m"
            ax.text(cx, cy - 0.6, sub, ha="center", va="center", fontsize=6.3, color="#3b4458", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))
    if titulo:
        ax.set_title(titulo, fontsize=10, fontweight="bold", color=TINTA, loc="left")


def plano_base(ed: Edificio, destino):
    maq = ed.datos["maqueta"]
    ancho, alto = maq["ancho_m"], maq["alto_m"]
    fig, ax = plt.subplots(figsize=(9.6, 11.2), dpi=160)
    dibujar(ax, ed)
    ax.set_xlim(-0.5, ancho + 0.5)
    ax.set_ylim(-7.5, alto + 0.5)
    base = f"{maq['base_cm'][0]} × {maq['base_cm'][1]} cm"
    fig.suptitle("Plano de la maqueta", x=0.05, y=0.985, ha="left", fontsize=20, fontweight="bold", color=TINTA)
    fig.text(0.05, 0.952, va="top", s="Grupo 2 · Edificio inteligente con rutas dinámicas de evacuación · una planta · "
             f"base de {base}\n1 LED = 1 m del modelo = {maq['cm_por_m']:.3f}".replace(".", ",") + " cm (tira de 60 LED/m). "
             "Medidas de replanteo: docs/Plano_montaje_60x60.png", fontsize=9, color="#3b4458", linespacing=1.4)
    controles = [("B0", "Alarma")] + [(a["pulsador"], a["id"]) for a in sorted(
        (a for a in ed.aristas if a.get("pulsador")), key=lambda a: a["pulsador"])] + [("B7", "Reinicio")]
    controles.sort(key=lambda c: int(c[0][1:]))
    ax.text(0, -2.6, "PANEL DE CONTROL", fontsize=8, fontweight="bold", color="#4a5468")
    for i, (b, f) in enumerate(controles):
        ax.text((i % 5) * 7.3, -4.6 - (i // 5) * 2.2, f"{b} · {f}", fontsize=8, fontweight="bold", color=TINTA,
                bbox=dict(boxstyle="round,pad=0.35", fc="#e8ecf3", ec="none"))
    x0, y0 = ancho - 11, alto - 1.6
    ax.plot([x0, x0 + 10], [y0, y0], color=TINTA, lw=1.4)
    for x, t in ((x0, "0"), (x0 + 5, "5"), (x0 + 10, "10 m (16,7 cm)")):
        ax.plot([x, x], [y0 - 0.4, y0 + 0.4], color=TINTA, lw=1.4)
        ax.text(x, y0 - 1.4, t, ha="center" if x < x0 + 10 else "right", fontsize=7.5, color="#3b4458")
    fig.text(0.05, 0.02, "Pasillos e1–e8: tramo · número de LED · pulsador que lo bloquea. Total: 82 LED. "
             "Líneas discontinuas: puertas sin LED (3 m; Auditorio 4 m).", fontsize=8.5, color="#3b4458")
    fig.subplots_adjust(left=0.03, right=0.97, top=0.92, bottom=0.05)
    fig.savefig(destino, facecolor="white")
    plt.close(fig)
