// Configuración del prototipo: pines, tiempos y colores.
#pragma once

// 1 = simulación en Wokwi (buzzer pasivo con tone(), PIR listo en 3 s)
// 0 = maqueta real (zumbador activo TMB12A05 con transistor NPN: HIGH = suena; PIR HC-SR501 listo tras 60 s)
#define SIMULACION 1

// ---- Pines (ESP32 DevKit). Se evitan los pines de arranque 0, 2, 5, 12 y 15 para entradas.
// En la placa de 30 pines con CH340 los GPIO llevan los mismos números (el 16 está rotulado RX2).
#define PIN_TIRA    16     // -> 74AHCT125 (pata 2) -> 330 ohm -> DIN de la tira
#define PIN_BUZZER  23     // -> 1 kohm -> base del transistor NPN que enciende el zumbador
#define PIN_LED     2      // LED integrado de la placa

// Pulsadores: un lado al GPIO y el otro a GND, con INPUT_PULLUP (pulsado = LOW)
#if SIMULACION
#define PIN_ALARMA    4    // B0 en Wokwi
#else
#define PIN_ALARMA    12   // B0 en la maqueta: en la protoboard el lado de D4 queda tapado por la placa.
                           // GPIO 12 es pin de arranque, pero el pulsador solo lo lleva a GND (seguro).
#endif
#define PIN_REINICIO  14   // B7
// Pulsador que bloquea cada pasillo, en el orden e1..e8 de grafo.h:
//                                  e1  e2  e3  e4  e5  e6  e7  e8
//                                  B5  B1  B2  B3  B6  B4  B8  B9
#define PINES_BLOQUEO             { 33, 25, 26, 27, 13, 32, 18, 19 }
#define ETIQUETAS_BLOQUEO         { "B5", "B1", "B2", "B3", "B6", "B4", "B8", "B9" }

// Sensores PIR: salida activa en alto. Los GPIO 34 y 35 son solo de entrada.
#define N_PIR 2
#define PINES_PIR  { 34, 35 }
#define ZONAS_PIR  { 6, 0 }    // índice de zona: PIR1 -> Z7 (6), PIR2 -> Z1 (0)

// ---- Tiempos (ms)
#define REBOTE_MS          40      // un cambio debe mantenerse este tiempo para aceptarse
#define FOTOGRAMA_MS       120     // velocidad de la animación de la ruta
#define PARPADEO_MS        400
#define PAUSA_CICLO_MS     2       // pausa al final de cada vuelta de loop()
#if SIMULACION
#define CALENTAMIENTO_PIR_MS  3000
#else
#define CALENTAMIENTO_PIR_MS  60000
#endif

// ---- Tira LED
#define BRILLO_GLOBAL  60        // 0-255. Mantener bajo: limita el consumo de la tira
#define PASO_ANIMACION 4         // un LED brillante cada 4, avanzando hacia la salida
