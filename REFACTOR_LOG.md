# Refactor final del overlay

## Problema encontrado

El refactor anterior había creado una arquitectura paralela (`controller.py`, `renderer.py`, `events_handler.py`) que no contenía toda la funcionalidad del overlay original. La interfaz se reemplazó antes de migrar sus callbacks y comportamientos, por lo que opciones, cierre, inicio y lanzamiento automático quedaron incompletos.

## Solución aplicada

Se tomó el overlay funcional como fuente de comportamiento y se trasladaron sus responsabilidades a mixins especializados. Los métodos funcionales se conservaron, mientras que se eliminaron dos implementaciones legacy sin referencias y la primera construcción visual duplicada que era ocultada inmediatamente.

### Módulos activos

- `app.py`: composición y estado.
- `view.py`: UI y geometría.
- `controls.py`: voz, tiempo y volumen.
- `settings.py`: panel de opciones.
- `stages.py`: mapeo y control manual.
- `editor_integration.py`: editor.
- `detection.py`: shared memory y lanzamiento.
- `lifecycle.py`: callbacks, hotkey, visibilidad y cierre.
- `helpers.py`: funciones puras y adaptadores.

## Limpieza

- Eliminado el conflicto `overlay.py` / `overlay/`.
- Eliminados los módulos experimentales incompletos.
- Eliminados los archivos `*-pre.py` y el backup monolítico de la distribución final.
- Eliminados métodos legacy sin llamadas.
- Eliminada la construcción inicial de cuatro columnas que se ocultaba para volver a construir la misma interfaz como tabla.
- `main.py` fija el directorio de trabajo junto al EXE para encontrar recursos aunque se abra desde un acceso directo.

## Verificaciones realizadas

- Compilación sintáctica de todo el proyecto.
- Importación confirmada desde `overlay.app.Overlay`.
- Paridad de 45 métodos funcionales respecto del overlay original; solo se excluyeron dos métodos legacy no utilizados.
- Prueba de humo de Tkinter:
  - mostrar y ocultar;
  - abrir y cerrar opciones;
  - colapsar y expandir;
  - inicio y detención manual;
  - callbacks reales de `⚙` y `✕`;
  - cierre y destrucción de recursos.


## Corrección de foco del overlay

- Se restauró el mecanismo Win32 comprobado de v0.1.14.
- Se eliminó el subclass de `WndProc` para `WM_MOUSEACTIVATE`.
- Se dejó de aplicar `WS_EX_TOOLWINDOW` y `SWP_FRAMECHANGED`.
- Se quitaron los refuerzos ligados a `<Map>` y `<FocusIn>`.
- El loop de topmost volvió a ejecutar solamente `SetWindowPos` con
  `SWP_NOACTIVATE` cada 1500 ms.
- Se restauró `ttk.Combobox` para la selección manual, evitando un segundo
  `Toplevel` administrado en paralelo.
- La ventana principal vuelve a minimizarse con `root.iconify()`, como en la
  versión funcional de referencia.

La corrección no modifica la lógica de etapas, audio, countdown ni editor.

## Reparación de regresiones de foco y primera largada

- Se descartó el experimento de desacoplar el owner y mostrar mediante
  `SW_SHOWNOACTIVATE`: dentro del juego dejaba el overlay detrás.
- Se restauró literalmente el ciclo de ventana de las versiones funcionales:
  `root.iconify()`, `overlay.deiconify()`, `WS_EX_NOACTIVATE` y TOPMOST.
- El atajo vuelve al backend global `keyboard`; `RegisterHotKey` no recibía
  de forma confiable las combinaciones mientras ACRally capturaba el teclado.
- Se eliminó la espera inicial fija de 15 segundos para abrir shared memory.
- La primera largada acepta el acelerador ya situado al 100 %; después de un
  reinicio continúa exigiendo liberarlo antes de rearmar.
- PortAudio se inicializa una sola vez y de forma sincronizada.
- La apertura del primer stream y las voces de cuenta regresiva tienen
  reintentos; un fallo transitorio ya no termina el hilo del copiloto.
