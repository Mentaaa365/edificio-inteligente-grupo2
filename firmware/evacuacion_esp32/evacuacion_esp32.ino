// Edificio inteligente con rutas dinámicas de evacuación · Grupo 2 · Modelos y Simulación
// Fase 1: prototipo para Wokwi (ESP32 + 82 LED WS2812 + 10 pulsadores + 2 PIR + buzzer).
//
// Flujo: entradas (pulsadores, PIR) -> modelo (pesos del grafo) -> Dijkstra -> LED, buzzer y JSON por serie.
// Librería necesaria: Adafruit NeoPixel.

#include <Adafruit_NeoPixel.h>
#include "config.h"
#include "grafo.h"
#include "rutas.h"

enum Estado : uint8_t { INICIALIZANDO, NORMAL, RUTA_ACTIVA, RUTA_PARCIAL, SIN_RUTA };
const char *const NOMBRE_ESTADO[] = {"INICIALIZANDO", "NORMAL", "RUTA_ACTIVA", "RUTA_PARCIAL", "SIN_RUTA"};

// ---------------------------------------------------------------- pulsadores con antirrebote
struct Pulsador {
  uint8_t pin;
  bool estable;          // último nivel aceptado (HIGH = suelto)
  bool ultimaLectura;
  uint32_t tCambio;
};

const uint8_t PIN_BLOQUEO[N_PASILLOS] = PINES_BLOQUEO;
const char *const ETIQUETA_BLOQUEO[N_PASILLOS] = ETIQUETAS_BLOQUEO;
const uint8_t PIN_PIR[N_PIR] = PINES_PIR;
const uint8_t ZONA_PIR[N_PIR] = ZONAS_PIR;

Pulsador btnAlarma = {PIN_ALARMA, HIGH, HIGH, 0};
Pulsador btnReinicio = {PIN_REINICIO, HIGH, HIGH, 0};
Pulsador btnBloqueo[N_PASILLOS];

// ---------------------------------------------------------------- estado del sistema
Adafruit_NeoPixel tira(TOTAL_LED, PIN_TIRA, NEO_GRB + NEO_KHZ800);

bool bloqueada[N_PASILLOS] = {false};   // entrada: pulsadores
bool ocupada[N_ZONAS] = {false};        // entrada: sensores PIR
bool emergencia = false;
Estado estado = INICIALIZANDO;
Campo campo;
uint32_t ultimoCalculoUs = 0;
uint32_t tFotograma = 0;
uint16_t fase = 0;

// Devuelve true una sola vez por pulsación (flanco de bajada ya filtrado).
bool pulsado(Pulsador &b) {
  bool lectura = digitalRead(b.pin);
  uint32_t ahora = millis();
  if (lectura != b.ultimaLectura) {      // hubo un cambio: puede ser rebote, se reinicia la cuenta
    b.ultimaLectura = lectura;
    b.tCambio = ahora;
  }
  if (lectura != b.estable && ahora - b.tCambio >= REBOTE_MS) {
    b.estable = lectura;                 // el nivel se mantuvo REBOTE_MS: se acepta
    return lectura == LOW;
  }
  return false;
}

// ---------------------------------------------------------------- modelo
void recalcular() {
  uint32_t t0 = micros();
  calcularCampo(bloqueada, ocupada, campo);
  ultimoCalculoUs = micros() - t0;
  if (!emergencia) estado = NORMAL;
  else if (campo.aisladas == 0) estado = RUTA_ACTIVA;
  else if (campo.aisladas == N_ZONAS) estado = SIN_RUTA;
  else estado = RUTA_PARCIAL;
}

// ---------------------------------------------------------------- salida por el puerto serie
void imprimirMetros(uint32_t costo) {
  Serial.printf("%lu.%02lu", (unsigned long)(costo / UNIDADES_POR_METRO),
                (unsigned long)((costo % UNIDADES_POR_METRO) / 100));
}

// Una línea JSON por evento: es lo que después recibirá el servidor (Fase 4).
void informar(const char *evento) {
  Serial.printf("{\"ms\":%lu,\"evento\":\"%s\",\"estado\":\"%s\",\"bloqueos\":[", (unsigned long)millis(), evento,
                NOMBRE_ESTADO[estado]);
  bool primero = true;
  for (uint8_t e = 0; e < N_PASILLOS; e++) {
    if (!bloqueada[e]) continue;
    Serial.printf("%s\"%s\"", primero ? "" : ",", NOMBRE_ARISTA[e]);
    primero = false;
  }
  Serial.print("],\"ocupadas\":[");
  primero = true;
  for (uint8_t z = 0; z < N_ZONAS; z++) {
    if (!ocupada[z]) continue;
    Serial.printf("%s\"%s\"", primero ? "" : ",", NOMBRE_NODO[PRIMERA_ZONA + z]);
    primero = false;
  }
  Serial.printf("],\"calculo_us\":%lu,\"explorados\":%u,\"aisladas\":%u,\"rutas\":{", (unsigned long)ultimoCalculoUs,
                campo.explorados, campo.aisladas);
  for (uint8_t z = 0; z < N_ZONAS; z++) {
    uint8_t n = PRIMERA_ZONA + z;
    Serial.printf("%s\"%s\":", z ? "," : "", NOMBRE_NODO[n]);
    if (campo.dist[n] == COSTO_INF) {
      Serial.print("null");
      continue;
    }
    Serial.print("{\"costo_m\":");
    imprimirMetros(campo.dist[n]);
    Serial.print(",\"ruta\":\"");
    Serial.print(NOMBRE_NODO[n]);
    while (n >= N_SALIDAS) {             // se sigue la ruta hasta llegar a una salida
      n = otroExtremo(campo.sig[n], n);
      Serial.printf(">%s", NOMBRE_NODO[n]);
    }
    Serial.print("\"}");
  }
  Serial.println("}}");
}

// ---------------------------------------------------------------- tira LED
void pintar() {
  bool parpadeo = (millis() / PARPADEO_MS) % 2;
  const uint32_t ROJO = tira.Color(255, 0, 0);
  const uint32_t ROJO_TENUE = tira.Color(40, 0, 0);
  const uint32_t AMBAR = tira.Color(255, 110, 0);
  const uint32_t AZUL_TENUE = tira.Color(0, 0, 30);

  for (uint8_t e = 0; e < N_PASILLOS; e++) {
    const Arista &a = ARISTAS[e];
    bool inalcanzable = campo.dist[a.u] == COSTO_INF && campo.dist[a.v] == COSTO_INF;
    for (uint8_t j = 0; j < a.longitud; j++) {
      uint32_t color = 0;
      if (estado == INICIALIZANDO) {
        color = AZUL_TENUE;
      } else if (bloqueada[e]) {
        color = emergencia ? ROJO : ROJO_TENUE;              // bloqueo: rojo fijo
      } else if (estado == SIN_RUTA) {
        color = parpadeo ? ROJO : 0;                         // nadie puede salir
      } else if (emergencia && campo.sentido[e] != SIN_USO) {
        // Ruta: verde con un punto brillante que avanza hacia la salida.
        // p = posición del LED contada en el sentido de la marcha.
        bool marchaDesdePrimerLed = (campo.sentido[e] == DE_U_A_V) == (a.ledDesde == a.u);
        uint8_t p = marchaDesdePrimerLed ? j : a.longitud - 1 - j;
        bool brillante = ((p + PASO_ANIMACION - fase % PASO_ANIMACION) % PASO_ANIMACION) == 0;
        color = brillante ? tira.Color(0, 255, 0) : tira.Color(0, 45, 0);
      } else if (emergencia && inalcanzable) {
        color = parpadeo ? AMBAR : 0;                        // tramo de una zona aislada
      }
      tira.setPixelColor(a.ledIni + j, color);
    }
  }
  tira.show();
}

// ---------------------------------------------------------------- buzzer
void sonar(bool encendido) {
#if SIMULACION
  if (encendido) tone(PIN_BUZZER, 2000);
  else noTone(PIN_BUZZER);
#else
  digitalWrite(PIN_BUZZER, encendido ? HIGH : LOW);
#endif
}

void actualizarBuzzer() {
  static bool sonando = false;
  uint32_t periodo = (estado == SIN_RUTA) ? 300 : 1000;      // más rápido si no hay salida
  bool debe = emergencia && (millis() % periodo) < 120;
  if (debe != sonando) {
    sonando = debe;
    sonar(sonando);
  }
}

// ---------------------------------------------------------------- arranque y ciclo principal
void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_ALARMA, INPUT_PULLUP);
  pinMode(PIN_REINICIO, INPUT_PULLUP);
  for (uint8_t e = 0; e < N_PASILLOS; e++) {
    btnBloqueo[e] = {PIN_BLOQUEO[e], HIGH, HIGH, 0};
    pinMode(PIN_BLOQUEO[e], INPUT_PULLUP);
  }
  for (uint8_t i = 0; i < N_PIR; i++) pinMode(PIN_PIR[i], INPUT);

  tira.begin();
  tira.setBrightness(BRILLO_GLOBAL);
  calcularCampo(bloqueada, ocupada, campo);
  pintar();
  Serial.println("Grupo 2 - Edificio inteligente. Esperando a que los PIR se estabilicen...");
}

void loop() {
  uint32_t ahora = millis();
  const char *evento = nullptr;

  // 1) Fin del calentamiento de los PIR
  if (estado == INICIALIZANDO) {
    if (ahora < CALENTAMIENTO_PIR_MS) return;
    estado = NORMAL;
    evento = "LISTO";
  }

  // 2) Entradas
  if (pulsado(btnAlarma) && !emergencia) {
    emergencia = true;
    evento = "B0";
  }
  if (pulsado(btnReinicio)) {
    emergencia = false;
    for (uint8_t e = 0; e < N_PASILLOS; e++) bloqueada[e] = false;
    evento = "B7";
  }
  for (uint8_t e = 0; e < N_PASILLOS; e++) {
    if (pulsado(btnBloqueo[e])) {
      bloqueada[e] = !bloqueada[e];        // cada pulsación alterna bloqueado / libre
      evento = ETIQUETA_BLOQUEO[e];
    }
  }
  for (uint8_t i = 0; i < N_PIR; i++) {
    bool presencia = digitalRead(PIN_PIR[i]) == HIGH;
    if (presencia != ocupada[ZONA_PIR[i]]) {
      ocupada[ZONA_PIR[i]] = presencia;
      evento = (i == 0) ? "PIR1" : "PIR2";
    }
  }

  // 3) Si algo cambió: recalcular el modelo, repintar e informar
  if (evento != nullptr) {
    recalcular();
    digitalWrite(PIN_LED, emergencia ? HIGH : LOW);
    pintar();
    informar(evento);
  }

  // 4) Animación y buzzer (sin esperas largas: el ciclo nunca se bloquea)
  if (emergencia && ahora - tFotograma >= FOTOGRAMA_MS) {
    tFotograma = ahora;
    fase++;
    pintar();
  }
  actualizarBuzzer();
  delay(PAUSA_CICLO_MS);   // pausa corta: cede tiempo al sistema y acelera la simulación en Wokwi
}
