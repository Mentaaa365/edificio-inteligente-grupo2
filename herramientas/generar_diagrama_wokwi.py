"""Genera firmware/evacuacion_esp32/diagram.json (circuito de Wokwi) a partir de modelo/grafo.json.

    python herramientas/generar_diagrama_wokwi.py

Cada tramo recto de pasillo es un wokwi-led-strip girado según el plano; los pasillos en L (e6, e8)
se parten en dos tiras seguidas. Todas se encadenan DOUT -> DIN en el mismo orden de índices que la
tira física (0..81).
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
sala = {n["id"]: n["sala"] for n in g["nodos"] if n["tipo"] == "zona"}   # rectángulo de cada zona [x0, y0, x1, y1]


def px(x, y):
    return round(x * PX, 1), round((ALTO - y) * PX, 1)


def en_sala(x, y):
    return any(x0 < x < x1 and y0 < y < y1 for x0, y0, x1, y1 in sala.values())


def centro(z):
    x0, y0, x1, y1 = sala[z]
    return (x0 + x1) / 2, (y0 + y1) / 2


partes, cables = [], []
Y_MIN = min(y for _, y in pos.values())
Y_PANEL = round((ALTO - Y_MIN + 6) * PX)  # fila de pulsadores, 6 m por debajo del nodo más bajo del plano

partes.append({"type": "board-esp32-devkit-c-v4", "id": "esp", "left": 40, "top": Y_PANEL + 130, "attrs": {}})
cables += [["esp:TX", "$serialMonitor:RX", "", []], ["esp:RX", "$serialMonitor:TX", "", []]]

# ---- Tira: un wokwi-led-strip por tramo recto, centrado en el tramo y girado con su ángulo
def recorrido(a):
    """Puntos del pasillo desde su primer LED (led_desde) hasta el otro extremo, con los quiebres de "trazo"."""
    pts = [pos[a["u"]], *[tuple(p) for p in a.get("trazo", [])], pos[a["v"]]]
    return pts if a["led_desde"] == a["u"] else pts[::-1]


anterior, total = f"esp:{g['salidas_esp32']['tira_led']}", 0
for a in sorted((a for a in g["aristas"] if a["tipo"] == "pasillo"), key=lambda a: a["led_ini"]):
    assert a["led_ini"] == total, "los tramos deben ser consecutivos"
    pts = recorrido(a)
    tramos = list(zip(pts, pts[1:]))
    rotulo = max(range(len(tramos)), key=lambda k: math.dist(*tramos[k]))   # el rótulo va en el tramo más largo
    for k, (p, q) in enumerate(tramos):
        n = math.dist(p, q)
        assert abs(n - round(n)) < 1e-6, f"{a['id']}: cada tramo debe medir un número entero de LED"
        n = round(n)
        total += n
        (x1, y1), (x2, y2) = px(*p), px(*q)
        ancho = PX * n + 2 * MARGEN
        xm, ym = (x1 + x2) / 2, (y1 + y2) / 2
        angulo = round(math.degrees(math.atan2(y2 - y1, x2 - x1)), 2)   # el primer LED queda en el extremo inicial
        tid = f"tira_{a['id']}" + ("" if len(tramos) == 1 else "abcdefgh"[k])
        partes.append({"type": "wokwi-led-strip", "id": tid, "left": round(xm - ancho / 2, 1),
                       "top": round(ym - ALTO_TIRA / 2, 1), "rotate": angulo, "attrs": {"pixels": str(n)}})
        cables.append([anterior, f"{tid}:DIN", "green", []])
        anterior = f"{tid}:DOUT"
        if k == rotulo:   # el rótulo va al lado del tramo donde no haya una sala (si la hay a ambos lados, arriba/derecha)
            (mx, my) = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
            if abs(y2 - y1) < 1:
                arriba = not en_sala(mx, my + 1.5) or en_sala(mx, my - 1.5)
                izq, arr = xm - 30, ym - 45 if arriba else ym + 22
            else:
                derecha = not en_sala(mx + 1.5, my) or en_sala(mx - 1.5, my)
                izq, arr = (xm + 10 if derecha else xm - 75), ym - 10
            partes.append({"type": "wokwi-text", "id": f"t_{a['id']}", "left": round(izq, 1), "top": round(arr, 1),
                           "attrs": {"text": f"{a['id']} · {a['pulsador']}"}})
    assert total == a["led_fin"] + 1, f"{a['id']}: la suma de sus tramos no coincide con su número de LED"
assert total == g["parametros"]["total_led"]

# ---- Rótulos de salidas y zonas (cada zona en el centro de su sala; si tiene PIR, el rótulo va a la izquierda)
pir = {s["zona"] for s in g["sensores"]}
for n in g["nodos"]:
    x, y = px(n["x_m"], n["y_m"])
    if n["tipo"] == "salida":
        partes.append({"type": "wokwi-text", "id": f"t_{n['id']}", "left": x - 30, "top": y + 28,
                       "attrs": {"text": f"SALIDA {n['id']}"}})
    elif n["tipo"] == "zona":
        cx, cy = px(*centro(n["id"]))
        partes.append({"type": "wokwi-text", "id": f"t_{n['id']}", "left": round(cx - 44 - (55 if n["id"] in pir else 0), 1),
                       "top": round(cy - 15, 1), "attrs": {"text": f"{n['id']}\n{n['nombre']}"}})

# ---- Sensores PIR (clic sobre el sensor durante la simulación -> "Simulate motion"), a la derecha del rótulo
for s in g["sensores"]:
    cx, cy = px(*centro(s["zona"]))
    partes.append({"type": "wokwi-pir-motion-sensor", "id": s["id"].lower(), "left": round(cx + 5, 1),
                   "top": round(cy - 40, 1), "attrs": {"delayTime": "6"}})
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
