"""Lógica del servidor: validar lo que llega, calcular con el motor, guardar y avisar.

Las vistas (views.py) solo leen la petición HTTP y llaman a estas funciones.
Así la misma lógica se usa desde la API, el comando simular_esp32 y las pruebas.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from . import difusion, motor
from .models import Escenario, Evento, Medicion, RutaCalculada

# Campos obligatorios del JSON del firmware y su tipo esperado.
CAMPOS_EVENTO = {
    "ms": int,
    "evento": str,
    "estado": str,
    "bloqueos": list,
    "ocupadas": list,
    "calculo_us": int,
    "explorados": int,
    "aisladas": int,
    "rutas": dict,
}


def validar_evento(datos) -> list[str]:
    """Devuelve la lista de errores del JSON recibido (vacía si es válido)."""
    if not isinstance(datos, dict):
        return ["El cuerpo debe ser un objeto JSON."]
    errores = []
    for campo, tipo in CAMPOS_EVENTO.items():
        if campo not in datos:
            errores.append(f"Falta el campo '{campo}'.")
        # bool es subclase de int en Python: se rechaza aparte para no aceptar true como número.
        elif not isinstance(datos[campo], tipo) or (tipo is int and isinstance(datos[campo], bool)):
            errores.append(f"El campo '{campo}' debe ser de tipo {tipo.__name__}.")
    if errores:
        return errores
    if datos["estado"] not in motor.ESTADOS_ESP32:
        errores.append(f"Estado desconocido '{datos['estado']}'. Válidos: {list(motor.ESTADOS_ESP32)}.")
    if not 0 < len(datos["evento"]) <= 16:
        errores.append("El campo 'evento' debe tener entre 1 y 16 caracteres.")
    try:
        motor.validar_entradas(datos["bloqueos"], datos["ocupadas"])
    except ValueError as e:
        errores.append(str(e))
    return errores


def _guardar_ruta(resultado: dict, evento=None, escenario=None, diferencias=None) -> RutaCalculada:
    """Guarda una RutaCalculada y sus ocho Medicion (una por zona)."""
    ruta = RutaCalculada.objects.create(
        evento=evento,
        escenario=escenario,
        bloqueos=resultado["bloqueos"],
        ocupadas=resultado["ocupadas"],
        alfa_pct=resultado["alfa_pct"],
        beta_pct=resultado["beta_pct"],
        estado=resultado["estado"],
        explorados=resultado["explorados"],
        aisladas=resultado["aisladas"],
        resultado=resultado,
        calculo_us=resultado["calculo_us"],
        coincide_esp32=None if diferencias is None else not diferencias,
        diferencias=diferencias or [],
    )
    Medicion.objects.bulk_create(
        Medicion(ruta=ruta, zona=zona, costo_m=d["costo_m"], longitud_m=d["longitud_m"],
                 tiempo_s=d["tiempo_s"], salida=d["salida"])
        for zona, d in resultado["detalle"].items()
    )
    return ruta


def registrar_evento(datos: dict, origen: str = "esp32") -> Evento:
    """Guarda el evento del ESP32, recalcula con modelo.py y anota si coinciden.

    Se usan los α y β de grafo.json porque son los que tiene compilados el firmware.
    """
    resultado = motor.calcular(datos["bloqueos"], datos["ocupadas"])
    diferencias = motor.comparar(datos, resultado)
    with transaction.atomic():           # o se guarda todo o no se guarda nada
        evento = Evento.objects.create(
            ms=datos["ms"], evento=datos["evento"], estado=datos["estado"],
            bloqueos=datos["bloqueos"], ocupadas=datos["ocupadas"],
            calculo_us=datos["calculo_us"], explorados=datos["explorados"],
            aisladas=datos["aisladas"], rutas=datos["rutas"],
            json_original=datos, origen=origen,
        )
        _guardar_ruta(resultado, evento=evento, diferencias=diferencias)
    # Se avisa al navegador cuando los datos ya están guardados.
    transaction.on_commit(lambda: difusion.enviar("evento", serializar_evento(evento)))
    return evento


def ejecutar_escenario(escenario: Escenario) -> RutaCalculada:
    """Deja el escenario pendiente para el ESP32 y calcula ya su ruta en el servidor."""
    resultado = motor.calcular(escenario.bloqueos, escenario.ocupadas, escenario.alfa_pct, escenario.beta_pct)
    with transaction.atomic():
        escenario.estado_envio = Escenario.EstadoEnvio.PENDIENTE
        escenario.enviado_en = None
        escenario.save(update_fields=["estado_envio", "enviado_en"])
        ruta = _guardar_ruta(resultado, escenario=escenario)
    transaction.on_commit(lambda: difusion.enviar("escenario", serializar_ruta(ruta)))
    return ruta


def tomar_comandos() -> list[dict]:
    """Escenarios pendientes para el ESP32. Al entregarlos se marcan como enviados."""
    with transaction.atomic():
        pendientes = list(Escenario.objects.select_for_update()
                          .filter(estado_envio=Escenario.EstadoEnvio.PENDIENTE).order_by("id"))
        ahora = timezone.now()
        for esc in pendientes:
            esc.estado_envio = Escenario.EstadoEnvio.ENVIADO
            esc.enviado_en = ahora
            esc.save(update_fields=["estado_envio", "enviado_en"])
    return [serializar_escenario(e) for e in pendientes]


# ----------------------------------------------------------------- de objeto a JSON
def serializar_escenario(esc: Escenario) -> dict:
    return {
        "id": esc.id, "nombre": esc.nombre, "descripcion": esc.descripcion,
        "bloqueos": esc.bloqueos, "ocupadas": esc.ocupadas, "alarma": esc.alarma,
        "alfa_pct": esc.alfa_pct, "beta_pct": esc.beta_pct,
        "estado_envio": esc.estado_envio,
        "enviado_en": esc.enviado_en.isoformat() if esc.enviado_en else None,
    }


def serializar_ruta(ruta: RutaCalculada) -> dict:
    return {
        "id": ruta.id,
        "creada": ruta.creada.isoformat(),
        "escenario": ruta.escenario.nombre if ruta.escenario else None,
        "coincide_esp32": ruta.coincide_esp32,
        "diferencias": ruta.diferencias,
        **ruta.resultado,    # estado, rutas, detalle, sentido, aristas_aisladas, etc.
    }


def serializar_evento(ev: Evento) -> dict:
    return {
        "id": ev.id,
        "recibido": ev.recibido.isoformat(),
        "origen": ev.origen,
        "esp32": {
            "ms": ev.ms, "evento": ev.evento, "estado": ev.estado,
            "bloqueos": ev.bloqueos, "ocupadas": ev.ocupadas,
            "calculo_us": ev.calculo_us, "explorados": ev.explorados,
            "aisladas": ev.aisladas, "rutas": ev.rutas,
        },
        "servidor": serializar_ruta(ev.ruta) if hasattr(ev, "ruta") else None,
    }
