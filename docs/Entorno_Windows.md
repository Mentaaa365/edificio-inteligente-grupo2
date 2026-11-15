# Entorno en Windows y repositorio privado

## 1. Python 3.13 y entorno virtual

1. Instala [Python para Windows](https://www.python.org/downloads/windows/) y selecciona una versión de la serie **3.13**.
2. Abre PowerShell dentro de `edificio-inteligente-grupo2` y ejecuta:

   ```powershell
   py -3.13 --version
   py -3.13 -m venv .venv
   .\.venv\Scripts\python.exe -c "import sys; print(sys.version); print('Entorno virtual activo:', sys.prefix != sys.base_prefix)"
   .\.venv\Scripts\python.exe -m pip --version
   ```

3. Comprueba que sale `Entorno virtual activo: True` y que `pip` apunta a `.venv`. En PyCharm puedes seleccionar `.venv\Scripts\python.exe` como intérprete del proyecto.

## 2. Arduino IDE 2.x y ESP32

1. Instala [Arduino IDE 2.x](https://www.arduino.cc/en/software).
2. En **Archivo → Preferencias → URLs adicionales para el Gestor de tarjetas**, añade el índice estable oficial:

   ```text
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```

3. En el **Gestor de tarjetas**, busca **esp32 by Espressif Systems** e instala una versión estable de la serie **3.3.x**. Anota la versión exacta para que los tres usen la misma.
4. Abre `firmware/verificacion_esp32/verificacion_esp32.ino`, selecciona **ESP32 Dev Module** para el ESP32 clásico del pedido y pulsa **Verificar**. Guarda la salida de compilación como evidencia.
5. Cuando reciban la placa, conéctala con su cable USB de datos, elige el puerto COM que aparece, pulsa **Subir** y abre el **Monitor serie** a **115200 baudios**. Debe mostrarse `FASE 0 OK - ESP32` una vez por segundo.

## 3. Trabajar con el repositorio privado

El repositorio ya está creado en [Mentaaa365/edificio-inteligente-grupo2](https://github.com/Mentaaa365/edificio-inteligente-grupo2).

1. Abre Git Bash en la carpeta donde guardarás el proyecto y ejecuta:

   ```bash
   git clone https://github.com/Mentaaa365/edificio-inteligente-grupo2.git
   cd edificio-inteligente-grupo2
   git status
   ```

2. Comprueba que estás en la rama `main`. El propietario puede agregar a sus dos compañeros desde **Settings → Collaborators** con sus usuarios exactos. Cada uno puede clonar el repositorio después de aceptar la invitación.
3. Para los siguientes commits, cada integrante configura su nombre y correo en su copia local. Usen el correo de GitHub que prefieran asociar con sus aportes.
