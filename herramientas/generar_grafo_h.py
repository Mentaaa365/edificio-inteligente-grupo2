"""Genera firmware/evacuacion_esp32/grafo.h a partir de modelo/grafo.json.

    python herramientas/generar_grafo_h.py

Así el firmware, la simulación y el diagrama de Wokwi usan exactamente el mismo grafo.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
g = json.loads((RAIZ / "modelo" / "grafo.json").read_text(encoding="utf-8"))
nodos = [n["id"] for n in g["nodos"]]
idx = {n: i for i, n in enumerate(nodos)}
tipo = {n["id"]: n["tipo"] for n in g["nodos"]}
aristas = g["aristas"]
pasillos = [a for a in aristas if a["tipo"] == "pasillo"]
zonas = [n for n in nodos if tipo[n] == "zona"]
assert aristas[: len(pasillos)] == pasillos, "los pasillos deben ir primero"
assert [tipo[n] for n in nodos[:3]] == ["salida"] * 3, "las salidas deben ir primero"

L = ["// ARCHIVO GENERADO por herramientas/generar_grafo_h.py a partir de modelo/grafo.json.",
     "// No lo edites a mano: cambia grafo.json y vuelve a generar.",
     "#pragma once", "#include <stdint.h>", ""]
p = g["parametros"]
L += [f"#define N_NODOS {len(nodos)}", f"#define N_SALIDAS {sum(t == 'salida' for t in tipo.values())}",
      f"#define N_ARISTAS {len(aristas)}", f"#define N_PASILLOS {len(pasillos)}", f"#define N_ZONAS {len(zonas)}",
      f"#define PRIMERA_ZONA {idx[zonas[0]]}", f"#define TOTAL_LED {p['total_led']}", "",
      "// Parámetros del modelo (porcentajes enteros: 50 = 0,5)",
      f"#define ALFA_PCT {p['alfa_pct']}", f"#define BETA_PCT {p['beta_pct']}",
      f"#define RIESGO_ADY_PCT {p['riesgo_adyacente_pct']}", ""]
L += ["// Índices de nodo"] + [f"#define N_{n} {i}" for n, i in idx.items()] + [""]
L += ["static const char *const NOMBRE_NODO[N_NODOS] = {" + ", ".join(f'"{n}"' for n in nodos) + "};",
      "static const char *const NOMBRE_ARISTA[N_ARISTAS] = {" + ", ".join(f'"{a["id"]}"' for a in aristas) + "};", "",
      "struct Arista {",
      "  uint8_t u, v;       // nodos que une",
      "  uint8_t longitud;   // metros = número de LED en los pasillos",
      "  int16_t ledIni;     // primer LED del tramo (-1 en las puertas)",
      "  uint8_t ledDesde;   // nodo donde está el primer LED del tramo",
      "};", "", "static const Arista ARISTAS[N_ARISTAS] = {"]
for a in aristas:
    led = a.get("led_ini", -1)
    desde = idx[a.get("led_desde", a["u"])]
    L.append(f"  {{N_{a['u']}, N_{a['v']}, {a['longitud_m']}, {led}, {desde}}},  // {a['id']}")
L += ["};", "", "// Intersección a la que da la puerta de cada zona (para la congestión)",
      "static const uint8_t INTERSECCION_ZONA[N_ZONAS] = {" +
      ", ".join(next("N_" + a["v"] for a in aristas if a["tipo"] == "puerta" and a["u"] == z) for z in zonas) + "};", ""]
(RAIZ / "firmware" / "evacuacion_esp32" / "grafo.h").write_text("\n".join(L), encoding="utf-8")
print("grafo.h generado:", len(nodos), "nodos,", len(aristas), "aristas")
