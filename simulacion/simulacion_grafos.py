"""Fase 1 · Simulación de emergencias con grafos.

Ejecutar desde la raíz del repositorio:

    python simulacion/simulacion_grafos.py

Genera en simulacion/resultados/ los CSV y las figuras, y actualiza docs/Plano_Fase_0.png.
"""
from __future__ import annotations

import csv
import itertools
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import modelo as m
import plano

SALIDA = Path(__file__).resolve().parent / "resultados"
SALIDA.mkdir(exist_ok=True)

ESCENARIOS = [
    ("S0", "Sin bloqueos", set(), set()),
    ("S1", "Pasillo norte e6 bloqueado", {"e6"}, set()),
    ("S2", "Salida S2 bloqueada (e7)", {"e7"}, set()),
    ("S3", "Bloqueos múltiples e2 + e4", {"e2", "e4"}, set()),
    ("S4", "Salida S1 bloqueada (e1)", {"e1"}, set()),
    ("S5", "Zona aislada: e2 + e3 + e6", {"e2", "e3", "e6"}, set()),
    ("S6", "Sin ruta: e1 + e5 + e7", {"e1", "e5", "e7"}, set()),
    ("S7", "Congestión: Auditorio ocupado (PIR1)", set(), {"Z7"}),
]


def escribir_csv(nombre: str, cabecera: list[str], filas: list[list]):
    with open(SALIDA / nombre, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cabecera)
        w.writerows(filas)


def r2(y, y_est) -> float:
    y, y_est = np.asarray(y, float), np.asarray(y_est, float)
    return 1 - float(np.sum((y - y_est) ** 2) / np.sum((y - y.mean()) ** 2))


def escenarios(ed: m.Edificio):
    v = ed.parametros["velocidad_m_s"]
    filas, resumen = [], []
    fig, ejes = plt.subplots(4, 2, figsize=(12, 24), dpi=120)
    for (cod, desc, bloq, ocup), ax in zip(ESCENARIOS, ejes.flat):
        campo = m.calcular_campo(ed, bloq, ocup)
        assert campo.dist == m.distancias_nx(ed, campo.peso), f"{cod}: no coincide con NetworkX"
        est = m.estado(campo)
        costos = [campo.costo_m(z) for z in ed.zonas if campo.rutas[z]]
        largos = [m.longitud_real_m(ed, campo, z) for z in ed.zonas if campo.rutas[z]]
        for z in ed.zonas:
            L = m.longitud_real_m(ed, campo, z)
            filas.append([cod, desc, "+".join(sorted(bloq)) or "-", "+".join(sorted(ocup)) or "-", est, z,
                          campo.salida(z) or "-", "" if L is None else L,
                          "" if L is None else campo.costo_m(z), "" if L is None else round(L / v, 2),
                          ">".join(campo.rutas[z]) or "-"])
        resumen.append([cod, desc, est, len(campo.aisladas),
                        round(float(np.mean(largos)), 2) if largos else "",
                        max(largos) if largos else "",
                        round(max(largos) / v, 1) if largos else "",
                        round(float(np.mean(costos)), 2) if costos else ""])
        plano.dibujar(ax, ed, campo, bloq, ocup, titulo=f"{cod} · {desc} · {est}", detalle=False)
    fig.tight_layout()
    fig.savefig(SALIDA / "fig1_escenarios.png", facecolor="white")
    plt.close(fig)
    escribir_csv("escenarios_rutas.csv",
                 ["escenario", "descripcion", "bloqueos", "ocupadas", "estado", "zona", "salida", "longitud_m",
                  "costo_modelo_m", "t_evac_s", "ruta"], filas)
    escribir_csv("escenarios_resumen.csv",
                 ["escenario", "descripcion", "estado", "zonas_aisladas", "longitud_media_m", "longitud_max_m",
                  "t_evac_max_s", "costo_medio_m"], resumen)
    return resumen


def algoritmos(ed: m.Edificio):
    """Dijkstra, A* y BFS desde cada zona, en cada escenario con ruta."""
    filas, acum = [], {"dijkstra": [], "astar": [], "bfs": []}
    peores = 0
    for cod, _, bloq, ocup in ESCENARIOS:
        w = m.pesos(ed, bloq, ocup)
        for z in ed.zonas:
            res = {met: m.buscar(ed, w, z, met) for met in acum}
            if res["dijkstra"]["costo"] is None:
                continue
            assert res["astar"]["costo"] == res["dijkstra"]["costo"], "A* debe ser óptimo"
            peor = res["bfs"]["costo"] > res["dijkstra"]["costo"]
            peores += peor
            for met in acum:
                acum[met].append(res[met]["explorados"])
            filas.append([cod, z, res["dijkstra"]["costo"] / m.ESCALA, res["dijkstra"]["explorados"],
                          res["astar"]["explorados"], res["bfs"]["costo"] / m.ESCALA, res["bfs"]["explorados"],
                          "si" if peor else "no", ">".join(res["dijkstra"]["ruta"]), ">".join(res["bfs"]["ruta"])])
    escribir_csv("algoritmos.csv", ["escenario", "zona", "costo_optimo_m", "explorados_dijkstra", "explorados_astar",
                                    "costo_bfs_m", "explorados_bfs", "bfs_peor", "ruta_dijkstra", "ruta_bfs"], filas)
    medias = {k: float(np.mean(v)) for k, v in acum.items()}
    fig, ax = plt.subplots(figsize=(6.4, 4), dpi=140)
    nombres = ["Dijkstra", "A*", "BFS"]
    vals = [medias["dijkstra"], medias["astar"], medias["bfs"]]
    barras = ax.bar(nombres, vals, color=["#12805c", "#2f6fb5", "#8791a5"], width=0.55)
    ax.bar_label(barras, fmt="%.1f")
    ax.set_ylabel("Nodos expandidos (media)")
    ax.set_title(f"Un origen → salida más cercana ({len(filas)} casos)\nBFS da una ruta más cara en {peores} casos",
                 fontsize=10, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(SALIDA / "fig2_algoritmos.png", facecolor="white")
    plt.close(fig)
    return medias, peores, len(filas)


def sensibilidad_alfa(ed: m.Edificio):
    """Con el Auditorio ocupado, ¿desde qué α cambia de salida cada zona?"""
    alfas = list(range(0, 205, 5))
    filas, cambios = [], {}
    base = m.calcular_campo(ed, set(), {"Z7"}, alfa_pct=0)
    for a in alfas:
        c = m.calcular_campo(ed, set(), {"Z7"}, alfa_pct=a)
        for z in ed.zonas:
            filas.append([a / 100, z, c.salida(z), c.costo_m(z), m.longitud_real_m(ed, c, z)])
            if c.salida(z) != base.salida(z) and z not in cambios:
                cambios[z] = (a / 100, base.salida(z), c.salida(z))
    escribir_csv("sensibilidad_alfa.csv", ["alfa", "zona", "salida", "costo_modelo_m", "longitud_m"], filas)
    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=140)
    for z, col in zip(("Z3", "Z4", "Z7"), ("#12805c", "#2f6fb5", "#6b2fa0")):
        ax.plot([f[0] for f in filas if f[1] == z], [f[3] for f in filas if f[1] == z], label=z, color=col, lw=2)
    for z, (a, s0, s1) in cambios.items():
        ax.axvline(a, color="#c98500", ls=":", lw=1.2)
        ax.text(a + 0.02, ax.get_ylim()[0] + 1, f"{z}: {s0}→{s1}\nα = {a:g}", fontsize=7.5, color="#8a5a00")
    ax.set_xlabel("α (peso de la congestión)")
    ax.set_ylabel("Costo del modelo (m)")
    ax.set_title("Sensibilidad a α con el Auditorio (Z7) ocupado", fontsize=10, loc="left")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(SALIDA / "fig3_sensibilidad_alfa.png", facecolor="white")
    plt.close(fig)
    return cambios


def barrido_bloqueos(ed: m.Edificio):
    """Todas las combinaciones de pasillos bloqueados: 2^8 = 256 escenarios, agrupados por k.
    Al ser pocas, se enumeran completas (resultado exacto, sin muestreo aleatorio)."""
    pas = ed.pasillos
    filas = []
    for k in range(len(pas) + 1):
        combos = list(itertools.combinations(pas, k))
        largos, aisl, sin_ruta = [], [], 0
        for b in combos:
            c = m.calcular_campo(ed, set(b))
            aisl.append(len(c.aisladas))
            sin_ruta += len(c.aisladas) == len(ed.zonas)
            largos += [m.longitud_real_m(ed, c, z) for z in ed.zonas if c.rutas[z]]
        filas.append([k, len(combos), round(float(np.mean(largos)), 3) if largos else "",
                      round(100 * float(np.mean(aisl)) / len(ed.zonas), 2), round(100 * sin_ruta / len(combos), 2)])
    escribir_csv("barrido_bloqueos.csv", ["k_bloqueos", "n_escenarios", "longitud_media_m",
                                          "pct_zonas_aisladas", "pct_sin_ruta"], filas)

    # --- Ajuste de curvas por mínimos cuadrados: % de zonas aisladas en función de k
    k = np.array([f[0] for f in filas], float)
    y = np.array([f[3] for f in filas], float)
    lin = np.polyfit(k, y, 1)
    cua = np.polyfit(k, y, 2)
    # Modelo logístico linealizado: ln(p / (1 - p)) = a + b·k, con los puntos donde 0 < p < 1
    dentro = (y > 0) & (y < 100)
    b_log, a_log = np.polyfit(k[dentro], np.log((y[dentro] / 100) / (1 - y[dentro] / 100)), 1)
    logistica = lambda x: 100 / (1 + np.exp(-(a_log + b_log * x)))
    ajuste = {"lineal": (lin, r2(y, np.polyval(lin, k))),
              "cuadratico": (cua, r2(y, np.polyval(cua, k))),
              "logistico_linealizado": (np.array([b_log, a_log]), r2(y, logistica(k)))}
    # --- Longitud media mientras casi nadie queda aislado (k = 0..3)
    kk, LL = k[:4], np.array([f[2] for f in filas[:4]], float)
    linL = np.polyfit(kk, LL, 1)
    ajuste["longitud_lineal_k0a3"] = (linL, r2(LL, np.polyval(linL, kk)))

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.2), dpi=140)
    ks = np.linspace(0, 8, 100)
    a1.scatter(k, y, color="#1b2438", zorder=3, label="Simulación (256 escenarios)")
    a1.plot(ks, np.polyval(lin, ks), color="#8791a5", ls="--", label=f"Lineal  R² = {ajuste['lineal'][1]:.3f}")
    a1.plot(ks, np.polyval(cua, ks), color="#2f6fb5", ls="-.", label=f"Cuadrático  R² = {ajuste['cuadratico'][1]:.3f}")
    a1.plot(ks, logistica(ks), color="#c8372d",
            label=f"Logístico linealizado  R² = {ajuste['logistico_linealizado'][1]:.3f}")
    a1.set_xlabel("k (pasillos bloqueados)")
    a1.set_ylabel("Zonas aisladas (%)")
    a1.set_title("Zonas sin ruta según el número de bloqueos", fontsize=10, loc="left")
    a1.legend(frameon=False, fontsize=8)
    a2.scatter(k[:-1], [f[2] for f in filas[:-1]], color="#1b2438", zorder=3, label="Simulación")
    a2.plot(kk, np.polyval(linL, kk), color="#12805c",
            label=f"Lineal (k ≤ 3): L = {linL[1]:.2f} + {linL[0]:.2f}·k   R² = {ajuste['longitud_lineal_k0a3'][1]:.3f}")
    a2.set_xlabel("k (pasillos bloqueados)")
    a2.set_ylabel("Longitud media de ruta (m)")
    a2.set_title("Recorrido medio de las zonas que conservan ruta", fontsize=10, loc="left")
    a2.legend(frameon=False, fontsize=8, loc="lower left")
    for a in (a1, a2):
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(SALIDA / "fig4_barrido_ajuste.png", facecolor="white")
    plt.close(fig)
    return filas, ajuste


def tiempo_calculo(ed: m.Edificio, repeticiones: int = 2000) -> float:
    t0 = time.perf_counter()
    for _ in range(repeticiones):
        m.calcular_campo(ed, {"e6"})
    return (time.perf_counter() - t0) / repeticiones * 1e6


def main():
    ed = m.cargar()
    plano.plano_base(ed, m.RAIZ / "docs" / "Plano_Fase_0.png")
    print("== Escenarios ==")
    for f in escenarios(ed):
        print(f)
    medias, peores, casos = algoritmos(ed)
    print("== Algoritmos (nodos expandidos, media) ==", medias, f"| BFS peor en {peores}/{casos}")
    print("== Sensibilidad a alfa (Z7 ocupada) ==", sensibilidad_alfa(ed))
    filas, ajuste = barrido_bloqueos(ed)
    print("== Barrido de bloqueos ==")
    for f in filas:
        print(f)
    for nombre, (coef, r) in ajuste.items():
        print(f"ajuste {nombre}: coef={np.round(coef, 4).tolist()} R2={r:.4f}")
    print(f"== Tiempo medio de cálculo en Python: {tiempo_calculo(ed):.0f} µs ==")


if __name__ == "__main__":
    main()
