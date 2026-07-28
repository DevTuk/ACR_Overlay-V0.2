# ACRally Pacenote Overlay — Modular Version

[Versión en español](README.md)

This version preserves the behavior of the working overlay while removing the monolithic `overlay.py` file as the active implementation.

## Entry Point

`main.py` continues to use a single import:

```python
from overlay import Overlay
```

The `overlay` package exposes the class from `overlay/app.py`:

```python
from .app import Overlay
```

`Overlay` works as the equivalent of `App` in React: it composes specialized modules and maintains the shared state of the instance.

## Project Structure

```text
overlay/
├── __init__.py             Exports Overlay
├── app.py                  Instance orchestrator and shared state
├── view.py                 Window, title bar, main table, and geometry
├── controls.py             Voice, pacenote timing, and volume
├── settings.py             Integrated settings and persistence
├── stages.py               Stage mapping and manual playback
├── editor_integration.py   Editor opening and positioning
├── detection.py            ACRally detection and automatic launch
├── lifecycle.py            Show, hide, close, hotkey, and topmost behavior
├── helpers.py              Stage resolution and Windows volume helpers
└── constants.py            Hotkey and Win32 indicator constants
```

## Functional Connections

- The `⚙` button calls `OverlaySettingsMixin._open_start_settings`.
- The `✕` button hides the overlay, and the hotkey can display it again.
- When the overlay is shown, the main window is minimized without activation and remains accessible from the Windows taskbar.
- `close()` destroys windows, cancels scheduled callbacks, and unregisters the hotkey.
- Automatic detection ends in `_launch()`, which calls `main.start_stage(stage)`.
- Manual start and stop actions call `main.start_stage()` and `main.stop_stage()`.
- Voice and pacenote timing controls update the same configuration shared by `Main`.
- `config.yml`, `stage_map.yml`, `voices`, and `pacenotes` are loaded from the project directory or from the folder next to the compiled executable.

## Smart Anticipation

The **Smart** selector next to **Timing** provides two behaviors:

- Enabled: compensates for the complete pacenote duration, vehicle speed,
  and the configurable manual timing value starting at `1.1 s`.
- Disabled (`OFF`): ignores both compensations and triggers the pacenote when
  the odometer reaches the distance stored in the YAML, within the small
  tolerance introduced by the telemetry polling interval.

The selection is immediately stored as `smart_anticipation` in `config.yml`.
Older configurations without this key keep the original smart behavior.

## Non-Activating Floating Overlay

On Windows, the overlay uses the same focus path as the stable pre-refactor versions: Tk show/hide plus `WS_EX_NOACTIVATE` and `SetWindowPos(..., SWP_NOACTIVATE)`. The overlay never calls `SetForegroundWindow`. Keyboard shortcuts use the global `keyboard` backend because ACRally can consume combinations before `RegisterHotKey` receives them.

The manual stage selector is a custom popup that remains above the overlay and is also non-activating. It closes after selecting a stage, pressing its button again, hiding the overlay, or clicking anywhere outside it, including inside the game.

Closing the main window stops detection, unregisters the hotkey, releases audio and pygame, and destroys secondary windows. The executable is built with `--onedir`, so the application runs as a single process.

While the overlay is visible, the main window is no longer removed with `withdraw()`. It is minimized to the Windows taskbar through `SW_SHOWMINNOACTIVE`, so it can still be restored or closed without taking focus away from the game.

## Building the Executable

1. Copy the real `pacenotes` and `voices` folders into this project directory.
2. Run `COMPILAR_EXE.bat`.
3. The compiled application will be created inside `ProgramaPacenotesMod`.
4. Keep the entire generated folder, not only the `.exe` file.

The BAT file detects Python 3.13, 3.12, 3.11, or the default Python installation. It creates an isolated build environment in `.build-venv`.

## Quick Validation

Run `VALIDAR_PROYECTO.bat`. It checks the Python syntax and confirms that the active import resolves to `overlay.app.Overlay`.
