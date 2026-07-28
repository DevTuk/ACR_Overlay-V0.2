"""Punto de entrada del overlay: compone los módulos y mantiene el estado."""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk

import yaml

from i18n import t

from .controls import OverlayControlsMixin
from .detection import OverlayDetectionMixin
from .editor_integration import OverlayEditorMixin
from .helpers import load_stage_map, resolve_voice
from .lifecycle import OverlayLifecycleMixin
from .settings import OverlaySettingsMixin
from .stages import OverlayStageMixin
from .view import OverlayViewMixin


class Overlay(
    OverlayDetectionMixin,
    OverlayLifecycleMixin,
    OverlayEditorMixin,
    OverlayStageMixin,
    OverlaySettingsMixin,
    OverlayControlsMixin,
    OverlayViewMixin,
):
    """Orquestador del overlay; la implementación vive en módulos específicos."""

    def __init__(self, main_app):
        self.main = main_app
        self.root = main_app.root
        self._closed = False
        self._hotkey_handle = None
        self._hotkey_backend = None
        self._native_hotkey_thread = None
        self._native_hotkey_thread_id = None
        self._native_hotkey_registered = False
        self._native_hotkey_ready = threading.Event()
        self._joystick_hotkey_thread = None
        self._shortcut_listener_stop = threading.Event()
        self._shortcut_error = None
        self._stop_event = threading.Event()
        self._detect_thread = None

        self._ui_queue = queue.SimpleQueue()
        self._ui_after_id = None
        self.visible = False
        self._cur_stage = None
        self._raw_track = None
        self._manual_override = False
        self._drag_x = self._drag_y = 0
        self.collapsed = False
        self._top_after_id = None
        self._settings_dialog = None
        self._settings_area = None
        self._settings_visible = False
        self._settings_height = 238
        self._settings_extra_width = 0
        self._normal_height = 150
        self._settings_save_btn = None
        self._editor = None
        self._editor_open_pending = False
        self._editor_foreground_hwnd = None

        self.overlay_width = int(self.main.config.get("overlay_width", 800))
        self.overlay_width = max(900, min(1400, self.overlay_width))
        self.overlay_alpha = float(self.main.config.get("overlay_alpha", 0.95))
        self.overlay_alpha = max(0.60, min(1.0, self.overlay_alpha))

        self.stage_map = load_stage_map()
        self.available = {
            filename.removesuffix(".yml")
            for filename in os.listdir("pacenotes")
            if filename.endswith(".yml")
        } if os.path.isdir("pacenotes") else set()

        self.voice_dirs = sorted(
            directory
            for directory in os.listdir("voices")
            if os.path.isdir(os.path.join("voices", directory))
        ) if os.path.isdir("voices") else []

        configured_voice = str(self.main.config.get("voice", ""))
        current_voice = resolve_voice(
            configured_voice, self.voice_dirs)
        self.voice_index = (
            self.voice_dirs.index(current_voice)
            if current_voice else 0
        )
        # Evita que la UI muestre la primera carpeta mientras main.py intenta
        # abrir un nombre viejo o inexistente guardado en config.yml.
        if current_voice and current_voice != configured_voice:
            self.main.config["voice"] = current_voice
            with open("config.yml", "w", encoding="utf-8") as config_file:
                yaml.safe_dump(
                    self.main.config, config_file,
                    allow_unicode=True, sort_keys=False)

        # El modo inteligente mantiene el comportamiento histórico. Al
        # desactivarlo, el motor respeta estrictamente la distancia del YAML.
        self.smart_anticipation_var = tk.BooleanVar(
            value=bool(
                self.main.config.get("smart_anticipation", True)))
        configured_timing = max(
            1.1, float(self.main.config.get("call_distance", 1.1)))
        self.dist_var = tk.DoubleVar(value=configured_timing)
        self.main.config["call_distance"] = configured_timing
        self.main.config.setdefault("smart_anticipation", True)
        self.lang = self.main.config.get("lang", "es")
        self._last_track = None

        self._build_window()
        self._register_hotkey()
        self._ui_after_id = self.root.after(40, self._drain_ui_queue)
        self._detect_thread = threading.Thread(
            target=self._detect_loop,
            name="ACR-stage-detection",
            daemon=True,
        )
        self._detect_thread.start()

    def _tr(self, key, **kwargs):
        return t(self.lang, key, **kwargs)
