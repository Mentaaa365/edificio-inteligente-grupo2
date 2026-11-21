# Fase 2. Montaje de la maqueta

**Grupo 2 · Modelos y Simulación · UNEMI**  
**Guía preparada el 20 de noviembre de 2026 · Montaje a cargo del grupo**

La maqueta se arma sobre un tablero MDF de **60 × 60 cm**. Los 8 pasillos, los 82 LED, los índices de la tira y los pesos del modelo son los mismos de las fases 0, 1 y 3; solo cambia la disposición. El plano es el de un edificio real de una planta: muros exteriores, salas con su puerta, pasillos en ángulo recto (e6 y e8 tienen forma de L), tres salidas en las fachadas y, fuera del edificio, el panel de control, el punto de encuentro y la electrónica. Por eso el firmware, la simulación y el servidor siguen valiendo sin cambios en el cálculo. Las coordenadas de `modelo/grafo.json` (nodos, salas, puertas, muros y quiebres de los pasillos) ya están en la nueva base, y de ellas salen el plano, el diagrama de Wokwi, el dashboard y el plano de replanteo.

| Entregable | Archivo | Estado |
|---|---|---|
| Lista de materiales comprados | Sección 1 | Hecha |
| Plano de replanteo con medidas | [`Plano_montaje_60x60.png`](Plano_montaje_60x60.png), generado por [`herramientas/plano_montaje.py`](../herramientas/plano_montaje.py) | Hecho |
| Plano del modelo | [`Plano_Fase_0.png`](Plano_Fase_0.png) | Actualizado a 60 × 60 cm |
| Montaje y pruebas por etapas | Secciones 3 a 5 | Pendiente: lo hace el grupo |

## 1. Materiales

### Comprado por el grupo

| Material | Cant. | Uso en la maqueta |
|---|---:|---|
| Módulo ESP32 WROOM, 30 pines, CH340, USB-C | 1 | Controlador. Necesita el controlador CH340 en Windows ([guía de entorno](Entorno_Windows.md)) |
| Sensor de movimiento HC-SR501 | 4 | PIR1 en Z7 (Auditorio) y PIR2 en Z1 (Aula A). Dos quedan de repuesto |
| Pulsador 12 × 12 mm de dos patas | 12 | B0–B9. Dos quedan de repuesto |
| Jack hembra 2,1 mm con bornera ("balun"), 12 V máx. | 1 | Entrada de la fuente de 5 V. El 12 V es el máximo que soporta, no la tensión de trabajo |
| Condensador electrolítico 1000 µF, 25 V | 2 | Reserva de energía en la entrada de la pieza A (S1) y de la pieza B (C2) |
| Condensador cerámico 100 nF ("104") | 2 | Desacople del 74AHCT125 entre sus patas 14 y 7; uno de repuesto |
| Resistencia 330 Ω, 1/2 W | 2 | Serie en la línea de datos de la tira; una de repuesto |
| Protoboard WB-102 | 1 | Electrónica (ESP32, 74AHCT125, transistor) |
| Jumpers macho-macho y macho-hembra, 20 cm | 12 + 12 | Conexiones en la protoboard y a los pines de los PIR |
| Cable UTP Cat-5e | 4 m | Hilos rígidos para pulsadores, PIR, puentes de la tira y alimentación (dos hilos por polo) |
| Zumbador activo TMB12A05 | 1 | Alarma sonora. Es de 5 V nominales y hasta 30 mA, así que se enciende con un transistor desde el GPIO 23 |
| Tablero MDF crudo 0,60 × 0,60 m, 9 mm | 1 | Base de la maqueta |
| Cautín 40 W, 2 m de estaño, pinza punta recta, multímetro | 1 c/u | Puentes de la tira, cables de pulsadores y comprobaciones |
| Pegamento instantáneo UHU, cinta doble faz, cinta aislante, estilete o tijeras | — | Fijar la tira y los pliegues, aislar uniones, cortar |
| Cable USB-C de datos | 1 | Programación y enlace serie con el servidor (`puente_serial`) |

### Lo que faltaba (dado por comprado)

| Material | Cant. | Por qué |
|---|---:|---|
| Tira LED **WS2812B 5 V, 60 LED/m, IP30**, PCB de 10 mm | 2 × 1 m | La tira Foco71 es RGB analógica de 12 V: todos sus LED muestran el mismo color, así que no puede marcar una ruta por pasillo. La WS2812B permite un color por LED |
| Circuito integrado **74AHCT125N** (DIP-14) | 1 | Convierte la señal de 3,3 V del ESP32 a 5 V. El 74LS125AN comprado solo garantiza 2,4 V en alto, menos que lo que pide la WS2812B (0,7 × VDD = 3,5 V) |
| Fuente **5 V, 3 A**, plug 5,5 × 2,1 mm, centro positivo | 1 | Alimenta la tira y los PIR. El adaptador de 12 V de la tira Foco71 **no se usa**: dañaría la tira WS2812B |
| Transistor NPN **2N2222A** (TO-92) | 1 | Enciende el zumbador con 5 V. A 3,3 V y directo del GPIO el TMB12A05 queda por debajo de su tensión de trabajo |
| Resistencia **1 kΩ** | 1 | Base del transistor (unos 2,6 mA) |
| Diodo **1N4148** | 1 | Protege el transistor del pico inductivo del zumbador magnético |

**No se usan:** la tira Foco71 con su adaptador de 12 V y control remoto, el 74LS125AN y los cables JST XH (se pueden cortar y aprovechar como hilos de 3 colores para los puentes de la tira).

## 2. Plano y replanteo

![Plano de replanteo](Plano_montaje_60x60.png)

Todas las medidas se toman desde la **esquina inferior izquierda** del tablero. El edificio ocupa el centro; el panel de control va en la esquina superior derecha, el punto de encuentro y la leyenda en la superior izquierda y la electrónica abajo, todo fuera de los muros.

| Punto | x (cm) | y (cm) |
|---|---:|---:|
| S1 (salida oeste) | 6,7 | 15,0 |
| C1 | 20,0 | 15,0 |
| C4 | 40,0 | 15,0 |
| S3 (salida este) | 53,3 | 15,0 |
| C2 | 20,0 | 35,0 |
| C3 | 40,0 | 35,0 |
| C5 | 26,7 | 45,0 |
| S2 (salida norte) | 26,7 | 55,0 |
| Quiebre de e6 | 20,0 | 45,0 |
| Quiebre de e8 | 40,0 | 45,0 |

El muro exterior es un rectángulo de 6,7 a 53,3 cm en x y de 6,7 a 36,0 cm en y, con un cuerpo norte (x 19,0–41,0; y 36,0–46,0) que rodea el Auditorio y un vestíbulo de 3 cm de ancho (x 25,2–28,2) que sube hasta S2 en y = 55,0. Las salidas S1 y S3 son aberturas en las fachadas oeste y este; S2, en el extremo del vestíbulo norte.

| Zona | Sala (cm) | Puerta (bisagra → extremo de la hoja) |
|---|---|---|
| Z1 Aula A (PIR2) | x 6,7–19,0 · y 16,0–36,0 | muro este, (19,0; 16,3) → (19,0; 18,3), a e2 junto a C1 |
| Z2 Aula B | x 6,7–21,0 · y 6,7–14,0 | muro norte, (18,7; 14,0) → (16,7; 14,0), a e1 junto a C1 |
| Z3 Laboratorio | x 21,0–29,9 · y 6,7–34,0 | muro norte, (21,3; 34,0) → (23,3; 34,0), a e3 junto a C2 |
| Z4 Oficina | x 30,1–39,0 · y 6,7–34,0 | muro norte, (38,7; 34,0) → (36,7; 34,0), a e3 junto a C3 |
| Z5 Baños | x 41,0–53,3 · y 26,0–36,0 | muro oeste, (41,0; 33,7) → (41,0; 31,7), a e4 junto a C3 |
| Z6 Bodega | x 41,0–53,3 · y 16,0–25,7 | muro oeste, (41,0; 16,3) → (41,0; 18,3), a e4 junto a C4 |
| Z7 Auditorio (PIR1) | x 21,0–39,0 · y 36,0–44,0 | muro norte, (30,0; 44,0) → (28,0; 44,0), a e8 junto a C5 |
| Z8 Recepción | x 39,0–53,3 · y 6,7–14,0 | muro norte, (41,3; 14,0) → (43,3; 14,0), a e5 junto a C4 |

El Auditorio queda dentro del anillo e3–e6–e8, así que se puede salir de él por C5 (S2) o, si ese lado se bloquea, rodeando por C2 o C3. Cada puerta está a menos de su largo en el modelo (3 m; 4 m el Auditorio) de su intersección, para que la heurística de A* siga siendo admisible.

Cada pasillo mide en el tablero exactamente su número de LED × 1,667 cm: e1 y e5, 13,3 cm; e2, e3 y e4, 20 cm; e6, 16,7 cm en L (10 cm hacia el norte desde C2 y 6,7 cm hacia el este hasta C5); e7, 10 cm; e8, 23,3 cm en L (13,3 cm hacia el este desde C5 y 10 cm hacia el sur hasta C3). `plano_montaje.py` lo comprueba cada vez que se genera el plano, junto con que ninguna tira atraviese una sala, que cada puerta caiga en su sala y que las salidas estén en un muro exterior.

**Muros y puertas.** Los muros se marcan con lápiz y se levantan con tiras de cartón o MDF de 1–2 cm de alto, dejando el ancho de pasillo libre a los lados de la tira (unos 2 cm). En cada puerta se deja una abertura de 2 cm y se dibuja el arco de giro hacia dentro de la sala. Los extintores son adhesivos decorativos (cuatro, en las posiciones rojas del plano); la maqueta es de una planta y no lleva escaleras.

## 3. Tira LED

La tira se corta en **tres piezas** y los quiebres se doblan sin cortar (7 pliegues, marcados con **D** en el plano):

| Pieza | Pasillos | LED | Índices | Largo | Pliegues (entre los LED) |
|---|---|---:|---|---:|---|
| A | e1 → e2 → e3 → e4 → e5 | 52 | 0–51 | 86,7 cm | C1 (7 y 8), C2 (19 y 20), C3 (31 y 32), C4 (43 y 44) |
| B | e6 → e7 | 16 | 52–67 | 26,7 cm | quiebre de e6 (57 y 58), C5 (61 y 62) |
| C | e8 | 14 | 68–81 | 23,3 cm | quiebre de e8 (75 y 76) |

La pieza A sale del primer metro y las piezas B y C del segundo (sobran 38 LED para practicar).

1. **Sentido.** Las flechas impresas en la tira van de DIN a DOUT y deben seguir las flechas verdes del plano: e1 empieza en S1, e6 en C2 y e8 en C5.
2. **Corte.** Solo por la línea marcada entre dos LED, a mitad de los pads de cobre.
3. **Pliegues.** Doblar la tira 45° hacia atrás y luego otra vez para formar el ángulo, justo en el espacio entre los dos LED indicados, nunca encima de un LED. Fijar el pliegue con una gota de pegamento. Practiquen primero con los LED sobrantes. Si un pliegue deja de conducir, se corta en esa línea y se puentea con tres hilos soldados como en el paso 4.
4. **Puentes soldados (3 hilos: 5 V, datos, GND).**
   - **Entrada (S1):** de la protoboard a los pads 5 V / DIN / GND del LED 0.
   - **J5 (unos 45 cm):** de los pads DOUT/5 V/GND del final de la pieza A (S3) a la entrada de la pieza B (C2). Va **por debajo de la base**: se taladran dos agujeros de 4–5 mm junto a S3 y junto a C2, se pasan los tres hilos y se fijan con cinta por debajo del tablero. Así no cruza las salas ni los muros.
   - **J7 (unos 15 cm):** del final de la pieza B (S2) a la entrada de la pieza C (C5). Va por el vestíbulo norte, junto a la tira de e7.
   - Usen hilos del UTP: naranja para 5 V, verde para datos y azul para GND, por ejemplo. Estañen primero el pad y el hilo, y luego únanlos en 2–3 s con el cautín. Comprueben con el multímetro, en continuidad, que no quedó un puente entre pads vecinos.
5. **Condensadores de 1000 µF:** uno entre 5 V y GND en la entrada de la pieza A (protoboard) y otro en la entrada de la pieza B (C2). La pata larga (+) va a 5 V.
6. **Pegado.** La tira trae adhesivo; refuercen con cinta doble faz. No peguen nada hasta pasar la prueba 3 de la sección 5.

## 4. Conexiones

| Desde | Hacia | Nota |
|---|---|---|
| Fuente 5 V → jack (bornera) | + a la línea roja de la protoboard, − a la azul | Dos hilos de UTP por polo. Medir 5 V con el multímetro antes de conectar nada |
| ESP32 GND | Línea azul (GND común) | El ESP32 se alimenta por USB desde el PC; **no conectar VIN** a la fuente |
| 74AHCT125 pata 14 (VCC) / 7 (GND) | 5 V / GND | Condensador de 100 nF entre las patas 14 y 7 |
| 74AHCT125 pata 1 (1OE) | GND | Activa el canal 1 |
| ESP32 GPIO 16 (RX2) | 74AHCT125 pata 2 (1A) | Datos a 3,3 V |
| 74AHCT125 pata 3 (1Y) | Resistencia 330 Ω → DIN del LED 0 | Datos a 5 V |
| 74AHCT125 patas 4, 10, 13 (2OE, 3OE, 4OE) | 5 V | Canales sin usar, desactivados |
| 74AHCT125 patas 5, 9, 12 (2A, 3A, 4A) | GND | Entradas sin usar, a un nivel fijo |
| ESP32 GPIO 23 | Resistencia 1 kΩ → base del 2N2222A | |
| 2N2222A emisor / colector | GND / pata − del zumbador | Confirmen el orden E-B-C con la hoja de datos de su transistor |
| Zumbador pata + (la más larga, marcada +) | 5 V | Diodo 1N4148 en paralelo con el zumbador: raya (cátodo) hacia 5 V |
| PIR1 (Z7): VCC / OUT / GND | 5 V / GPIO 34 / GND | Puente de disparo en **H** (repetible), tiempo al mínimo, sensibilidad media |
| PIR2 (Z1): VCC / OUT / GND | 5 V / GPIO 35 / GND | Igual que PIR1 |
| B0 Alarma / B7 Reinicio | GPIO 4 / GPIO 14 | La otra pata de cada pulsador va a GND |
| B1–B4 (e2, e3, e4, e6) | GPIO 25, 26, 27, 32 | La otra pata a GND (`INPUT_PULLUP`: pulsado = LOW) |
| B5, B6, B8, B9 (e1, e5, e7, e8) | GPIO 33, 13, 18, 19 | La otra pata a GND |

Los pulsadores van en el panel de control (esquina superior derecha, dos columnas de cinco). Se suelda un hilo de UTP a cada pata y el otro extremo se pincha en la protoboard. Todas las patas de GND del panel se pueden unir entre sí y bajar con un solo hilo.

**Consumo.** Con `BRILLO_GLOBAL 60` (de 255) un LED encendido en un solo color usa unos 60/255 × 20 mA ≈ 4,7 mA, así que los 82 LED en rojo intermitente (`SIN_RUTA`) piden unos 0,4 A. La fuente de 3 A sobra; la prueba P11 de la Fase 4 lo mide.

## 5. Orden de montaje y pruebas por etapas

Cada etapa se prueba antes de pasar a la siguiente. Anoten el resultado y guarden una foto o captura en `docs/evidencias/`.

| # | Etapa | Cómo se comprueba |
|---:|---|---|
| 1 | Placa | Instalar el controlador CH340 y subir `firmware/verificacion_esp32`. El Monitor serie a 115200 muestra `FASE 0 OK - ESP32` |
| 2 | Fuente y protoboard | Sin nada más conectado, el multímetro marca 5 V (±0,25 V) entre las líneas roja y azul, con la polaridad correcta |
| 3 | Pieza A con el 74AHCT125 | En `config.h` poner `#define SIMULACION 0` y subir `evacuacion_esp32`. Tras 60 s, pulsar B0 (puenteando GPIO 4 a GND): e1, e4 y e5 se ven en verde con el punto brillante hacia S1 y S3 |
| 4 | Piezas B y C | Con la alarma, e6 y e7 en verde hacia S2; e8 apagado. Con e6 bloqueado (GPIO 32 a GND), e6 en rojo |
| 5 | Pulsadores | Uno por uno, con el Monitor serie: cada pulsación produce un solo evento JSON con el pasillo correcto en `bloqueos` |
| 6 | PIR | Esperar 60 s de calentamiento. Al mover la mano a 10 cm, `"ocupadas":["Z7"]` (PIR1) o `["Z1"]` (PIR2) |
| 7 | Zumbador | Suena a ritmo lento con la alarma y rápido en `SIN_RUTA` (B5, B6 y B8) |
| 8 | Servidor | Cerrar el Monitor serie y ejecutar `manage.py puente_serial --puerto COMx`. Los eventos llegan al dashboard y aparecen como coincidentes |

Después de la etapa 8 empieza la Fase 4 (plan de pruebas P1–P11 del informe).

## 6. Seguridad

- Nunca conectar el adaptador de 12 V de la tira Foco71 ni ninguna fuente que no sea de 5 V.
- Desconectar la fuente y el USB antes de soldar o recablear.
- Los condensadores electrolíticos tienen polaridad; al revés pueden reventar.
- La fuente de 5 V y el USB del PC comparten GND, pero el 5 V de la fuente no se conecta al ESP32.
- El cautín de 40 W se apoya siempre en su base; el pegamento instantáneo se aplica con la tira desconectada.

## Referencias

Adafruit Industries. (s. f.-a). *Adafruit NeoPixel Überguide: Powering NeoPixels*. https://learn.adafruit.com/adafruit-neopixel-uberguide/powering-neopixels

Adafruit Industries. (s. f.-b). *Level shifting 3.3V microcontrollers and NeoPixels*. https://learn.adafruit.com/neopixel-levelshifter

Jiangsu Huaneng Electronics. (s. f.). *TMB12A05 specification* [Hoja de datos]. LCSC. https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/Jiangsu-Huaneng-Elec-TMB12A05_C96093.pdf

SparkFun Electronics. (s. f.). *How to install CH340 drivers*. https://learn.sparkfun.com/tutorials/how-to-install-ch340-drivers

Texas Instruments. (2002). *SN74LS125A quadruple bus buffers with 3-state outputs* [Hoja de datos]. https://www.ti.com/lit/gpn/SN74LS125A

Texas Instruments. (s. f.). *SN74AHCT125 quadruple bus buffer gates with 3-state outputs* [Hoja de datos]. https://www.ti.com/product/SN74AHCT125

Worldsemi. (2016). *WS2812B intelligent control LED integrated light source* [Hoja de datos]. https://cdn.shopify.com/s/files/1/0174/1800/files/WS2812B-LED-datasheet.pdf
