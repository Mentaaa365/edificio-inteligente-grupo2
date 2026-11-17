"""API HTTP del servidor. Cada vista lee la petición, llama a servicios.py y responde JSON.

    POST /api/eventos/                   el ESP32 envía una línea JSON (requiere X-Token si API_TOKEN tiene valor)
    GET  /api/comandos/                  el ESP32 pregunta si hay escenarios pendientes (mismo token)
    GET  /api/escenarios/                lista de escenarios (dashboard)
    POST /api/escenarios/<id>/ejecutar/  deja un escenario pendiente y calcula su ruta (dashboard)
    GET  /api/historico/                 eventos guardados, con filtros
    GET  /api/grafo/                     nodos y aristas de grafo.json para dibujar el plano
    POST /api/simular/                   calcula sin guardar, con α y β elegidos (simulador del dashboard)

Referencia: https://docs.djangoproject.com/en/5.2/topics/http/views/
"""
import hmac
import json
from datetime import datetime, time

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from . import motor, servicios
from .models import Escenario, Evento

LIMITE_POR_DEFECTO = 100
LIMITE_MAXIMO = 1000


# ----------------------------------------------------------------- ayudas
def _error(mensaje, estado=400, **extra):
    return JsonResponse({"ok": False, "error": mensaje, **extra}, status=estado)


def _leer_json(request):
    """Devuelve (datos, None) o (None, respuesta_de_error)."""
    try:
        return json.loads(request.body.decode("utf-8") or "{}"), None
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return None, _error(f"JSON inválido: {e}")


def _token_valido(request) -> bool:
    """Si API_TOKEN está vacío no se pide clave. compare_digest evita ataques por tiempo."""
    if not settings.API_TOKEN:
        return True
    return hmac.compare_digest(request.headers.get("X-Token", ""), settings.API_TOKEN)


# ----------------------------------------------------------------- dashboard
@ensure_csrf_cookie        # deja la cookie csrftoken para que el JS pueda hacer POST
def dashboard(request):
    return render(request, "rutas/dashboard.html")


# ----------------------------------------------------------------- API del ESP32
# csrf_exempt: el ESP32 no tiene cookies de sesión; se protege con el token X-Token.
@csrf_exempt
@require_POST
def recibir_evento(request):
    if not _token_valido(request):
        return _error("Token inválido o ausente (cabecera X-Token).", 401)
    datos, error = _leer_json(request)
    if error:
        return error
    errores = servicios.validar_evento(datos)
    if errores:
        return _error("El evento no tiene el formato del firmware.", 400, detalles=errores)
    origen = "simulador" if request.headers.get("X-Origen") == "simulador" else "esp32"
    evento = servicios.registrar_evento(datos, origen=origen)
    return JsonResponse(
        {
            "ok": True,
            "id": evento.id,
            "coincide": evento.ruta.coincide_esp32,
            "diferencias": evento.ruta.diferencias,
            "estado_modelo": evento.ruta.estado,
        },
        status=201,
    )


@require_GET
def comandos(request):
    if not _token_valido(request):
        return _error("Token inválido o ausente (cabecera X-Token).", 401)
    return JsonResponse({"ok": True, "comandos": servicios.tomar_comandos()})


# ----------------------------------------------------------------- API del dashboard
@require_GET
def lista_escenarios(request):
    escenarios = [servicios.serializar_escenario(e) for e in Escenario.objects.all()]
    return JsonResponse({"ok": True, "escenarios": escenarios})


@require_POST      # protegido con CSRF: solo lo llama el dashboard del mismo servidor
def ejecutar_escenario(request, escenario_id):
    escenario = get_object_or_404(Escenario, pk=escenario_id)
    ruta = servicios.ejecutar_escenario(escenario)
    return JsonResponse({
        "ok": True,
        "escenario": servicios.serializar_escenario(escenario),
        "ruta": servicios.serializar_ruta(ruta),
    })


def _a_fecha(texto, fin_del_dia=False):
    """Acepta '2026-11-17' o '2026-11-17T10:30'. Devuelve datetime con zona horaria o None."""
    if not texto:
        return None
    valor = parse_datetime(texto)
    if valor is None:
        dia = parse_date(texto)
        if dia is None:
            raise ValueError(f"Fecha inválida: {texto}")
        valor = datetime.combine(dia, time.max if fin_del_dia else time.min)
    if timezone.is_naive(valor):
        valor = timezone.make_aware(valor)
    return valor


@require_GET
def historico(request):
    """Filtros: desde, hasta, estado, evento, coincide (si/no), origen, despues_de (id), limite."""
    p = request.GET
    eventos = Evento.objects.select_related("ruta", "ruta__escenario")
    try:
        if desde := _a_fecha(p.get("desde")):
            eventos = eventos.filter(recibido__gte=desde)
        if hasta := _a_fecha(p.get("hasta"), fin_del_dia=True):
            eventos = eventos.filter(recibido__lte=hasta)
        limite = min(int(p.get("limite", LIMITE_POR_DEFECTO)), LIMITE_MAXIMO)
        despues_de = int(p["despues_de"]) if p.get("despues_de") else None
    except ValueError as e:
        return _error(str(e))
    if p.get("estado"):
        eventos = eventos.filter(estado=p["estado"])
    if p.get("evento"):
        eventos = eventos.filter(evento=p["evento"])
    if p.get("origen"):
        eventos = eventos.filter(origen=p["origen"])
    if p.get("coincide") in ("si", "true", "1"):
        eventos = eventos.filter(ruta__coincide_esp32=True)
    elif p.get("coincide") in ("no", "false", "0"):
        eventos = eventos.filter(ruta__coincide_esp32=False)
    if despues_de is not None:   # usado por el sondeo: solo lo nuevo
        eventos = eventos.filter(id__gt=despues_de)

    total = eventos.count()
    lista = [servicios.serializar_evento(e) for e in eventos[:max(limite, 0)]]
    return JsonResponse({"ok": True, "total": total, "eventos": lista})


@require_GET
def grafo(request):
    return JsonResponse({"ok": True, **motor.grafo_para_dashboard()})


@csrf_exempt     # no guarda nada: solo calcula
@require_POST
def simular(request):
    datos, error = _leer_json(request)
    if error:
        return error
    try:
        alfa = datos.get("alfa_pct")
        beta = datos.get("beta_pct")
        for nombre, valor in (("alfa_pct", alfa), ("beta_pct", beta)):
            if valor is not None and (not isinstance(valor, int) or isinstance(valor, bool) or not 0 <= valor <= 1000):
                raise ValueError(f"{nombre} debe ser un entero entre 0 y 1000.")
        resultado = motor.calcular(datos.get("bloqueos", []), datos.get("ocupadas", []), alfa, beta)
    except (ValueError, TypeError) as e:
        return _error(str(e))
    return JsonResponse({"ok": True, **resultado})
