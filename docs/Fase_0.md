# Fase 0. Arranque del proyecto

**Grupo 2 · Modelos y Simulación · UNEMI · Días 1 y 2**  
**Cotización consultada el 13 de noviembre de 2026 · Fase cerrada el 16 de noviembre de 2026**

> **Actualización del 20 de noviembre de 2026.** La maqueta se arma sobre un tablero MDF de **60 × 60 cm** y no sobre la base de 100 × 54 cm. Los pasillos, los LED y los pesos del modelo no cambian; solo se pliega el pasillo largo en forma de U. El replanteo, la compra real y el montaje están en la [Fase 2](Fase_2.md).

## Alcance propuesto para el arranque

El prototipo representa una planta con ocho zonas, cinco intersecciones y tres salidas. En la demostración, el ESP32 usará los pulsadores para registrar bloqueos y los PIR para registrar presencia. Con esas entradas se recalculará la ruta del modelo y se encenderá el recorrido en la tira LED. El tablero web mostrará el estado del prototipo. La Fase 1 desarrollará el grafo, la simulación en Python y la prueba inicial en Wokwi.

El [plano](Plano_Fase_0.png) conserva la topología y el mapeo de la sección D del plan. Se adopta una escala didáctica aproximada de **1:60**, porque una tira de 60 LED/m ocupa **1,67 cm por LED**. En el arranque se propuso una base de 100 × 54 cm para tender en línea recta los 52 LED de e1–e5 (86,7 cm); desde el 20 de noviembre la base es de **60 × 60 cm** y ese tramo se pliega (ver [Fase 2](Fase_2.md)). En el modelo se conserva la equivalencia **1 LED = 1 m de peso base** para los pasillos. Los recintos del croquis indican ubicación y conexión. Para Fase 1 se propone asignar **4 m a la puerta del Auditorio**, según el escenario S0 del plan, y **3 m a cada puerta restante** como supuesto inicial.

| Pasillo | Extremos | Peso base | Índices LED | Control físico |
|---|---|---:|---|---|
| e1 | S1–C1 | 8 m | 0–7 | B5 |
| e2 | C1–C2 | 12 m | 8–19 | B1 |
| e3 | C2–C3 | 12 m | 20–31 | B2 |
| e4 | C3–C4 | 12 m | 32–43 | B3 |
| e5 | C4–S3 | 8 m | 44–51 | B6 |
| e6 | C2–C5 | 10 m | 52–61 | B4 |
| e7 | C5–S2 | 6 m | 62–67 | B8 |
| e8 | C5–C3 | 14 m | 68–81 | B9 |

**Replanteo.** Las medidas en la base de 60 × 60 cm están en [`Plano_montaje_60x60.png`](Plano_montaje_60x60.png) y en la [Fase 2](Fase_2.md).

Para el corte, reserva una tira de 60 LED para e1–e5 (52 LED) y la otra para e6–e8 (30 LED). Quedan 38 LED de reserva.

B0 inicia la emergencia y B7 restablece la maqueta. PIR1 va en Z7 (Auditorio) y PIR2 en Z1 (Aula A). Se añadieron los pulsadores **B8 (e7, salida S2)** y **B9 (e8)** en los GPIO 18 y 19, de modo que los ocho pasillos se pueden bloquear en la maqueta y no solo en la simulación. El primer LED de cada tramo está en el primer extremo indicado en la tabla.

**Transporte.** La base es un tablero de MDF de 60 × 60 cm y 9 mm, con la electrónica en el borde inferior y los cables sujetos con bridas o cinta. Para llevarla al aula se protege la cara superior con una tapa de cartón del mismo tamaño separada por topes de 3 cm y se traslada en posición horizontal. La fuente, el cable USB y los repuestos van aparte.

## Lista de compras y presupuesto

> Esta es la cotización del arranque. La compra real del grupo y los cambios respecto a esta lista están en la [Fase 2](Fase_2.md#1-materiales).

Precios en USD. Los valores marcados como **estimado** sirven para reservar presupuesto. Confirmen las existencias, la ficha, el IVA y el envío antes de pagar.

| Material | Cant. | Unitario | Subtotal | Referencia o especificación |
|---|---:|---:|---:|---|
| ESP32 DevKit clásico ESP-WROOM-32 | 1 | 11,00 | 11,00 | [AV Electronics](https://avelectronics.cc/producto/esp32-esp-wroom-32-wifi-bluetooth/). Alternativa de [38 pines en APM](https://apmelectronica.com/producto/esp32-de-38-pines/) a 12,00. Confirmen puerto USB y pines. |
| Tira WS2812B 5 V, 60 LED/m, 1 m | 2 | 12,00 | 24,00 | [Mercado Libre Ecuador](https://listado.mercadolibre.com.ec/led-ws2812b-precio-ecuador). Alternativa [T-800](https://t800.tech/producto/tira-led-ws2812b-1m-60-leds-t8-ws2812b-1m.html) con precio por consultar. |
| PIR HC-SR501 | 2 | 2,85 | 5,70 | [AV Electronics](https://avelectronics.cc/producto/deteccion-presencia-pir-hc-sr501/). |
| Pulsador táctil momentáneo 12 × 12 mm | 10 | 0,24 | 2,40 | [Megatronica](https://megatronica.cc/producto/pulsador-grande-de-4-pines-12x12x4/), tarifa de 5–10 unidades. |
| Condensador electrolítico 1000 µF, 16 V | 2 | 0,35 | 0,70 | [Megatronica](https://megatronica.cc/producto/condensador-electrolitico-1000uf-16v/). |
| Adaptador cerrado 5 V CC, 3 A | 1 | 8,00 | 8,00 | [Tecnotrade](https://www.tecnotrade.com.ec/producto/adaptador-de-corriente-ac-dc-5v-3a/). Verificar etiqueta de salida, conector y polaridad. |
| Jack DC hembra a bornera 5,5 × 2,1 mm | 1 | 0,75 | 0,75 | [Megatronica](https://megatronica.cc/producto/conector-dc-bornera-jack-hembra/). Confirmar que coincide con la fuente. |
| Resistencias de 330–470 Ω y condensador cerámico de 100 nF | 1 lote | 1,00 | 1,00 | Estimado. Resistencia en datos y desacople para el conversor. |
| Buffer 74AHCT125 DIP-14 o módulo equivalente para WS2812B | 1 | Por cotizar | — | [Referencia técnica](https://www.adafruit.com/product/1787). Pedir adaptación de 3,3 V a 5 V apta para la señal de datos. |
| Protoboard de 830 puntos | 1 | 3,75 | 3,75 | Estimado del plan. [Robotics](https://roboticsec.com/producto/protoboard-830-puntos/). |
| Jumpers Dupont M–M y M–H | 1 juego de cada uno | 4,49 | 4,49 | Estimado del plan por ambos juegos. |
| Buzzer activo 5 V, módulo con transistor compatible con control de 3,3 V | 1 | 1,25 | 1,25 | Estimado del plan. [AV Electronics](https://avelectronics.cc/producto/buzzer-activo/). |
| Base, adhesivo, difusor y cable para alimentación y puentes de tira | 1 lote | 15,00–20,00 | 15,00–20,00 | Reserva estimada. Base de cartón pluma o MDF de 100 × 54 cm. |
| Cable USB de datos compatible con el ESP32 | 1 | Reutilizado | 0,00 | Comprar y agregar al total si el grupo no tiene uno compatible. |

**Subtotal base estimado: US$78,04–83,04**, equivalente a **US$26,01–27,68 por integrante** entre tres. Sumar el conversor, cualquier cable USB que haga falta y los envíos. **El grupo da la compra por realizada el 16 de noviembre de 2026.** El responsable guarda los comprobantes en `docs/evidencias/` con proveedor, importe, fecha y entrega estimada.

**Criterio para la alimentación.** Con la referencia de 60 mA por LED a blanco máximo, 82 LED podrían requerir 4,92 A. La fuente de 3 A se considera para la demostración con brillo limitado y colores de ruta y bloqueo. La alimentación de la tira irá desde la fuente por cable adecuado, con tierra común al ESP32. En Fase 2 se verificará el consumo con la configuración prevista antes de integrar el montaje (Adafruit Industries, s. f.).

## Cierre de la fase

| Actividad | Estado al 16 de noviembre de 2026 |
|---|---|
| Lectura grupal del PDF oficial y contraste con el alcance y el plano | Dada por cumplida por el grupo. |
| Cotización y compra | Dada por cumplida por el grupo. Comprobantes en `docs/evidencias/`. |
| Plano, zonas, conexiones, medidas y pesos | Cumplido. El plano se genera desde `modelo/grafo.json`. |
| Repositorio y acceso de los tres integrantes | Dado por cumplido por el grupo. |
| Reparto de aportes entre los tres integrantes | Dado por cumplido por el grupo. Cada integrante hace commits con su propio usuario. |
| Entorno de simulación | Primero se trabaja en simulación: Wokwi en el navegador para el circuito y el firmware, y Python 3.13 con `.venv` para el modelo. Ver [Fase 1](Fase_1.md). |
| Arduino IDE, core ESP32 y prueba en placa | Se trasladan al inicio de la Fase 2, cuando la simulación funcione. La [guía de Windows](Entorno_Windows.md) y el sketch de verificación quedan listos para ese momento. |

El repositorio [Mentaaa365/edificio-inteligente-grupo2](https://github.com/Mentaaa365/edificio-inteligente-grupo2) fue creado el 15 de noviembre de 2026 y usa la rama `main`. Cada integrante verifica Python 3.13 y su `.venv` en su propio equipo con la guía de Windows antes de ejecutar la simulación.

**Base de datos y entrega.** `.gitignore` excluye `*.sqlite3` para no versionar la base de trabajo. Al armar el RAR final se copia la base con los datos de las pruebas dentro de la carpeta del backend, porque el docente debe poder ejecutar el proyecto.

**Registro de la reunión.** Fecha: __________ · Participantes: __________ · Acuerdos: __________.

## Referencias

Adafruit Industries. (s. f.). *Powering NeoPixels*. Adafruit Learning System. https://learn.adafruit.com/adafruit-neopixel-uberguide/powering-neopixels

Arduino. (s. f.). *Downloading and installing the Arduino IDE 2*. https://docs.arduino.cc/software/ide-v2/tutorials/getting-started/ide-v2-downloading-and-installing

Espressif Systems. (s. f.). *Installing*. Arduino ESP32 Documentation. https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html

GitHub. (s. f.). *Creating a new repository*. GitHub Docs. https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository

Grupo 2. (s. f.). *Plan completo — Grupo 2: Edificio inteligente con rutas dinámicas de evacuación* [Plan interno de trabajo].

Python Software Foundation. (s. f.). *venv — Creation of virtual environments*. https://docs.python.org/3.13/library/venv.html

Wokwi. (s. f.). *ESP32 simulation*. Wokwi Docs. https://docs.wokwi.com/guides/esp32
