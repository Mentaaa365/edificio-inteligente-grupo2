// Sustituto de la tira: guarda los colores en memoria para poder revisarlos.
#pragma once
#include <cstdint>
#define NEO_GRB 0
#define NEO_KHZ800 0
extern uint32_t pixeles[256];
extern unsigned actualizaciones;
struct Adafruit_NeoPixel {
  int n;
  Adafruit_NeoPixel(int cantidad, int, int) : n(cantidad) {}
  void begin() {}
  void setBrightness(int) {}
  static uint32_t Color(uint8_t r, uint8_t g, uint8_t b) { return ((uint32_t)r << 16) | ((uint32_t)g << 8) | b; }
  void setPixelColor(int i, uint32_t c) { if (i >= 0 && i < n) pixeles[i] = c; }
  void show() { actualizaciones++; }
};
