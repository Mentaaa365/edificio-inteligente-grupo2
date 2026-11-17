// Sustituto mínimo de Arduino para ejecutar el sketch en la PC (solo para pruebas).
#pragma once
#include <cstdarg>
#include <cstdint>
#include <cstdio>

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2

extern uint64_t reloj_us;
extern int nivel[40];
extern bool buzzer;

inline uint32_t millis() { return (uint32_t)(reloj_us / 1000); }
inline uint32_t micros() { return (uint32_t)(reloj_us += 7); }   // cada lectura "tarda" 7 µs
inline void delay(uint32_t ms) { reloj_us += (uint64_t)ms * 1000; }
inline void pinMode(int, int) {}
inline int digitalRead(int pin) { return nivel[pin]; }
inline void digitalWrite(int pin, int v) { nivel[pin] = v; }
inline void tone(int, int) { buzzer = true; }
inline void noTone(int) { buzzer = false; }

struct SerieFalsa {
  void begin(long) {}
  void print(const char *s) { fputs(s, stdout); }
  void println(const char *s) { puts(s); }
  void printf(const char *f, ...) {
    va_list ap;
    va_start(ap, f);
    vprintf(f, ap);
    va_end(ap);
  }
};
extern SerieFalsa Serial;
