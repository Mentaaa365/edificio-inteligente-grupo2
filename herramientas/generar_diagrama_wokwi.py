"""Genera firmware/evacuacion_esp32/diagram.json (circuito de Wokwi) a partir de modelo/grafo.json.

    python herramientas/generar_diagrama_wokwi.py

Cada pasillo es un wokwi-led-strip girado según el plano. Los ocho tramos se encadenan
DOUT -> DIN en el mismo orden de índices que la tira física (0..81).
(Con 82 wokwi-neopixel sueltos la simulación baja a menos del 10 % de velocidad.)
"""
import json
import math
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
g = json.loads((RAIZ / "modelo" / "grafo.json").read_text(encoding="utf-8"))
PX = 23                                   # píxeles por metro: es la separación entre LED de wokwi-led-strip
MARGEN, ALTO_TIRA = 8, 35                 # la tira mide 23·n + 16 px de ancho y 35 px de alto
ALTO = g["maqueta"]["alto_m"]
pos = {n["id"]: (n["x_m"], n["y_m"]) for n in g["nodos"]}
nombre = {n["id"]: n["nombre"] for n in g["nodos"]}
interseccion = {a["u"]: a["v"] for a in g["aristas"] if a["tipo"] == "puerta"}   # zona -> intersección


def px(x, y):
    return round(x * PX, 1), round((ALTO - y) * PX, 1)


partes, cables = [], []
Y_MIN = min(y for _, y in pos.values())
Y_PANEL = round((ALTO - Y_MIN + 6) * PX)  # fila de pulsadores, 6 m por debajo del nodo más bajo del plano

partes.append({"type": "board-esp32-devkit-c-v4", "id": "esp", "left": 40, "top": Y_PANEL + 130, "attrs": {}})
cables += [["esp:TX", "$serialMonitor:RX", "", []], ["esp:RX", "$serialMonitor:TX", "", []]]

# ---- Tira: un wokwi-led-strip por pasillo, centrado en el tramo y girado con su ángulo
anterior, total = f"esp:{g['salidas_esp32']['tira_led']}", 0
for a in sorted((a for a in g["aristas"] if a["tipo"] == "pasillo"), key=lambda a: a["led_ini"]):
    desde = a["led_desde"]
    hacia = a["v"] if a["u"] == desde else a["u"]
    (x1, y1), (x2, y2) = px(*pos[desde]), px(*pos[hacia])
    n = a["longitud_m"]
    assert a["led_ini"] == total, "los tramos deben ser consecutivos"
    total += n
    ancho = PX * n + 2 * MARGEN
    xm, ym = (x1 + x2) / 2, (y1 + y2) / 2
    angulo = round(math.degrees(math.atan2(y2 - y1, x2 - x1)), 2)   # el primer LED queda en el extremo "desde"
    tid = f"tira_{a['id']}"
    partes.append({"type": "wokwi-led-strip", "id": tid, "left": round(xm - ancho / 2, 1),
                   "top": round(ym - ALTO_TIRA / 2, 1), "rotate": angulo, "attrs": {"pixels": str(n)}})
    cables.append([anterior, f"{tid}:DIN", "green", []])
    anterior = f"{tid}:DOUT"
    horizontal = abs(y2 - y1) < 1
    partes.append({"type": "wokwi-text", "id": f"t_{a['id']}", "left": round(xm - 30 + (0 if horizontal else 40), 1),
                   "top": round(ym - (45 if horizontal else 10), 1), "attrs": {"text": f"{a['id']} · {a['pulsador']}"}})
assert total == g["parametros"]["total_led"]

# ---- Rótulos de salidas y zonas
for n in g["nodos"]:
    x, y = px(n["x_m"], n["y_m"])
    if n["tipo"] == "salida":
        partes.append({"type": "wokwi-text", "id": f"t_{n['id']}", "left": x - 30, "top": y + 28,
                       "attrs": {"text": f"SALIDA {n['id']}"}})
    elif n["tipo"] == "zona":
        cx, cy = pos[interseccion[n["id"]]]
        if abs(n["x_m"] - cx) > abs(n["y_m"] - cy):   # zona a un lado de su intersección: rótulo a ese lado
            izq, arr = (x - 110 if n["x_m"] < cx else x + 30), y - 10
        else:                                           # zona arriba o abajo: rótulo encima o debajo
            izq, arr = x - 30 + (-40 if n["x_m"] < cx else 20), (y - 50 if n["y_m"] > cy else y + 35)
        partes.append({"type": "wokwi-text", "id": f"t_{n['id']}", "left": round(izq, 1), "top": round(arr, 1),
                       "attrs": {"text": f"{n['id']} {n['nombre']}"}})

# ---- Sensores PIR (clic sobre el sensor durante la simulación -> "Simulate motion")
for s in g["sensores"]:
    x, y = px(*pos[s["zona"]])
    (zx, zy), (cx, cy) = pos[s["zona"]], pos[interseccion[s["zona"]]]
    if abs(zx - cx) > abs(zy - cy):   # zona a un lado de su intersección: el sensor va más hacia ese lado
        izq, arr = (x - 230, y - 50) if zx < cx else (x + 120, y - 50)
    else:                             # zona arriba o abajo: el sensor va por encima o por debajo del rótulo
        izq, arr = x - 40 + (-60 if zx < cx else 60), (y - 130 if zy > cy else y + 50)
    partes.append({"type": "wokwi-pir-motion-sensor", "id": s["id"].lower(), "left": round(izq, 1),
                   "top": round(arr, 1), "attrs": {"delayTime": "6"}})
    cables += [[f"{s['id'].lower()}:VCC", "esp:5V", "red", []],
               [f"{s['id'].lower()}:GND", "esp:GND.2", "black", []],
               [f"{s['id'].lower()}:OUT", f"esp:{s['gpio']}", "purple", []]]

# ---- Panel de pulsadores B0..B9 (teclas 0..9 del teclado)
botones = [(c["id"], c["funcion"].capitalize(), c["gpio"]) for c in g["controles"]]
botones += [(a["pulsador"], a["id"], a["gpio"]) for a in g["aristas"] if a.get("pulsador")]
botones.sort(key=lambda b: int(b[0][1:]))
colores = {"B0": "red", "B7": "blue"}
for i, (bid, funcion, gpio) in enumerate(botones):
    x = 330 + i * 125
    partes.append({"type": "wokwi-pushbutton", "id": bid.lower(), "left": x, "top": Y_PANEL + 170,
                   "attrs": {"color": colores.get(bid, "yellow"), "key": bid[1:], "label": f"{bid} {funcion}"}})
    cables += [[f"{bid.lower()}:1.l", f"esp:{gpio}", "orange" if bid not in colores else colores[bid], []],
               [f"{bid.lower()}:2.r", "esp:GND.1", "black", []]]

# ---- Buzzer
partes.append({"type": "wokwi-buzzer", "id": "bz1", "left": 200, "top": Y_PANEL + 120, "attrs": {"volume": "0.1"}})
cables += [["bz1:1", "esp:GND.3", "black", []], ["bz1:2", f"esp:{g['salidas_esp32']['buzzer']}", "gray", []]]

partes.append({"type": "wokwi-text", "id": "t_titulo", "left": 40, "top": 10, "attrs": {
    "text": "Grupo 2 · Edificio inteligente con rutas dinamicas de evacuacion\n"
            "Teclas 0-9 = pulsadores B0-B9 (0 alarma, 7 reinicio). Clic en un PIR -> Simulate motion."}})

diagrama = {"version": 1, "author": "Grupo 2 - Modelos y Simulacion", "editor": "wokwi",
            "parts": partes, "connections": cables, "dependencies": {}}
destino = RAIZ / "firmware" / "evacuacion_esp32" / "diagram.json"
destino.write_text(json.dumps(diagrama, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"diagram.json: {len(partes)} partes, {len(cables)} conexiones")
