// Compila en la PC el MISMO rutas.h del firmware y evalúa todos los escenarios posibles.
// Entrada (stdin): una línea por escenario con dos máscaras de bits: bloqueos (e1..e8) y zonas ocupadas (Z1..Z8).
// Salida: dist[16] sig[16] sentido[16] salidaZona[8] aisladas explorados
#include <cstdio>
#include "../firmware/evacuacion_esp32/rutas.h"

int main() {
  unsigned mb, mo;
  Campo c;
  while (scanf("%u %u", &mb, &mo) == 2) {
    bool bloqueada[N_PASILLOS], ocupada[N_ZONAS];
    for (int i = 0; i < N_PASILLOS; i++) bloqueada[i] = (mb >> i) & 1;
    for (int i = 0; i < N_ZONAS; i++) ocupada[i] = (mo >> i) & 1;
    calcularCampo(bloqueada, ocupada, c);
    for (int n = 0; n < N_NODOS; n++) printf("%u ", c.dist[n]);
    for (int n = 0; n < N_NODOS; n++) printf("%u ", c.sig[n]);
    for (int e = 0; e < N_ARISTAS; e++) printf("%u ", c.sentido[e]);
    for (int z = 0; z < N_ZONAS; z++) printf("%u ", c.salidaZona[z]);
    printf("%u %u\n", c.aisladas, c.explorados);
  }
  return 0;
}
