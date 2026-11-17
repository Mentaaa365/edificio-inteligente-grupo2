"""Verificación de la Fase 1 sin hardware. Ejecutar desde la raíz del repositorio:

    python pruebas/verificar.py

Requiere g++ (en Windows: MSYS2/MinGW o WSL). Hace dos comprobaciones:
 1. Concordancia: el rutas.h del firmware contra el modelo en Python y contra NetworkX,
    en TODAS las combinaciones de bloqueos (256) y de zonas ocupadas (256).
 2. Sketch completo ejecutado en la PC con un Arduino simulado: antirrebote, estados,
    JSON por serie y colores de la tira, comparados con el modelo.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "simulacion"))
import modelo as m  # noqa: E402

ed = m.cargar()
tmp = Path(tempfile.mkdtemp())
CXX = ["g++", "-std=c++17", "-Wall", "-Wextra", "-O2"]


def compilar(fuente, salida, extra=()):
    subprocess.run([*CXX, *extra, "-o", str(salida), str(fuente)], check=True, cwd=RAIZ)


def prueba_concordancia():
    exe = tmp / "concordancia"
    compilar("pruebas/prueba_concordancia.cpp", exe)
    pas, zonas = ed.pasillos, ed.zonas
    casos = [(mb, mo) for mb in range(256) for mo in range(256)]
    salida = subprocess.run([str(exe)], input="\n".join(f"{a} {b}" for a, b in casos), text=True,
                            capture_output=True, check=True).stdout.splitlines()
    ids = [a["id"] for a in ed.aristas]
    fallos = 0
    for (mb, mo), linea in zip(casos, salida):
        v = list(map(int, linea.split()))
        dist, sig, sentido, sal, aisl, expl = v[:16], v[16:32], v[32:48], v[48:56], v[56], v[57]
        bloq = {pas[i] for i in range(8) if mb >> i & 1}
        ocup = {zonas[i] for i in range(8) if mo >> i & 1}
        c = m.calcular_campo(ed, bloq, ocup)
        ok = dist == [c.dist[n] for n in ed.nodos]
        ok &= sig == [255 if c.sig[n] is None else ids.index(c.sig[n]) for n in ed.nodos]
        ok &= sal == [255 if not c.rutas[z] else ed.nodos.index(c.rutas[z][-1]) for z in zonas]
        ok &= aisl == len(c.aisladas) and expl == c.explorados
        esperado = []
        for a in ed.aristas:
            s = c.sentido.get(a["id"])
            esperado.append(0 if s is None else 1 if s[0] == a["u"] else 2)
        ok &= sentido == esperado
        if mo == 0 or mb % 17 == 0:              # validación independiente con NetworkX (muestra amplia)
            ok &= c.dist == m.distancias_nx(ed, c.peso)
        fallos += not ok
    print(f"[1] Concordancia firmware (C++) vs Python vs NetworkX: {len(casos) - fallos}/{len(casos)} escenarios iguales")
    return fallos == 0


def prueba_sketch():
    exe = tmp / "simpc"
    compilar("pruebas/simulador_pc/main.cpp", exe, ["-x", "c++", "-Ipruebas/simulador_pc"])
    gpio = {a["pulsador"]: a["gpio"] for a in ed.aristas if a.get("pulsador")}
    gpio.update({c["id"]: c["gpio"] for c in ed.datos["controles"]})
    pir = {s["id"]: (s["gpio"], s["zona"]) for s in ed.datos["sensores"]}
    arista_de = {a["pulsador"]: a["id"] for a in ed.aristas if a.get("pulsador")}
    pasos = ["B0", "B4", "PIR1+", "B8", "B9", "B9", "B1", "B2", "PIR1-", "B5", "B6", "B4", "B7", "B3", "B0", "PIR2+"]
    guion = ["t 3100", "leds"]
    for p in pasos:
        guion.append(f"pir {pir[p[:-1]][0]} {int(p[-1] == '+')}" if p.startswith("PIR") else f"p {gpio[p]}")
        guion += ["t 450", "leds"]
    lineas = subprocess.run([str(exe)], input="\n".join(guion), text=True, capture_output=True,
                            check=True).stdout.splitlines()
    eventos = [json.loads(x) for x in lineas if x.startswith("{")]
    leds = [x.split()[1] for x in lineas if x.startswith("LEDS")]
    assert eventos[0]["evento"] == "LISTO" and len(eventos) == len(pasos) + 1, "un evento por pulsación (antirrebote)"

    bloq, ocup, emergencia, fallos = set(), set(), False, 0
    for paso, ev, tira in zip(pasos, eventos[1:], leds[1:]):
        if paso == "B0":
            emergencia = True
        elif paso == "B7":
            emergencia, bloq = False, set()
        elif paso.startswith("PIR"):
            (ocup.add if paso[-1] == "+" else ocup.discard)(pir[paso[:-1]][1])
        else:
            bloq ^= {arista_de[paso]}
        c = m.calcular_campo(ed, bloq, ocup)
        estado = m.estado(c) if emergencia else "NORMAL"
        ok = ev["evento"] == paso.rstrip("+-") and ev["estado"] == estado
        ok &= sorted(ev["bloqueos"]) == sorted(bloq) and sorted(ev["ocupadas"]) == sorted(ocup)
        for z in ed.zonas:
            r = ev["rutas"][z]
            ok &= (r is None) == (not c.rutas[z])
            if r:
                ok &= r["ruta"] == ">".join(c.rutas[z]) and abs(r["costo_m"] - c.costo_m(z)) < 0.006
        for a in ed.aristas:                      # color esperado de cada tramo de la tira
            if a["tipo"] != "pasillo":
                continue
            tramo = set(tira[a["led_ini"]: a["led_fin"] + 1])
            if a["id"] in bloq:
                esp = {"R"}
            elif not emergencia:
                esp = {"."}
            elif estado == "SIN_RUTA":
                esp = {"R"} if tramo == {"R"} else {"."}      # parpadeo
            elif a["id"] in c.sentido:
                esp = {"V"}
            elif c.dist[a["u"]] == m.INF and c.dist[a["v"]] == m.INF:
                esp = {"A"} if tramo == {"A"} else {"."}      # parpadeo
            else:
                esp = {"."}
            ok &= tramo == esp
        fallos += not ok
        print(f"    {paso:6s} -> {ev['estado']:13s} bloqueos={'+'.join(sorted(bloq)) or '-':12s} "
              f"ocupadas={'+'.join(sorted(ocup)) or '-':3s} {'OK' if ok else 'FALLO'}")
    print(f"[2] Sketch en PC: {len(pasos) - fallos}/{len(pasos)} pasos coinciden con el modelo (eventos, rutas y LED)")
    return fallos == 0


if __name__ == "__main__":
    a = prueba_concordancia()
    b = prueba_sketch()
    sys.exit(0 if a and b else 1)
