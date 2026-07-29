# ACRally Pacenote Overlay v0.2.1 — versión modular


[English version](README_EN.md)

Esta versión conserva el comportamiento del overlay funcional, pero elimina el archivo monolítico `overlay.py` como implementación activa.

## Punto de entrada

`main.py` sigue usando una única importación:

```python
from overlay import Overlay
```

El paquete `overlay` expone la clase desde `overlay/app.py`:

```python
from .app import Overlay
```

`Overlay` funciona como el equivalente a `App` en React: compone módulos especializados y mantiene el estado compartido de la instancia.

## Estructura

```text
overlay/
├── __init__.py             Exporta Overlay
├── app.py                  Orquestador y estado de la instancia
├── view.py                 Ventana, barra, tabla principal y geometría
├── controls.py             Voz, adelanto y volumen
├── settings.py             Opciones integradas y guardado
├── stages.py               Mapeo y reproducción manual
├── editor_integration.py   Apertura y posicionamiento del editor
├── detection.py            Detección de ACRally y lanzamiento automático
├── lifecycle.py            Mostrar, ocultar, cerrar, hotkey y topmost
├── helpers.py              Resolución de etapas y volumen de Windows
└── constants.py            Indicadores y mensajes Win32
```

## Conexiones funcionales

- El botón `⚙` ejecuta `OverlaySettingsMixin._open_start_settings`.
- El botón `✕` oculta el overlay y el hotkey puede volver a mostrarlo.
- Al mostrar el overlay, el main se minimiza sin activarse y permanece accesible desde la barra de tareas.
- `close()` destruye ventanas, cancela callbacks y elimina el hotkey.
- La detección automática termina en `_launch()`, que llama a `main.start_stage(stage)`.
- Inicio/detención manual llaman a `main.start_stage()` y `main.stop_stage()`.
- La voz y el adelanto modifican la misma configuración compartida por `Main`.
- `config.yml`, `stage_map.yml`, `voices` y `pacenotes` se leen junto al proyecto o al EXE.

## Adelanto inteligente

El selector **Auto** situado junto a **Adelanto** permite elegir entre dos
comportamientos:

- Activado: compensa la duración completa de la nota, la velocidad del auto
  y el adelanto manual configurado desde `1.1 s`.
- Desactivado (`OFF`): ignora ambas compensaciones y dispara la nota al
  alcanzar la distancia escrita en el YAML, con la pequeña tolerancia propia
  de la frecuencia de lectura de la telemetría.

La selección se guarda inmediatamente como `smart_anticipation` en
`config.yml`. Las configuraciones antiguas que no tengan esa clave conservan
el comportamiento inteligente original.

## Búsqueda de llamadas en el editor

Los campos de llamada filtran el catálogo de la voz seleccionada después de
que transcurre `1 segundo` sin nuevas pulsaciones. Cada tecla reinicia la
espera, evitando que las sugerencias interrumpan la escritura. La búsqueda no
distingue mayúsculas, acentos, espacios, guiones ni guiones bajos, por lo que
`left 4` puede encontrar `Left4`. Al seleccionar un resultado se conserva y
guarda el token interno exacto definido por el WAV o por `dictionary.yml`.
Cuando hay más coincidencias que líneas visibles, la lista conserva todos los
resultados y permite recorrerlos con su barra vertical o la rueda del mouse.

## Overlay sin pérdida de foco

En Windows, el wrapper nativo del overlay usa `WS_EX_NOACTIVATE`. El orden visual se mantiene con `SetWindowPos(..., SWP_NOACTIVATE)`: el overlay no llama a `SetForegroundWindow`, no intenta devolver el foco y no compite con ACRally.

## Atajo configurable

Desde la ventana principal, el botón **CAMBIAR** permite elegir una tecla o combinación de teclado, o detectar un botón/eje de un volante, joystick o gamepad conectado. El valor queda guardado en `config.yml` y se aplica sin reiniciar. Los atajos de teclado usan el backend global `keyboard`, que es el mecanismo compatible con ACRally utilizado por las versiones estables; los controles físicos se leen en segundo plano. Si el dispositivo no está disponible, la aplicación conserva automáticamente el atajo anterior.

Al cerrar el main se detienen la detección, el hotkey, el audio, pygame y las ventanas secundarias. La compilación usa `--onedir`, por lo que la aplicación funciona como un único proceso.

Cuando el overlay está visible, el main no se retira con `withdraw()`: queda minimizado en la barra de tareas mediante `SW_SHOWMINNOACTIVE`. De esta forma sigue siendo posible restaurarlo o cerrarlo desde Windows sin que tome el foco del juego.

## Compilar

1. Copiá las carpetas reales `pacenotes` y `voices` dentro de esta carpeta.
2. Ejecutá `COMPILAR_EXE.bat`.
3. El resultado queda en `ProgramaPacenotesMod`.
4. Conservá la carpeta completa, no solamente el EXE.

El BAT detecta Python 3.13, 3.12, 3.11 o la instalación predeterminada. Crea un entorno de compilación aislado en `.build-venv`.

## Validación rápida

Ejecutá `VALIDAR_PROYECTO.bat`. Comprueba la sintaxis y confirma que la importación activa sea `overlay.app.Overlay`.
