# Edificio inteligente con rutas dinámicas de evacuación

**Grupo 2 · Modelos y Simulación · Componente Práctico 2 · UNEMI**

Ante una zona bloqueada o una emergencia simulada, el sistema calcula la ruta segura de cada zona con un grafo ponderado y la muestra con una tira LED en la maqueta.

## Estado

| Fase | Estado | Documento |
|---|---|---|
| 0. Arranque | Cerrada | [Fase 0](docs/Fase_0.md) |
| 1. Modelo y simulación previa | Modelo, simulación y [proyecto Wokwi](https://wokwi.com/projects/480903247493856257) hechos. Falta completar las pruebas en Wokwi | [Fase 1](docs/Fase_1.md) |
| 2. Hardware incremental | Pendiente | |
| 3. Servidor y dashboard | Pendiente | |
| 4. Integración y pruebas | Pendiente | |
| 5. Cierre | Pendiente | |

## Contenido

| Carpeta | Uso |
|---|---|
| [`modelo/grafo.json`](modelo/grafo.json) | Grafo del edificio: nodos, pasillos, LED, pulsadores y pines. Fuente única del proyecto. |
| [`simulacion/`](simulacion) | Modelo en Python con NetworkX, escenarios, ajuste de curvas y resultados. |
| [`firmware/evacuacion_esp32/`](firmware/evacuacion_esp32) | Sketch del ESP32 y archivos del proyecto Wokwi. |
| [`firmware/verificacion_esp32/`](firmware/verificacion_esp32) | Prueba mínima de la placa por USB para el inicio de la Fase 2. |
| [`herramientas/`](herramientas) | Generadores de `grafo.h` y `diagram.json` a partir de `grafo.json`. |
| [`pruebas/`](pruebas) | Verificación del firmware en la PC frente al modelo. |
| [`docs/`](docs) | Fases, plano, guía de entorno y evidencias. |

![Plano](docs/Plano_Fase_0.png)

## Uso rápido

```bash
git clone https://github.com/Mentaaa365/edificio-inteligente-grupo2.git
cd edificio-inteligente-grupo2
```

Sigue la [guía de Windows](docs/Entorno_Windows.md) para Python 3.13 y luego:

```powershell
.\.venv\Scripts\python.exe simulacion\simulacion_grafos.py
.\.venv\Scripts\python.exe pruebas\verificar.py
```

Si cambias `modelo/grafo.json`, regenera los archivos derivados:

```powershell
.\.venv\Scripts\python.exe herramientas\generar_grafo_h.py
.\.venv\Scripts\python.exe herramientas\generar_diagrama_wokwi.py
```
