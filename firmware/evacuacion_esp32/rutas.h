// Cálculo del campo de evacuación: Dijkstra multi-fuente desde las salidas.
//
// Este archivo es C++ puro (no usa nada de Arduino). Por eso el mismo código se
// compila en el ESP32 y en la PC (pruebas/prueba_concordancia.cpp) para comparar
// sus resultados con la simulación en Python (simulacion/modelo.py).
#pragma once
#include <stdint.h>
#include "grafo.h"

#define COSTO_INF 0xFFFFFFFFu
#define UNIDADES_POR_METRO 10000u   // los costos se guardan en diezmilésimas de metro
#define SIN_ARISTA 0xFF

enum Sentido : uint8_t { SIN_USO = 0, DE_U_A_V = 1, DE_V_A_U = 2 };

struct Campo {
  uint32_t peso[N_ARISTAS];     // peso dinámico de cada arista (COSTO_INF = bloqueada)
  uint32_t dist[N_NODOS];       // costo mínimo de cada nodo hasta su salida más cercana
  uint8_t  sig[N_NODOS];        // arista por la que se sale de cada nodo (SIN_ARISTA si no hay)
  uint8_t  sentido[N_ARISTAS];  // sentido en que alguna ruta recorre la arista
  uint8_t  salidaZona[N_ZONAS]; // salida asignada a cada zona (SIN_ARISTA si está aislada)
  uint8_t  aisladas;            // cuántas zonas no tienen ruta
  uint8_t  explorados;          // nodos extraídos por Dijkstra
};

static inline uint8_t otroExtremo(uint8_t arista, uint8_t nodo) {
  return ARISTAS[arista].u == nodo ? ARISTAS[arista].v : ARISTAS[arista].u;
}

static inline bool tocaNodo(uint8_t arista, uint8_t nodo) {
  return ARISTAS[arista].u == nodo || ARISTAS[arista].v == nodo;
}

// w_e = d_e * (100 + ALFA*o_e) * (100 + BETA*r_e/100)      (unidad: 0,0001 m)
static void calcularPesos(const bool *bloqueada, const bool *ocupada, uint32_t *peso) {
  bool riesgo[N_NODOS] = {false};      // nodos que tocan un pasillo bloqueado
  bool congestion[N_NODOS] = {false};  // intersecciones de zonas ocupadas
  for (uint8_t e = 0; e < N_PASILLOS; e++) {
    if (bloqueada[e]) {
      riesgo[ARISTAS[e].u] = true;
      riesgo[ARISTAS[e].v] = true;
    }
  }
  for (uint8_t z = 0; z < N_ZONAS; z++) {
    if (ocupada[z]) congestion[INTERSECCION_ZONA[z]] = true;
  }
  for (uint8_t e = 0; e < N_ARISTAS; e++) {
    const Arista &a = ARISTAS[e];
    if (e < N_PASILLOS && bloqueada[e]) {
      peso[e] = COSTO_INF;
      continue;
    }
    uint32_t o = (e < N_PASILLOS && (congestion[a.u] || congestion[a.v])) ? 1 : 0;
    uint32_t r = (riesgo[a.u] || riesgo[a.v]) ? RIESGO_ADY_PCT : 0;
    peso[e] = (uint32_t)a.longitud * (100 + ALFA_PCT * o) * (100 + BETA_PCT * r / 100);
  }
}

static void calcularCampo(const bool *bloqueada, const bool *ocupada, Campo &c) {
  calcularPesos(bloqueada, ocupada, c.peso);

  // 1) Dijkstra O(V^2) con todas las salidas como origen (distancia 0)
  bool visto[N_NODOS] = {false};
  for (uint8_t n = 0; n < N_NODOS; n++) c.dist[n] = (n < N_SALIDAS) ? 0 : COSTO_INF;
  c.explorados = 0;
  while (true) {
    uint8_t u = SIN_ARISTA;
    uint32_t mejor = COSTO_INF;
    for (uint8_t n = 0; n < N_NODOS; n++) {
      if (!visto[n] && c.dist[n] < mejor) {
        mejor = c.dist[n];
        u = n;
      }
    }
    if (u == SIN_ARISTA) break;          // lo que queda es inalcanzable
    visto[u] = true;
    c.explorados++;
    for (uint8_t e = 0; e < N_ARISTAS; e++) {
      if (c.peso[e] == COSTO_INF || !tocaNodo(e, u)) continue;
      uint8_t v = otroExtremo(e, u);
      if (c.dist[u] + c.peso[e] < c.dist[v]) c.dist[v] = c.dist[u] + c.peso[e];
    }
  }

  // 2) Siguiente arista de cada nodo: la primera, por índice, que conserva el costo mínimo
  for (uint8_t n = 0; n < N_NODOS; n++) {
    c.sig[n] = SIN_ARISTA;
    if (n < N_SALIDAS || c.dist[n] == COSTO_INF) continue;
    for (uint8_t e = 0; e < N_ARISTAS; e++) {
      if (c.peso[e] == COSTO_INF || !tocaNodo(e, n)) continue;
      uint8_t v = otroExtremo(e, n);
      if (c.dist[v] != COSTO_INF && c.dist[v] + c.peso[e] == c.dist[n]) {
        c.sig[n] = e;
        break;
      }
    }
  }

  // 3) Ruta de cada zona: se sigue sig[] hasta una salida y se anota el sentido de cada arista
  for (uint8_t e = 0; e < N_ARISTAS; e++) c.sentido[e] = SIN_USO;
  c.aisladas = 0;
  for (uint8_t z = 0; z < N_ZONAS; z++) {
    uint8_t n = PRIMERA_ZONA + z;
    if (c.dist[n] == COSTO_INF) {
      c.salidaZona[z] = SIN_ARISTA;
      c.aisladas++;
      continue;
    }
    while (n >= N_SALIDAS) {
      uint8_t e = c.sig[n];
      c.sentido[e] = (ARISTAS[e].u == n) ? DE_U_A_V : DE_V_A_U;
      n = otroExtremo(e, n);
    }
    c.salidaZona[z] = n;
  }
}
