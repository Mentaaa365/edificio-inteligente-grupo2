"""Dibujo del plano del edificio con Matplotlib (plano base y resultado de un escenario)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from modelo import Campo, Edificio

VERDE, ROJO, AMBAR, GRIS, TINTA = "#12805c", "#c8372d", "#c98500", "#b9c0cc", "#1b2438"
MORADO = "#6b2fa0"


def dibujar(ax, ed: Edificio, campo: Campo | None = None, bloqueados=frozenset(), ocupadas=frozenset(),
            titulo: str = "", detalle: bool = True):
    maq = ed.datos["maqueta"]
    ax.set_aspect("equal")
    ax.set_xlim(0, maq["ancho_m"])
    ax.set_ylim(0, maq["alto_m"])
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), maq["ancho_m"], maq["alto_m"], fc="none", ec="#d5d9e2", lw=1, zorder=0))
    for a in ed.aristas:
        (x1, y1), (x2, y2) = ed.pos[a["u"]], ed.pos[a["v"]]
        if a["tipo"] == "puerta":
            usada = campo is not None and a["id"] in campo.sentido
            ax.plot([x1, x2], [y1, y2], ls="--", lw=1.2, color=VERDE if usada else "#8791a5", zorder=1)
            continue
        n = a["longitud_m"]
        color, ancho = GRIS, 5
        if a["id"] in bloqueados:
            color = ROJO
        elif campo is not None and a["id"] in campo.sentido:
            color = VERDE
        elif campo is not None and campo.dist[a["u"]] == 0xFFFFFFFF and campo.dist[a["v"]] == 0xFFFFFFFF:
            color = AMBAR
        ax.plot([x1, x2], [y1, y2], lw=ancho, color=color, alpha=0.35, solid_capstyle="round", zorder=1)
        xs = [x1 + (x2 - x1) * (k + 0.5) / n for k in range(n)]
        ys = [y1 + (y2 - y1) * (k + 0.5) / n for k in range(n)]
        ax.scatter(xs, ys, s=9, color=color, zorder=2)
        if campo is not None and a["id"] in campo.sentido:
            d, h = campo.sentido[a["id"]]
            (xa, ya), (xb, yb) = ed.pos[d], ed.pos[h]
            xm, ym = (xa + xb) / 2, (ya + yb) / 2
            dx, dy = (xb - xa) / n, (yb - ya) / n
            ax.annotate("", xy=(xm + dx, ym + dy), xytext=(xm - dx, ym - dy),
                        arrowprops=dict(arrowstyle="-|>", color=VERDE, lw=2.2, mutation_scale=16), zorder=5)
        if detalle:
            ox, oy = (0, 1.1) if abs(y2 - y1) < 0.1 else (1.9, 0)
            if a["id"] == "e6":
                ox = -2.6
            if a["id"] == "e8":
                ox, oy = 1.6, 1.0
            texto = f"{a['id']} · {n}" + (f" · {a['pulsador']}" if a.get("pulsador") else "")
            ax.text((x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy, texto, ha="center", va="center",
                    fontsize=7.5, color="#0f5a45" if color != ROJO else ROJO, fontweight="bold")
    for n in ed.nodos:
        x, y = ed.pos[n]
        t = ed.tipo[n]
        if t == "interseccion":
            ax.scatter([x], [y], s=70, color=TINTA, edgecolor="white", linewidth=1.2, zorder=4)
            dx, dy = (1.5, 0.5) if n == "C5" else (0, 1.0)
            ax.text(x + dx, y + dy, n, ha="center", fontsize=7.5, color=TINTA, fontweight="bold")
        elif t == "salida":
            ax.add_patch(FancyBboxPatch((x - 1.5, y - 0.9), 3, 1.8, boxstyle="round,pad=0.1,rounding_size=0.3",
                                        fc="#1f7a4d", ec="none", zorder=4))
            ax.text(x, y, n, ha="center", va="center", fontsize=8.5, color="white", fontweight="bold", zorder=5)
        else:
            ocupada = n in ocupadas
            aislada = campo is not None and not campo.rutas[n]
            # La caja se dibuja hacia el lado contrario a su intersección, para no tapar los pasillos.
            cx, cy = ed.pos[next(a["v"] for a in ed.aristas if a["tipo"] == "puerta" and a["u"] == n)]
            if abs(x - cx) > abs(y - cy):
                bx, by = (x + 0.5 if x > cx else x - 3.7), y - 1.3
            else:
                bx, by = x - 1.6, (y if y > cy else y - 2.6)
            ax.add_patch(FancyBboxPatch((bx, by), 3.2, 2.6, boxstyle="round,pad=0.05,rounding_size=0.25",
                                        fc="#fff1d6" if aislada else "#f3e8ff" if ocupada else "white",
                                        ec=AMBAR if aislada else MORADO if ocupada else "#c5ccd8", lw=1.2, zorder=3))
            pir = next((s["id"] for s in ed.datos["sensores"] if s["zona"] == n), None)
            ax.text(bx + 1.6, by + 1.75, n + (f" {pir}" if pir and detalle else ""), ha="center", va="center", fontsize=7.5,
                    fontweight="bold", color=MORADO if pir else TINTA, zorder=5)
            sub = next(d["nombre"] for d in ed.datos["nodos"] if d["id"] == n)
            if campo is not None:
                c = campo.costo_m(n)
                sub = "aislada" if c is None else f"{campo.salida(n)} · {c:g} m"
            ax.text(bx + 1.6, by + 0.75, sub, ha="center", va="center", fontsize=6.3, color="#3b4458", zorder=5)
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
