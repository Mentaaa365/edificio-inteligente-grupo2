"""Dibuja la Figura 1 del informe (arquitectura de la solución) en docs/Arquitectura.png.

Uso, desde la raíz del repositorio:
    python docs/generar_arquitectura.py

Los componentes con borde discontinuo están previstos en el diseño pero todavía no
instalados en la maqueta (tira WS2812B, pulsadores B8 y B9, zumbador).
Referencia: https://matplotlib.org/stable/api/_as_gen/matplotlib.patches.FancyBboxPatch.html
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

SALIDA = Path(__file__).resolve().parent / "Arquitectura.png"

TINTA = "#1f2933"
GRIS = "#6b7280"
CAPAS = {  # color de fondo de cada capa
    "fisica": "#eef4fb",
    "esp32": "#eef8f1",
    "servidor": "#fdf6ea",
    "web": "#f4f0fb",
}


def caja(ax, x, y, w, h, titulo, lineas=(), fondo="white", pendiente=False, borde=TINTA, tam=10):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=fondo, ec=GRIS if pendiente else borde, lw=1.2,
                                ls=(0, (4, 3)) if pendiente else "-"))
    color = GRIS if pendiente else TINTA
    ax.text(x + w / 2, y + h - 0.22, titulo, ha="center", va="top", fontsize=tam, weight="bold", color=color)
    for i, linea in enumerate(lineas):
        ax.text(x + w / 2, y + h - 0.62 - i * 0.34, linea, ha="center", va="top", fontsize=tam - 1.5, color=color)


def flecha(ax, a, b, texto="", dy=0.18, doble=False):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="<|-|>" if doble else "-|>", mutation_scale=14,
                                 lw=1.3, color=TINTA, shrinkA=2, shrinkB=2))
    if texto:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + dy, texto, ha="center", va="bottom", fontsize=8.5, color=TINTA)


fig, ax = plt.subplots(figsize=(14, 7.2), dpi=200)
ax.set_xlim(0, 28)
ax.set_ylim(0, 14.4)
ax.axis("off")

# Fondos de las cuatro capas
capas = [
    (0.2, "Capa física", "fisica", 6.2),
    (6.8, "Control (ESP32)", "esp32", 6.4),
    (13.6, "Servidor (PC)", "servidor", 7.6),
    (21.6, "Aplicación web", "web", 6.2),
]
for x, nombre, clave, ancho in capas:
    ax.add_patch(FancyBboxPatch((x, 0.5), ancho, 13.3, boxstyle="round,pad=0.02,rounding_size=0.25",
                                fc=CAPAS[clave], ec="none"))
    ax.text(x + ancho / 2, 13.45, nombre, ha="center", va="center", fontsize=12.5, weight="bold", color=TINTA)

# Capa física: entradas arriba, salidas abajo
caja(ax, 0.6, 10.3, 5.4, 2.5, "Pulsadores", ["B0 alarma (GPIO 12) · B7 reinicio", "B1–B6: bloqueo de e1–e6", "INPUT_PULLUP, antirrebote 40 ms"])
caja(ax, 0.6, 8.3, 5.4, 1.4, "Pulsadores B8 y B9", ["bloqueo de e7 y e8"], pendiente=True)
caja(ax, 0.6, 5.4, 5.4, 2.5, "Sensores PIR HC-SR501", ["PIR1 → Auditorio Z7 (GPIO 34)", "PIR2 → Oficina Z1 (GPIO 35)", "salida digital de 3,3 V"])
caja(ax, 0.6, 2.5, 5.4, 2.2, "Tira WS2812B (82 LED)", ["GPIO 16 → buffer 74xx125 → DIN", "verde ruta · rojo bloqueo"], pendiente=True)
caja(ax, 0.6, 0.8, 5.4, 1.4, "Zumbador TMB12A05", ["GPIO 23 → 2N2222A"], pendiente=True)

# ESP32 (una sola caja con los pasos del ciclo principal)
caja(ax, 7.2, 0.8, 5.6, 12.0, "ESP32 WROOM-32", [], fondo="white", tam=11)
pasos = ["1. Lee pulsadores y PIR", "2. Actualiza los pesos w(e)", "    w = d·(1+α·o)·(1+β·r)",
         "3. Dijkstra con 3 fuentes", "    (S1, S2, S3), O(V²)", "4. Máquina de estados",
         "    NORMAL · RUTA_ACTIVA", "    RUTA_PARCIAL · SIN_RUTA", "5. Pinta la tira y el zumbador",
         "6. Imprime una línea JSON", "    por evento (115 200 bd)", "", "grafo.h: generado desde",
         "modelo/grafo.json (16 nodos,", "16 aristas)"]
for i, p in enumerate(pasos):
    ax.text(7.55, 12.0 - i * 0.72, p, ha="left", va="top", fontsize=9.3,
            color=GRIS if i >= 12 else TINTA, style="italic" if i >= 12 else "normal")

# Servidor
caja(ax, 14.0, 10.9, 6.8, 1.9, "puente_serial", ["lee el puerto COM por USB", "reenvía cada JSON por HTTP"], fondo="white")
caja(ax, 14.0, 6.0, 6.8, 3.9, "Django 5.2 + Channels", ["POST /api/eventos/ (con token)", "motor.py → simulacion/modelo.py", "recalcula y compara con el ESP32", "«coincide» o discrepancia", "avisa al panel por WebSocket"], fondo="white")
caja(ax, 14.0, 3.3, 6.8, 1.7, "SQLite", ["Evento · RutaCalculada · Medicion"], fondo="white")
caja(ax, 14.0, 0.8, 6.8, 1.6, "exportar_historico", ["datos/experimentos.csv → métricas"], fondo="white")

# Web
caja(ax, 22.0, 6.0, 5.4, 6.8, "Panel (navegador)", ["Plano SVG desde grafo.json:", "rutas, bloqueos, zonas", "aisladas y ocupadas", "Alertas y discrepancias", "Gráficas (Chart.js)", "Histórico filtrable", "Simulador de escenarios"], fondo="white")
caja(ax, 22.0, 0.8, 5.4, 4.2, "Simulación previa", ["Python 3.13 + NetworkX:", "8 escenarios y", "256 combinaciones", "Wokwi: mismo firmware", "y mismo circuito"], fondo="white")

# Flechas
flecha(ax, (6.0, 11.4), (7.2, 11.4))
flecha(ax, (6.0, 6.5), (7.2, 6.5))
flecha(ax, (7.2, 3.6), (6.0, 3.6))
flecha(ax, (7.2, 1.5), (6.0, 1.5))
flecha(ax, (12.8, 11.85), (14.0, 11.85), "USB", dy=0.1)
flecha(ax, (17.4, 10.9), (17.4, 9.9))
ax.text(17.6, 10.4, "HTTP", fontsize=8.5, va="center", color=TINTA)
flecha(ax, (17.4, 6.0), (17.4, 5.0), doble=True)
flecha(ax, (17.4, 3.3), (17.4, 2.4))
flecha(ax, (20.8, 8.9), (22.0, 8.9))
ax.text(21.4, 9.15, "Web-\nSocket", ha="center", fontsize=7.5, color=TINTA)
flecha(ax, (22.0, 7.0), (20.8, 7.0))
ax.text(21.4, 6.55, "HTTP", ha="center", fontsize=8, color=TINTA)

# Leyenda
ax.add_patch(FancyBboxPatch((0.6, 0.05), 0.9, 0.32, boxstyle="round,pad=0.01", fc="white", ec=GRIS, ls=(0, (4, 3))))
ax.text(1.7, 0.21, "Previsto en el diseño, pendiente de instalar en la maqueta", va="center", fontsize=8.5, color=GRIS)

fig.savefig(SALIDA, bbox_inches="tight", facecolor="white")
print(f"Figura guardada en {SALIDA}")
