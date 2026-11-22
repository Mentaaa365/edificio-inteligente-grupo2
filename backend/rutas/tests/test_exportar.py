"""Prueba del comando exportar_historico.
Referencia: https://docs.djangoproject.com/en/5.2/topics/testing/tools/#management-commands"""
import csv
import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from .test_api import linea_esp32


class ExportarHistorico(TestCase):
    def test_exporta_una_fila_por_evento(self):
        for datos in (linea_esp32(evento="LISTO"), linea_esp32(["e2", "e3", "e4", "e5"], evento="B6")):
            r = self.client.post("/api/eventos/", json.dumps(datos), content_type="application/json")
            self.assertEqual(r.status_code, 201)

        with tempfile.TemporaryDirectory() as carpeta:
            salida = Path(carpeta) / "sub" / "experimentos.csv"
            call_command("exportar_historico", "--salida", str(salida), stdout=StringIO())
            with salida.open(encoding="utf-8-sig", newline="") as archivo:
                filas = list(csv.DictReader(archivo))

        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[0]["evento"], "LISTO")
        self.assertEqual(filas[1]["n_bloqueos"], "4")
        self.assertEqual(filas[1]["estado"], "RUTA_PARCIAL")
        self.assertEqual(filas[1]["coincide"], "1")
        self.assertEqual(filas[1]["ruta_Z6"], "aislada")
        self.assertEqual(filas[1]["costo_Z6"], "")
