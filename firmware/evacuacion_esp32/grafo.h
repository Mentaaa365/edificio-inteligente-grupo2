// ARCHIVO GENERADO por herramientas/generar_grafo_h.py a partir de modelo/grafo.json.
// No lo edites a mano: cambia grafo.json y vuelve a generar.
#pragma once
#include <stdint.h>

#define N_NODOS 16
#define N_SALIDAS 3
#define N_ARISTAS 16
#define N_PASILLOS 8
#define N_ZONAS 8
#define PRIMERA_ZONA 8
#define TOTAL_LED 82

// Parámetros del modelo (porcentajes enteros: 50 = 0,5)
#define ALFA_PCT 50
#define BETA_PCT 100
#define RIESGO_ADY_PCT 50

// Índices de nodo
#define N_S1 0
#define N_S2 1
#define N_S3 2
#define N_C1 3
#define N_C2 4
#define N_C3 5
#define N_C4 6
#define N_C5 7
#define N_Z1 8
#define N_Z2 9
#define N_Z3 10
#define N_Z4 11
#define N_Z5 12
#define N_Z6 13
#define N_Z7 14
#define N_Z8 15

static const char *const NOMBRE_NODO[N_NODOS] = {"S1", "S2", "S3", "C1", "C2", "C3", "C4", "C5", "Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"};
static const char *const NOMBRE_ARISTA[N_ARISTAS] = {"e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8", "p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"};

struct Arista {
  uint8_t u, v;       // nodos que une
  uint8_t longitud;   // metros = número de LED en los pasillos
  int16_t ledIni;     // primer LED del tramo (-1 en las puertas)
  uint8_t ledDesde;   // nodo donde está el primer LED del tramo
};

static const Arista ARISTAS[N_ARISTAS] = {
  {N_S1, N_C1, 8, 0, 0},  // e1
  {N_C1, N_C2, 12, 8, 3},  // e2
  {N_C2, N_C3, 12, 20, 4},  // e3
  {N_C3, N_C4, 12, 32, 5},  // e4
  {N_C4, N_S3, 8, 44, 6},  // e5
  {N_C2, N_C5, 10, 52, 4},  // e6
  {N_C5, N_S2, 6, 62, 7},  // e7
  {N_C5, N_C3, 14, 68, 7},  // e8
  {N_Z1, N_C1, 3, -1, 8},  // p1
  {N_Z2, N_C1, 3, -1, 9},  // p2
  {N_Z3, N_C2, 3, -1, 10},  // p3
  {N_Z4, N_C3, 3, -1, 11},  // p4
  {N_Z5, N_C3, 3, -1, 12},  // p5
  {N_Z6, N_C4, 3, -1, 13},  // p6
  {N_Z7, N_C5, 4, -1, 14},  // p7
  {N_Z8, N_C4, 3, -1, 15},  // p8
};

// Intersección a la que da la puerta de cada zona (para la congestión)
static const uint8_t INTERSECCION_ZONA[N_ZONAS] = {N_C1, N_C1, N_C2, N_C3, N_C3, N_C4, N_C5, N_C4};
