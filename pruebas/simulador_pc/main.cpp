// Ejecuta el sketch real en la PC siguiendo un guion leído por stdin:
//   t <ms>          avanza el tiempo (1 ms por vuelta de loop)
//   p <gpio>        pulsa y suelta un pulsador, con rebotes al apretar y al soltar
//   pir <gpio> <0|1> cambia la salida de un PIR
//   leds            imprime la tira: V verde, R rojo, A ámbar, Z azul, . apagado
#include <cstring>
#include "Arduino.h"
#include "Adafruit_NeoPixel.h"

uint64_t reloj_us = 0;
int nivel[40];
bool buzzer = false;
SerieFalsa Serial;
uint32_t pixeles[256];
unsigned actualizaciones = 0;

#include "../../firmware/evacuacion_esp32/evacuacion_esp32.ino"

static void avanzar(int ms) {
  for (int i = 0; i < ms; i++) {
    reloj_us += 1000;
    loop();
  }
}

static void rebotar(int pin, int final) {      // 8 cambios rápidos antes de quedar estable
  for (int i = 0; i < 8; i++) {
    nivel[pin] = (i % 2) ? !final : final;
    avanzar(1);
  }
  nivel[pin] = final;
}

int main() {
  for (int i = 0; i < 40; i++) nivel[i] = HIGH;
  nivel[34] = nivel[35] = LOW;
  setup();
  char orden[16];
  while (scanf("%15s", orden) == 1) {
    if (!strcmp(orden, "t")) {
      int ms; if (scanf("%d", &ms) == 1) avanzar(ms);
    } else if (!strcmp(orden, "p")) {
      int pin; if (scanf("%d", &pin) != 1) break;
      rebotar(pin, LOW); avanzar(120); rebotar(pin, HIGH); avanzar(120);
    } else if (!strcmp(orden, "pir")) {
      int pin, v; if (scanf("%d %d", &pin, &v) != 2) break;
      nivel[pin] = v; avanzar(5);
    } else if (!strcmp(orden, "leds")) {
      printf("LEDS ");
      for (int i = 0; i < TOTAL_LED; i++) {
        uint32_t c = pixeles[i];
        int r = c >> 16, g = (c >> 8) & 255, b = c & 255;
        putchar(!c ? '.' : (r && g) ? 'A' : r ? 'R' : g ? 'V' : b ? 'Z' : '?');
      }
      printf(" show=%u buzzer_gpio=%d\n", actualizaciones, PIN_BUZZER);
    }
  }
  return 0;
}
