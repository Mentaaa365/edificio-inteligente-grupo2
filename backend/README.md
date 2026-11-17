# Servidor y dashboard (Fase 3)

Aplicación Django 5.2 que recibe los eventos del ESP32, recalcula las rutas con el mismo `simulacion/modelo.py` de la Fase 1, guarda el histórico en SQLite y los muestra en un dashboard que se actualiza en tiempo real por WebSocket (Django Channels).

Explicación completa del diseño: [docs/Fase_3.md](../docs/Fase_3.md).

## Ejecutarlo en Windows

Todo se hace en PowerShell desde la carpeta raíz `edificio-inteligente-grupo2`.

### 1. Entorno virtual e instalación (una sola vez)

Si todavía no tienes el `.venv` de la [guía de Windows](../docs/Entorno_Windows.md):

```powershell
py -3.13 -m venv .venv
```

Instala las dependencias del servidor (incluyen NetworkX, que necesita `modelo.py`):

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

> **Si pip falla con `SSLCertVerificationError`:** la red tiene un filtro web que intercepta `files.pythonhosted.org`. No desactives la verificación. Conéctate a otra red (por ejemplo, el celular) y vacía la caché DNS con `ipconfig /flushdns` antes de reintentar.

### 2. Archivo `.env` (una sola vez)

```powershell
Copy-Item backend\.env.example backend\.env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(50))"
```

Abre `backend\.env` y pega la clave generada en `SECRET_KEY=`. El `.env` no se sube a git.

### 3. Base de datos (una sola vez, y cada vez que cambien los modelos)

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py migrate
```

Esto crea `backend\db.sqlite3` con las tablas y los escenarios S0–S7.

### 4. Arrancar el servidor

```powershell
..\.venv\Scripts\python.exe manage.py runserver
```

Abre <http://127.0.0.1:8000/>. Al cargar el dashboard, la consola del servidor muestra `WebSocket CONNECT /ws/dashboard/` y la esquina superior derecha de la página dice **Tiempo real · WebSocket**. Si dice **Sondeo cada 1 s**, el WebSocket no conectó y el navegador consulta la API cada segundo.

### 5. Probar sin hardware

En **otra** terminal, también dentro de `backend`:

```powershell
..\.venv\Scripts\python.exe manage.py simular_esp32
..\.venv\Scripts\python.exe manage.py simular_esp32 --eventos 0 --intervalo 2 --discrepancia 0.1
```

| Opción | Uso |
|---|---|
| `--eventos N` | Cuántos eventos enviar (`0` = sin fin, se para con Ctrl+C) |
| `--intervalo S` | Segundos entre eventos |
| `--discrepancia P` | Probabilidad de enviar una ruta alterada para ver la alerta "NO coinciden" |
| `--semilla N` | Repite exactamente la misma secuencia |
| `--url` | Otro servidor (por defecto `http://127.0.0.1:8000`) |

### 6. Pruebas automáticas

```powershell
..\.venv\Scripts\python.exe manage.py test rutas
```

### 7. Panel de administración (opcional)

```powershell
..\.venv\Scripts\python.exe manage.py createsuperuser
```

Luego entra en <http://127.0.0.1:8000/admin/>.

## Conectar la maqueta real por USB (puente serie)

El firmware actual solo imprime el JSON por el puerto serie. El comando `puente_serial` lee ese puerto y reenvía cada línea al servidor, así la maqueta aparece en el dashboard **sin cambiar el firmware**.

1. Carga el firmware en el ESP32 con Arduino IDE. Para la maqueta real pon `SIMULACION 0` en `config.h` (ver [Fase 1](../docs/Fase_1.md), sección 4).
2. Conecta el ESP32 a la PC con un cable USB **de datos**.
3. **Cierra el Monitor serie de Arduino IDE**, o cierra Arduino IDE entero. Un puerto COM solo lo puede usar un programa a la vez.
4. Terminal 1, dentro de `backend`, arranca el servidor:

   ```powershell
   ..\.venv\Scripts\python.exe manage.py runserver
   ```

5. Terminal 2, dentro de `backend`, busca el puerto del ESP32:

   ```powershell
   ..\.venv\Scripts\python.exe manage.py puente_serial --listar
   ```

   Suele aparecer como `COM5   Silicon Labs CP210x USB to UART Bridge` o `USB-SERIAL CH340`. Si no aparece nada, prueba otro cable (algunos solo cargan) o instala el controlador CP210x o CH340, según el chip de la placa.

6. Arranca el puente con ese puerto:

   ```powershell
   ..\.venv\Scripts\python.exe manage.py puente_serial --puerto COM5
   ```

   Debe decir `Conectado a COM5. Esperando eventos de la maqueta...`. El puente no reinicia la placa al conectarse: si ya había bloqueos, se mantienen.

7. Abre <http://127.0.0.1:8000/> y usa la maqueta (B0, pulsadores de bloqueo, PIR). Cada evento aparece en la terminal 2 con `coincide` o `NO coincide`, y en el dashboard con origen `esp32`.

Qué muestra la terminal 2:

| Línea | Significa |
|---|---|
| `[ESP32] Grupo 2 - Edificio inteligente...` | Texto del ESP32 que no es un evento: se muestra pero no se envía |
| `B4    RUTA_ACTIVA  bloqueos=e6 -> #12 coincide` | Evento reenviado y guardado. La maqueta calcula igual que el modelo |
| `NO coincide: Z3: ruta ...` | La placa y `modelo.py` dieron rutas distintas. Revisa que `grafo.h` esté regenerado desde `grafo.json` |
| `no se pudo conectar con ...` | El servidor no está arrancado. El puente sigue leyendo; ese evento se pierde |
| `No se pudo abrir COM5 ... Reintento en 2 s` | Puerto equivocado, cable suelto o Monitor serie abierto. Se reconecta solo |

Para parar el puente: **Ctrl+C**. Para volver a usar el Monitor serie, primero para el puente.

## Para que el ESP32 llegue al servidor por WiFi (Fase 4)

1. Busca la IP del PC con `ipconfig` (por ejemplo, `192.168.1.50`).
2. Añádela en `ALLOWED_HOSTS` del `.env` y pon una clave en `API_TOKEN`.
3. Arranca el servidor escuchando en la red local:

   ```powershell
   ..\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
   ```

   Windows pedirá permiso en el firewall: acepta solo para redes **privadas**.
4. El ESP32 hace `POST http://192.168.1.50:8000/api/eventos/` con la misma línea JSON que imprime por serie y la cabecera `X-Token`.

## API

| Método y ruta | Quién la usa | Qué hace |
|---|---|---|
| `POST /api/eventos/` | ESP32 | Guarda el evento, recalcula con `modelo.py` y responde `{"id", "coincide", "diferencias", "estado_modelo"}` |
| `GET /api/comandos/` | ESP32 | Entrega los escenarios pendientes y los marca como enviados |
| `GET /api/escenarios/` | Dashboard | Lista de escenarios |
| `POST /api/escenarios/<id>/ejecutar/` | Dashboard | Calcula la ruta del escenario y lo deja pendiente para el ESP32 |
| `GET /api/historico/` | Dashboard | Eventos guardados. Filtros: `desde`, `hasta`, `estado`, `evento`, `coincide=si/no`, `origen`, `despues_de`, `limite` |
| `GET /api/grafo/` | Dashboard | Nodos y aristas de `grafo.json` para dibujar el plano |
| `POST /api/simular/` | Dashboard | Calcula sin guardar con `{"bloqueos", "ocupadas", "alfa_pct", "beta_pct"}` |
| `ws://…/ws/dashboard/` | Dashboard | Mensajes `evento` y `escenario` en tiempo real |

Ejemplo desde PowerShell:

```powershell
$cuerpo = '{"ms":3001,"evento":"B4","estado":"RUTA_ACTIVA","bloqueos":["e6"],"ocupadas":[],"calculo_us":700,"explorados":16,"aisladas":0,"rutas":{"Z1":{"costo_m":11.00,"ruta":"Z1>C1>S1"},"Z2":{"costo_m":11.00,"ruta":"Z2>C1>S1"},"Z3":{"costo_m":30.50,"ruta":"Z3>C2>C1>S1"},"Z4":{"costo_m":23.00,"ruta":"Z4>C3>C4>S3"},"Z5":{"costo_m":23.00,"ruta":"Z5>C3>C4>S3"},"Z6":{"costo_m":11.00,"ruta":"Z6>C4>S3"},"Z7":{"costo_m":15.00,"ruta":"Z7>C5>S2"},"Z8":{"costo_m":11.00,"ruta":"Z8>C4>S3"}}}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/eventos/ -ContentType "application/json" -Body $cuerpo
```

## Archivos

| Archivo | Contenido |
|---|---|
| `edificio/settings.py` | Configuración: lee `.env`, SQLite, Channels |
| `edificio/asgi.py` | Reparte HTTP → vistas y WebSocket → consumidor |
| `rutas/motor.py` | Puente a `simulacion/modelo.py`: calcular, formato del ESP32, comparar |
| `rutas/models.py` | `Escenario`, `Evento`, `RutaCalculada`, `Medicion` |
| `rutas/servicios.py` | Validar, calcular, guardar y avisar |
| `rutas/views.py`, `rutas/urls.py` | API HTTP |
| `rutas/consumers.py`, `rutas/routing.py`, `rutas/difusion.py` | WebSocket |
| `rutas/templates/rutas/dashboard.html`, `rutas/static/rutas/` | Dashboard |
| `rutas/management/commands/simular_esp32.py` | ESP32 simulado |
| `rutas/management/commands/puente_serial.py` | Puente USB: ESP32 real → servidor |
| `rutas/cliente_http.py` | Envío de un evento por HTTP (lo usan los dos comandos) |
| `rutas/migrations/0002_escenarios_fase1.py` | Crea los escenarios S0–S7 |
| `rutas/tests/` | Pruebas del cálculo, de la API y del WebSocket |
