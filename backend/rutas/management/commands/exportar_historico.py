"""Exporta el histórico de eventos a un CSV para analizarlo fuera del servidor.

Cada fila es un evento recibido (del ESP32 por el puente serie, o del simulador)
con lo que calculó el ESP32, lo que calculó el servidor y si coinciden.
El archivo lo lee simulacion/analisis_experimentos.py para obtener la media,
la desviación estándar, el percentil 95 y el diagrama de caja del informe.

Uso (desde la carpeta backend, con el entorno activado):
    python manage.py exportar_historico
    python manage.py exportar_historico --origen esp32 --salida ..\\datos\\experimentos.csv

Referencias:
    https://docs.djangoproject.com/en/5.2/howto/custom-management-commands/
    https://docs.python.org/3.13/library/csv.html
"""
import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from rutas.models import Evento

ZONAS = [f"Z{i}" for i in range(1, 9)]

COLUMNAS = (
    ["id", "recibido", "origen", "ms", "evento", "estado", "n_bloqueos", "bloqueos", "ocupadas",
     "calculo_us_esp32", "explorados", "aisladas", "calculo_us_servidor", "coincide"]
    + [f"costo_{z}" for z in ZONAS]
    + [f"ruta_{z}" for z in ZONAS]
)


def fila_de(evento: Evento) -> dict:
    """Convierte un evento (y su ruta calculada en el servidor, si existe) en una fila del CSV."""
    ruta = getattr(evento, "ruta", None)
    fila = {
        "id": evento.pk,
        "recibido": evento.recibido.isoformat(timespec="milliseconds"),
        "origen": evento.origen,
        "ms": evento.ms,
        "evento": evento.evento,
        "estado": evento.estado,
        "n_bloqueos": len(evento.bloqueos),
        "bloqueos": " ".join(evento.bloqueos),
        "ocupadas": " ".join(evento.ocupadas),
        "calculo_us_esp32": evento.calculo_us,
        "explorados": evento.explorados,
        "aisladas": evento.aisladas,
        "calculo_us_servidor": ruta.calculo_us if ruta else "",
        "coincide": "" if ruta is None or ruta.coincide_esp32 is None else int(ruta.coincide_esp32),
    }
    rutas = evento.rutas if isinstance(evento.rutas, dict) else {}
    for z in ZONAS:
        datos = rutas.get(z)  # None = zona aislada
        fila[f"costo_{z}"] = datos.get("costo_m", "") if isinstance(datos, dict) else ""
        fila[f"ruta_{z}"] = datos.get("ruta", "") if isinstance(datos, dict) else "aislada"
    return fila


class Command(BaseCommand):
    help = "Exporta el histórico de eventos a datos/experimentos.csv"

    def add_arguments(self, parser):
        por_defecto = Path(settings.BASE_DIR).parent / "datos" / "experimentos.csv"
        parser.add_argument("--salida", default=str(por_defecto), help=f"archivo CSV (por defecto {por_defecto})")
        parser.add_argument("--origen", choices=["esp32", "simulador"], help="exportar solo un origen")

    def handle(self, *args, **opciones):
        eventos = Evento.objects.select_related("ruta").order_by("recibido", "id")
        if opciones["origen"]:
            eventos = eventos.filter(origen=opciones["origen"])

        salida = Path(opciones["salida"])
        salida.parent.mkdir(parents=True, exist_ok=True)
        # utf-8-sig: Excel en Windows abre el archivo con las tildes bien.
        with salida.open("w", newline="", encoding="utf-8-sig") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
            escritor.writeheader()
            total = 0
            for evento in eventos.iterator():
                escritor.writerow(fila_de(evento))
                total += 1

        self.stdout.write(self.style.SUCCESS(f"{total} eventos exportados a {salida}"))
