"""Migración de datos: crea los escenarios S0–S7 de la Fase 1 (docs/Fase_1.md, sección 3).

Referencia: https://docs.djangoproject.com/en/5.2/topics/migrations/#data-migrations
"""
from django.db import migrations

ESCENARIOS = [
    ("S0", "Sin bloqueos", [], []),
    ("S1", "e6 bloqueado", ["e6"], []),
    ("S2", "e7 bloqueado (salida S2)", ["e7"], []),
    ("S3", "e2 + e4 bloqueados", ["e2", "e4"], []),
    ("S4", "e1 bloqueado (salida S1)", ["e1"], []),
    ("S5", "e2 + e3 + e6 bloqueados", ["e2", "e3", "e6"], []),
    ("S6", "e1 + e5 + e7 bloqueados", ["e1", "e5", "e7"], []),
    ("S7", "Auditorio ocupado (PIR1)", [], ["Z7"]),
]


def crear(apps, schema_editor):
    Escenario = apps.get_model("rutas", "Escenario")
    for nombre, descripcion, bloqueos, ocupadas in ESCENARIOS:
        Escenario.objects.get_or_create(
            nombre=nombre,
            defaults={"descripcion": descripcion, "bloqueos": bloqueos, "ocupadas": ocupadas},
        )


def borrar(apps, schema_editor):
    apps.get_model("rutas", "Escenario").objects.filter(nombre__in=[e[0] for e in ESCENARIOS]).delete()


class Migration(migrations.Migration):
    dependencies = [("rutas", "0001_initial")]
    operations = [migrations.RunPython(crear, borrar)]
