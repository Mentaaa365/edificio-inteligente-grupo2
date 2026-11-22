# Fase 3. Servidor y dashboard

**Grupo 2 · Modelos y Simulación · UNEMI**

En esta fase se añade un servidor en la PC. Recibe las líneas JSON que el ESP32 imprime por serie, vuelve a calcular las rutas con el mismo modelo de Python de la Fase 1, guarda todo en una base de datos y lo muestra en un dashboard web que se actualiza en tiempo real. Sigue sin hacer falta hardware: un comando simula al ESP32.

| Entregable | Archivo | Estado |
|---|---|---|
| Aplicación Django 5.2 con SQLite y `.env` | [`backend/`](../backend) | Hecho |
| API para el ESP32 y para el dashboard | [`backend/rutas/views.py`](../backend/rutas/views.py) | Hecho, con pruebas |
| Dashboard con plano SVG, alertas, histórico, gráficas y simulador | [`backend/rutas/templates/rutas/dashboard.html`](../backend/rutas/templates/rutas/dashboard.html) y [`static/rutas/`](../backend/rutas/static/rutas) | Hecho y revisado en el navegador |
| Tiempo real con Django Channels (WebSocket) y sondeo de respaldo | [`backend/rutas/consumers.py`](../backend/rutas/consumers.py) | Hecho, con pruebas |
| ESP32 simulado | [`backend/rutas/management/commands/simular_esp32.py`](../backend/rutas/management/commands/simular_esp32.py) | Hecho |
| Puente USB para la maqueta real | [`backend/rutas/management/commands/puente_serial.py`](../backend/rutas/management/commands/puente_serial.py) | Hecho y probado con un puerto simulado; falta probarlo con la placa |
| Pruebas automáticas | [`backend/rutas/tests/`](../backend/rutas/tests) | 50 de 50 pasan |
| Guía de instalación en Windows | [`backend/README.md`](../backend/README.md) | Hecho |

## 1. Arquitectura

```
 ESP32 por USB + puente_serial               Servidor Django (Daphne, ASGI)                        Navegador
 ───────────────────────   POST /api/eventos/  ┌─────────────────────────────────────┐   WebSocket   ┌──────────────┐
 línea JSON de informar() ───────────────────▶ │ views.py   valida la petición        │ ────────────▶ │ dashboard.js │
                                                │ servicios  guarda y compara          │  /ws/dashboard│  plano SVG   │
 GET /api/comandos/  ◀───────────────────────── │ motor.py ─▶ simulacion/modelo.py     │               │  Chart.js    │
 (escenarios pendientes)                        │            modelo/grafo.json         │ ◀──────────── │  simulador   │
                                                │ SQLite: Evento, RutaCalculada, ...   │  API HTTP     └──────────────┘
                                                └─────────────────────────────────────┘
```

**No se duplica el modelo.** [`rutas/motor.py`](../backend/rutas/motor.py) añade la carpeta `simulacion/` a la ruta de Python e importa `modelo.py`. Usa `cargar`, `calcular_campo`, `pesos` (a través de `calcular_campo`), `estado` y `longitud_real_m`, todos sin cambios. Como `modelo.py` ya se verificó contra el firmware en las 65 536 combinaciones (Fase 1, sección 5), el servidor y el ESP32 calculan lo mismo. Si cambia `grafo.json`, el servidor lo toma al reiniciarse. No se modificó nada en `firmware/`, `modelo/` ni `simulacion/`.

`motor.py` solo añade tres cosas:

1. **Formato del ESP32.** `costo_esp32()` imita a `imprimirMetros()`: metros con dos decimales truncados. Las rutas se escriben como `"Z3>C2>C5>S2"` y las zonas aisladas como `null`.
2. **Comparación.** `comparar()` revisa las rutas, los costos, las zonas aisladas y los nodos explorados. El estado solo se compara en emergencia, porque sin alarma el firmware informa `NORMAL` aunque tenga las rutas calculadas.
3. **Datos para el plano.** Para cada zona: aristas de la ruta, sentido de evacuación, metros reales, tiempo y salida. También las aristas aisladas, con la misma regla que `pintar()`: los dos extremos tienen costo infinito.

**¿Dos decimales bastan?** Sí. Con los parámetros del firmware (α = 0,5, β = 1, riesgo 50 %), cada arista cuesta d, 1,5·d o 2,25·d metros, con d entero. Por tanto todo costo es múltiplo de 0,25 m y el truncado no pierde información. Una prueba lo comprueba en las 256 × 4 combinaciones de bloqueos y PIR.

## 2. Base de datos (SQLite)

| Modelo | Una fila por… | Campos principales |
|---|---|---|
| `Escenario` | Condición preparada | `nombre`, `bloqueos`, `ocupadas`, `alarma`, `alfa_pct`, `beta_pct`, `estado_envio` (inactivo / pendiente / enviado) |
| `Evento` | Línea JSON recibida del ESP32 | Los nueve campos del firmware, más `json_original`, `recibido` y `origen` (esp32 o simulador) |
| `RutaCalculada` | Cálculo del servidor (de un evento o de un escenario) | `estado`, `explorados`, `aisladas`, `resultado` (JSON completo), `calculo_us`, `coincide_esp32`, `diferencias` |
| `Medicion` | Zona de cada cálculo | `zona`, `costo_m`, `longitud_m`, `tiempo_s`, `salida` |

La migración `0002_escenarios_fase1.py` crea los escenarios S0–S7 de la Fase 1. `Medicion` permite filtrar y graficar sin abrir el JSON. Por ejemplo, para saber cuántas veces el Laboratorio salió por S1 basta con `Medicion.objects.filter(zona="Z3", salida="S1").count()`.

## 3. API

| Método y ruta | Uso | Respuesta |
|---|---|---|
| `POST /api/eventos/` | El ESP32 envía su línea JSON | `201` con `id`, `coincide`, `diferencias`; `400` si el formato no es el del firmware; `401` si el token no coincide |
| `GET /api/comandos/` | El ESP32 consulta escenarios pendientes | Lista de escenarios; cada uno se entrega una sola vez |
| `POST /api/escenarios/<id>/ejecutar/` | Botón «Ejecutar» del dashboard | Ruta calculada; el escenario queda pendiente |
| `GET /api/historico/` | Tabla y gráficas | Filtros `desde`, `hasta`, `estado`, `evento`, `coincide`, `origen`, `despues_de`, `limite` |
| `GET /api/escenarios/`, `GET /api/grafo/`, `POST /api/simular/` | Dashboard | Lista, grafo y cálculo sin guardar |

**Seguridad básica.**
- El ESP32 no puede usar cookies, así que `eventos` y `comandos` están exentos de CSRF. En su lugar, si `API_TOKEN` del `.env` tiene valor, exigen la cabecera `X-Token`, que se compara con `hmac.compare_digest`.
- `ejecutar` cambia datos y solo lo usa el dashboard, así que conserva la protección CSRF de Django: el JS envía la cookie `csrftoken` en la cabecera `X-CSRFToken`.
- El WebSocket solo acepta conexiones cuyo `Origin` esté en `ALLOWED_HOSTS` (`AllowedHostsOriginValidator`).

**El ESP32 todavía no consulta comandos.** El firmware actual solo imprime por serie. Enviar por WiFi y consultar `/api/comandos/` es trabajo de la Fase 4. Por eso el servidor ya expone esos endpoints, pero no se tocó el firmware. Mientras tanto, la maqueta se conecta con el puente USB de la sección 5.

## 4. Dashboard

Una sola página en <http://127.0.0.1:8000/>:

| Sección | Qué muestra |
|---|---|
| Estado actual | Estado del ESP32, último evento, bloqueos, zonas ocupadas, tiempo de cálculo del ESP32 y del servidor, y si coinciden |
| Alertas | `SIN_RUTA` (crítica), `RUTA_PARCIAL` con las zonas aisladas, alarma, reinicio y discrepancias ESP32 ≠ modelo |
| Plano en vivo | SVG dibujado desde `grafo.json`: verde = ruta (con flecha hacia la salida), rojo = bloqueado, ámbar intermitente = aislado, morado = zona ocupada. Debajo, la tabla de rutas por zona |
| Escenarios | S0–S7 con el botón «Ejecutar» |
| Gráficas (Chart.js) | Tiempo de cálculo del ESP32 frente al servidor; recorrido medio y máximo; zonas aisladas por evento |
| Simulador | Casillas para e1–e8 y Z1–Z8 y deslizadores de α y β. Recalcula en cuanto cambias algo |
| Histórico | Tabla filtrable por fechas, estado, evento y coincidencia |

**Tiempo real.**
- Al abrir la página, el navegador se conecta a `ws://…/ws/dashboard/`.
- Cada evento guardado se difunde al grupo `dashboard` con `transaction.on_commit`, para que solo se avise de lo que ya está en la base de datos.
- Si el WebSocket se cae, el navegador pasa solo a **sondeo cada segundo** (`/api/historico/?despues_de=<último id>`) y reintenta el WebSocket cada 5 s. La esquina superior derecha indica qué modo está activo.
- Channels se instaló sin problemas en Windows, así que el sondeo quedó como respaldo y no como solución principal. Se usa `InMemoryChannelLayer`, que no necesita Redis, con una limitación: solo funciona con un único proceso de servidor, que es suficiente para la maqueta.

## 5. Cómo ejecutarlo

Los pasos detallados para Windows están en [`backend/README.md`](../backend/README.md). En resumen, desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env      # y poner una SECRET_KEY propia
cd backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py runserver
```

En otra terminal, dentro de `backend`:

```powershell
..\.venv\Scripts\python.exe manage.py simular_esp32 --eventos 30 --intervalo 1 --discrepancia 0.1
..\.venv\Scripts\python.exe manage.py test rutas
```

`simular_esp32` imita el `loop()` del firmware. Guarda la alarma, los bloqueos y las zonas ocupadas, pulsa botones al azar (B0, B1–B9, B7, PIR1, PIR2) y envía por HTTP la misma línea que `informar()`. Con `--discrepancia` altera a propósito algunas rutas para ver la alerta.

### Maqueta real por USB

Mientras el firmware no tenga WiFi, la placa se conecta con `puente_serial`:

```
Maqueta (ESP32) ──USB──▶ COM5 ──▶ puente_serial ──HTTP──▶ POST /api/eventos/ ──WebSocket──▶ dashboard
```

```powershell
..\.venv\Scripts\python.exe manage.py puente_serial --listar
..\.venv\Scripts\python.exe manage.py puente_serial --puerto COM5
```

- **Lectura por trozos.** El puerto entrega bytes en trozos de cualquier tamaño. `separar_lineas()` guarda lo incompleto hasta que llega el fin de línea, para no partir un JSON en dos.
- **Solo se envían eventos.** `extraer_json()` reenvía solo las líneas que son un JSON con el campo `evento`. Los mensajes de arranque del ESP32 y el saludo del firmware se muestran pero no se envían.
- **No reinicia la placa.** En el ESP32 DevKit, las señales DTR y RTS del USB reinician la placa; se dejan apagadas al abrir el puerto.
- **Pasa por la API.** Los eventos usan el mismo `POST /api/eventos/` que usará el ESP32 por WiFi. Así se valida, se compara y se avisa al dashboard igual que en la Fase 4.
- **Se recupera solo.** Si se desconecta el cable, reintenta cada 2 s. Si el servidor está apagado, informa del evento perdido y sigue leyendo.
- **Monitor serie cerrado.** El Monitor serie de Arduino debe estar cerrado: un puerto COM no se puede abrir dos veces.

Los pasos para el integrante que tiene la maqueta están en [`backend/README.md`](../backend/README.md), sección «Conectar la maqueta real por USB».

### Exportar el histórico y calcular las métricas

El dashboard guarda cada evento en SQLite. Para las métricas del informe (sección de resultados):

```powershell
# 1. En backend\, con el servidor detenido o en marcha (no importa):
..\.venv\Scripts\python.exe manage.py exportar_historico --origen esp32
#    -> datos\experimentos.csv  (una fila por evento: estado, bloqueos, PIR, calculo_us, coincide, ruta de cada zona)

# 2. En la raíz del repositorio:
.\.venv\Scripts\python.exe -m pip install -r simulacion\requirements.txt
.\.venv\Scripts\python.exe simulacion\analisis_experimentos.py
#    -> simulacion\resultados\metricas_esp32.csv   (n, media, desviación, mínimo, P95, máximo por nº de bloqueos)
#    -> simulacion\resultados\fig5_calculo_esp32.png (diagrama de caja)
```

- El evento `LISTO` se excluye por defecto: es el cálculo del arranque, no lo provoca ningún pulsador (`--incluir-listo` lo cuenta).
- La desviación es la muestral (n − 1). Con menos de 2 eventos en un grupo se informa 0.
- `datos/experimentos.csv` sí se versiona y va en el RAR: son los datos crudos de las pruebas.

## 6. Verificación

| Comprobación | Resultado al 17 de noviembre de 2026 |
|---|---|
| Escenarios S0–S7 de la Fase 1 (estado, zonas aisladas, recorrido medio y máximo) | 8 de 8 iguales a la tabla de la sección 3 de la Fase 1 |
| Valores medidos en Wokwi: Laboratorio a S1 con 30,50 m al bloquear e6; Laboratorio de S2 (19 m) a S1 (23 m) con PIR1 | Iguales |
| Umbral de α con el Auditorio ocupado | El Laboratorio sale por S2 con α = 0,20 y por S1 con α = 0,30, coherente con el umbral 0,25 de la Fase 1 |
| Costos múltiplos de 0,25 m (2 decimales bastan) | Cierto en las 1 024 combinaciones probadas |
| Línea JSON con el formato exacto de `informar()` | Aceptada y marcada como coincidente |
| API: validación, token, CSRF, comandos entregados una sola vez, filtros del histórico | Pasan (`manage.py test rutas`) |
| Puente USB con un puerto simulado: mensajes de arranque, saludo, 4 eventos con el formato exacto de `informar()` partidos en trozos de 64 bytes | Los 4 eventos llegan por HTTP al servidor de pruebas, se guardan con origen `esp32` y coinciden; el texto que no es JSON se ignora; con el servidor caído sigue leyendo |
| `puente_serial --listar` y un puerto inexistente en este PC | Lista vacía con aviso; reintenta cada 2 s con un mensaje claro |
| WebSocket: un evento y un escenario llegan al navegador; se rechaza un `Origin` ajeno | Pasan |
| Dashboard en el navegador con `simular_esp32` (15 eventos, 15 % de discrepancias) | Plano, tabla, alertas, gráficas e histórico se actualizan por WebSocket; las 2 discrepancias inyectadas aparecen como alerta |
| Sondeo de respaldo | Con el WebSocket cerrado a propósito, los 3 eventos siguientes llegaron por sondeo; luego se volvió a conectar |
| Ancho de celular (375 px) | Sin desplazamiento horizontal de la página |
| `puente_serial` con la maqueta física: PIR1, PIR2 y pulsadores B0–B7 | Los eventos llegan al dashboard y el servidor informa «coincide». 41 líneas registradas iguales al modelo; cálculo en el ESP32: media 55,5 µs sin bloqueos (n = 20) y 29 µs con 6 bloqueos |
| `exportar_historico` (eventos con y sin zonas aisladas) | Pasa (50 de 50 pruebas en total) |

**No comprobado todavía:**
- Envío desde un ESP32 real o desde Wokwi por WiFi (Fase 4).
- Varias pestañas abiertas durante horas.
- El servidor en otro PC de la red local.
- Las gráficas sin internet: Chart.js se carga desde un CDN, y sin conexión el resto del dashboard funciona pero las gráficas no aparecen.

## 7. Qué falta para cerrar la Fase 3

1. Ejecutar los pasos de `backend/README.md` en el equipo de cada integrante, y en el que tiene la maqueta conectarla con `puente_serial`. Guardar en `docs/evidencias/` una captura del dashboard y de la terminal del puente.
2. Decidir si se guarda Chart.js dentro del proyecto para que funcione sin internet el día de la presentación.
3. Estudio del código por los tres. Cada integrante debe poder explicar:
   - Por qué el servidor importa `modelo.py` en lugar de copiar el algoritmo.
   - Qué compara `comparar()` y por qué ignora `NORMAL`.
   - Qué hace cada modelo de datos.
   - La diferencia entre WebSocket y sondeo.
   - Por qué `eventos` usa token y `ejecutar` usa CSRF.

   Y hacer en vivo un cambio como añadir un escenario desde `/admin/` y ejecutarlo, o añadir un filtro al histórico.

## Referencias

Chart.js. (s. f.). *Installation*. Chart.js documentation. https://www.chartjs.org/docs/latest/getting-started/installation.html

Django Software Foundation. (s. f.-a). *Database transactions: Performing actions after commit*. Django 5.2 documentation. https://docs.djangoproject.com/en/5.2/topics/db/transactions/

Django Software Foundation. (s. f.-b). *Databases: SQLite notes*. Django 5.2 documentation. https://docs.djangoproject.com/en/5.2/ref/databases/

Django Software Foundation. (s. f.-c). *How to use Django's CSRF protection*. Django 5.2 documentation. https://docs.djangoproject.com/en/5.2/howto/csrf/

Django Software Foundation. (s. f.-d). *How to create custom django-admin commands*. Django 5.2 documentation. https://docs.djangoproject.com/en/5.2/howto/custom-management-commands/

Django Software Foundation. (s. f.-e). *Migrations: Data migrations*. Django 5.2 documentation. https://docs.djangoproject.com/en/5.2/topics/migrations/

Django Software Foundation. (s. f.-f). *Models*. Django 5.2 documentation. https://docs.djangoproject.com/en/5.2/topics/db/models/

Django Software Foundation. (s. f.-g). *Django settings*. Django 5.2 documentation. https://docs.djangoproject.com/en/5.2/topics/settings/

Django Software Foundation. (s. f.-h). *Testing tools*. Django 5.2 documentation. https://docs.djangoproject.com/en/5.2/topics/testing/tools/

Django Software Foundation. (s. f.-i). *Writing views*. Django 5.2 documentation. https://docs.djangoproject.com/en/5.2/topics/http/views/

pySerial. (s. f.). *pySerial API*. https://pyserial.readthedocs.io/en/latest/pyserial_api.html

Django Channels. (s. f.-a). *Installation*. Channels documentation. https://channels.readthedocs.io/en/stable/installation.html

Django Channels. (s. f.-b). *Tutorial part 2: Implement a chat server*. Channels documentation. https://channels.readthedocs.io/en/stable/tutorial/part_2.html

Django Channels. (s. f.-c). *Consumers*. Channels documentation. https://channels.readthedocs.io/en/stable/topics/consumers.html

Django Channels. (s. f.-d). *Channel layers*. Channels documentation. https://channels.readthedocs.io/en/stable/topics/channel_layers.html

Django Channels. (s. f.-e). *Security*. Channels documentation. https://channels.readthedocs.io/en/stable/topics/security.html

Django Channels. (s. f.-f). *Testing*. Channels documentation. https://channels.readthedocs.io/en/stable/topics/testing.html

django-environ. (s. f.). *django-environ documentation*. https://django-environ.readthedocs.io/en/latest/
