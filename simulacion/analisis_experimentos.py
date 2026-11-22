"""Métricas de desempeño del prototipo físico a partir del histórico exportado.

Lee datos/experimentos.csv (generado con `python manage.py exportar_historico`)
y calcula, para el tiempo de cálculo de rutas medido EN EL ESP32 (campo calculo_us):
    n, media, desviación estándar muestral, mínimo, percentil 95 y máximo,
    en total y agrupado por número de pasillos bloqueados.
También informa el porcentaje de eventos en que el servidor obtuvo la misma ruta.

Salidas:
    simulacion/resultados/metricas_esp32.csv     tabla para el informe
    simulacion/resultados/fig5_calculo_esp32.png diagrama de caja

Uso (desde la raíz del repositorio):
    python simulacion/analisis_experimentos.py
    python simulacion/analisis_experimentos.py --entrada datos/experimentos.csv --origen esp32
    python simulacion/analisis_experimentos.py --entrada docs/evidencias/prueba_pulsadores.txt
        (un .txt se lee como log del Monitor serie: solo las líneas JSON completas)

Referencias:
    numpy.std (ddof=1, desviación muestral): https://numpy.org/doc/stable/reference/generated/numpy.std.html
    numpy.percentile:                       https://numpy.org/doc/stable/reference/generated/numpy.percentile.html
    matplotlib boxplot:                     https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.boxplot.html
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
RESULTADOS = Path(__file__).resolve().parent / "resultados"


def leer_log_serie(ruta: Path) -> list[dict]:
    """Lee un log del Monitor serie (o de puente_serial) y toma solo las líneas JSON completas del firmware."""
    filas = []
    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        if "{" not in linea or '"evento"' not in linea:
            continue
        try:
            d = json.loads(linea[linea.index("{"):])
        except json.JSONDecodeError:   # línea cortada al copiar el log
            continue
        filas.append({"origen": "esp32", "evento": d["evento"], "n_bloqueos": len(d["bloqueos"]),
                      "calculo_us_esp32": d["calculo_us"], "coincide": ""})
    return filas


def leer(ruta: Path, origen: str | None, incluir_listo: bool) -> list[dict]:
    if ruta.suffix.lower() == ".txt":
        filas = leer_log_serie(ruta)
    else:
        with ruta.open(newline="", encoding="utf-8-sig") as archivo:
            filas = list(csv.DictReader(archivo))
    if origen:
        filas = [f for f in filas if f["origen"] == origen]
    if not incluir_listo:
        # LISTO es el primer cálculo tras el arranque: no lo provoca ningún pulsador ni sensor.
        filas = [f for f in filas if f["evento"] != "LISTO"]
    return filas


def resumen(valores: list[float]) -> dict:
    v = np.asarray(valores, dtype=float)
    return {
        "n": len(v),
        "media_us": round(float(v.mean()), 1),
        "desv_us": round(float(v.std(ddof=1)), 1) if len(v) > 1 else 0.0,
        "min_us": int(v.min()),
        "p95_us": round(float(np.percentile(v, 95)), 1),
        "max_us": int(v.max()),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--entrada", default=str(RAIZ / "datos" / "experimentos.csv"))
    p.add_argument("--origen", default="esp32", help="esp32 (por defecto), simulador o '' para todos")
    p.add_argument("--incluir-listo", action="store_true", help="contar también el evento LISTO")
    args = p.parse_args()

    filas = leer(Path(args.entrada), args.origen or None, args.incluir_listo)
    if not filas:
        raise SystemExit("No hay eventos para analizar: revise el archivo y el filtro --origen.")

    grupos: dict[int, list[float]] = {}
    for f in filas:
        grupos.setdefault(int(f["n_bloqueos"]), []).append(float(f["calculo_us_esp32"]))

    tabla = [{"bloqueos": "todos", **resumen([float(f["calculo_us_esp32"]) for f in filas])}]
    tabla += [{"bloqueos": k, **resumen(grupos[k])} for k in sorted(grupos)]

    comparados = [f for f in filas if f["coincide"] in ("0", "1")]
    coinciden = sum(f["coincide"] == "1" for f in comparados)

    RESULTADOS.mkdir(exist_ok=True)
    salida_csv = RESULTADOS / "metricas_esp32.csv"
    with salida_csv.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(tabla[0]))
        escritor.writeheader()
        escritor.writerows(tabla)

    print(f"Eventos analizados: {len(filas)} (origen: {args.origen or 'todos'})")
    print(f"{'bloqueos':>9} {'n':>4} {'media':>8} {'desv':>7} {'mín':>6} {'P95':>8} {'máx':>6}   (µs)")
    for t in tabla:
        print(f"{t['bloqueos']!s:>9} {t['n']:>4} {t['media_us']:>8} {t['desv_us']:>7} "
              f"{t['min_us']:>6} {t['p95_us']:>8} {t['max_us']:>6}")
    if comparados:
        print(f"Coincidencia ESP32 = servidor: {coinciden}/{len(comparados)} "
              f"({100 * coinciden / len(comparados):.1f} %)")
    print(f"Tabla guardada en {salida_csv}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    claves = sorted(grupos)
    fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
    ax.boxplot([grupos[k] for k in claves], tick_labels=[str(k) for k in claves])
    ax.set_xlabel("Pasillos bloqueados")
    ax.set_ylabel("Tiempo de cálculo en el ESP32 (µs)")
    ax.set_title("Tiempo de cálculo de rutas en el prototipo físico")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    salida_png = RESULTADOS / "fig5_calculo_esp32.png"
    fig.savefig(salida_png)
    print(f"Gráfico guardado en {salida_png}")


if __name__ == "__main__":
    main()
