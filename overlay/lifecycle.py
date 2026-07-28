"""Ciclo de vida, hotkey y ventana flotante del overlay.

El manejo nativo replica el comportamiento probado de v0.1.14: el Toplevel
usa únicamente ``WS_EX_NOACTIVATE`` y se mantiene arriba mediante
``SetWindowPos(..., SWP_NOACTIVATE)``. No se subclasifica el WndProc, no se
reordena el marco en cada evento de mapa y nunca se fuerza el foreground.
"""

from __future__ import annotations

import ctypes
import os
import queue
import threading
import tkinter as tk
import keyboard

from ui_theme import BG2, BORDER, FG, PAD_MD, PAD_SM

from shortcut import (
    joystick_input_active, normalize_shortcut, resolve_joystick_device,
)

from .constants import (
    GWL_EXSTYLE,
    HWND_TOPMOST,
    SWP_NOACTIVATE,
    SWP_NOMOVE,
    SWP_NOSIZE,
    WS_EX_NOACTIVATE,
)


class OverlayLifecycleMixin:
    # ───────────────────────── Cola de interfaz ─────────────────────────

    def _post_ui(self, callback, *args):
        if not self._closed:
            self._ui_queue.put((callback, args))

    def _drain_ui_queue(self):
        self._ui_after_id = None
        if self._closed:
            return
        while True:
            try:
                callback, args = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback(*args)
            except (tk.TclError, RuntimeError):
                pass
        try:
            self._ui_after_id = self.root.after(25, self._drain_ui_queue)
        except tk.TclError:
            self._ui_after_id = None

    # ─────────────────────────── Limpieza ───────────────────────────────

    def close(self):
        """Detiene hilos, callbacks, hotkey y ventanas secundarias."""
        if self._closed:
            return
        self._closed = True

        stop_event = getattr(self, "_stop_event", None)
        if stop_event is not None:
            stop_event.set()

        self._stop_hotkey()

        try:
            self.manual_combo.close_popup()
        except (AttributeError, tk.TclError):
            pass

        for owner, attribute in (
            (self.root, "_ui_after_id"),
            (self.window, "_top_after_id"),
        ):
            after_id = getattr(self, attribute, None)
            if after_id is not None:
                try:
                    owner.after_cancel(after_id)
                except (tk.TclError, RuntimeError):
                    pass
                setattr(self, attribute, None)

        if self._settings_dialog is not None:
            try:
                if self._settings_dialog.winfo_exists():
                    self._settings_dialog.destroy()
            except tk.TclError:
                pass
            self._settings_dialog = None

        if self._editor is not None:
            try:
                self._editor._close_editor()
            except (tk.TclError, RuntimeError, AttributeError):
                pass
            self._editor = None

        try:
            if self.window.winfo_exists():
                self.window.destroy()
        except tk.TclError:
            pass

        detect_thread = getattr(self, "_detect_thread", None)
        if (detect_thread is not None
                and detect_thread.is_alive()
                and detect_thread is not threading.current_thread()):
            detect_thread.join(timeout=1.25)
        self._detect_thread = None

    # ─────────────────────── Hotkey global nativo ──────────────────────

    def _register_hotkey(self):
        """Activa el atajo con el mismo backend de las versiones estables."""
        self._hotkey_backend = None
        self._native_hotkey_thread = None
        self._native_hotkey_thread_id = None
        self._native_hotkey_registered = False
        self._joystick_hotkey_thread = None
        self._shortcut_error = None
        self._shortcut_listener_stop.clear()

        shortcut = normalize_shortcut(self.main.config.get("shortcut"))
        if shortcut["type"] == "joystick":
            try:
                from handbrake import Handbrake

                device_names = Handbrake.device_names()
                device = resolve_joystick_device(shortcut, device_names)
                Handbrake.read_input(
                    device, shortcut["input_type"], int(shortcut["number"]))
            except Exception as exc:
                self._shortcut_error = str(exc)
                return

            self._joystick_hotkey_thread = threading.Thread(
                target=self._joystick_hotkey_loop,
                args=(shortcut,),
                name="ACR-overlay-controller-shortcut",
                daemon=True,
            )
            self._joystick_hotkey_thread.start()
            self._hotkey_backend = "joystick"
            return

        parts = list(shortcut.get("modifiers", []))
        parts.append(str(shortcut.get("key", "F9")).lower())
        hotkey_text = "+".join(parts)
        try:
            # ``keyboard`` fue el backend usado cuando el atajo funcionaba
            # dentro de ACRally. El callback sólo encola trabajo para Tk.
            try:
                self._hotkey_handle = keyboard.add_hotkey(
                    hotkey_text,
                    lambda: self._post_ui(self.toggle),
                    suppress=True,
                    trigger_on_release=False,
                )
            except Exception:
                self._hotkey_handle = keyboard.add_hotkey(
                    hotkey_text,
                    lambda: self._post_ui(self.toggle),
                    suppress=False,
                    trigger_on_release=False,
                )
            self._hotkey_backend = "keyboard"
        except Exception as exc:
            self._shortcut_error = str(exc)

    def reload_shortcut(self):
        """Aplica un atajo nuevo sin reconstruir el overlay."""
        if self._closed:
            return "El overlay está cerrado"
        self._stop_hotkey()
        self._register_hotkey()
        try:
            self.shortcut_label.config(text=self.main.shortcut_text())
        except (AttributeError, tk.TclError):
            pass
        return self._shortcut_error

    def _joystick_hotkey_loop(self, shortcut):
        """Escucha un botón/eje sin interactuar con el foco de Windows."""
        try:
            from handbrake import Handbrake

            device_names = Handbrake.device_names()
            device = resolve_joystick_device(shortcut, device_names)
            input_type = shortcut["input_type"]
            number = int(shortcut["number"])
            was_active = joystick_input_active(
                shortcut,
                Handbrake.read_input(device, input_type, number),
            )

            while (not self._closed
                   and not self._shortcut_listener_stop.wait(0.035)):
                current = Handbrake.read_input(device, input_type, number)
                is_active = joystick_input_active(shortcut, current)
                if is_active and not was_active:
                    self._post_ui(self.toggle)
                was_active = is_active
        except Exception as exc:
            self._shortcut_error = str(exc)

    def _stop_hotkey(self):
        self._shortcut_listener_stop.set()

        if self._hotkey_handle is not None:
            try:
                keyboard.remove_hotkey(self._hotkey_handle)
            except Exception:
                pass
            self._hotkey_handle = None

        for thread in (
            getattr(self, "_joystick_hotkey_thread", None),
        ):
            if (thread is not None
                    and thread.is_alive()
                    and thread is not threading.current_thread()):
                thread.join(timeout=1.25)

        self._hotkey_backend = None
        self._native_hotkey_thread = None
        self._native_hotkey_thread_id = None
        self._native_hotkey_registered = False
        self._joystick_hotkey_thread = None

    # ────────────────────── Mostrar / ocultar ──────────────────────────

    def toggle(self):
        if self._closed:
            return
        self.hide() if self.visible else self.show()

    def show(self):
        """Muestra el overlay sin activar la aplicación."""
        if self._closed:
            return

        # Secuencia exacta utilizada antes del refactor.
        try:
            self.root.iconify()
        except tk.TclError:
            pass

        try:
            self.window.deiconify()
        except (tk.TclError, RuntimeError):
            return

        self.visible = True
        self._make_no_activate()
        self._force_top()
        if self._top_after_id is None:
            self._top_loop()

    def hide(self):
        try:
            self.manual_combo.close_popup()
        except (AttributeError, tk.TclError):
            pass
        try:
            self.window.withdraw()
        except tk.TclError:
            pass
        self.visible = False
        if self._top_after_id is not None:
            try:
                self.window.after_cancel(self._top_after_id)
            except Exception:
                pass
            self._top_after_id = None

    def _toggle_collapsed(self):
        """Alterna entre el panel completo y la barra compacta."""
        x = self.window.winfo_x()
        y = self.window.winfo_y()

        if self.collapsed:
            self.main_row.pack(
                fill="x", expand=False, padx=PAD_MD, pady=PAD_SM)
            self.window.geometry(
                f"{self.overlay_width}x{self._normal_height}{x:+d}{y:+d}")
            self.window.attributes("-alpha", self.overlay_alpha)
            self.collapse_btn.config(text="−")
            self.collapsed = False
        else:
            if self._settings_visible:
                self._hide_inline_settings()
            self.main_row.pack_forget()
            self.window.update_idletasks()
            bar_height = self.title_bar.winfo_reqheight()
            self.window.geometry(
                f"{self.overlay_width}x{bar_height}{x:+d}{y:+d}")
            self.window.attributes(
                "-alpha", max(0.55, self.overlay_alpha - 0.13))
            self.collapse_btn.config(text="□")
            self.collapsed = True

        # Restaurar únicamente los dos atributos usados por la versión estable.
        self._make_no_activate()
        self._force_top()

    # ───────────────────── Integración nativa Win32 ────────────────────

    def _get_hwnds(self, window=None):
        """Devuelve el HWND de contenido de Tk y su wrapper superior."""
        window = window or self.window
        raw_hwnd = int(window.winfo_id())
        handles = [raw_hwnd]
        if os.name == "nt":
            try:
                parent = int(ctypes.windll.user32.GetParent(raw_hwnd) or 0)
                if parent and parent not in handles:
                    handles.append(parent)
            except Exception:
                pass
        return tuple(handles)

    def _get_hwnd(self, window=None):
        return self._get_hwnds(window)[-1]

    def _make_no_activate(self, window=None):
        """Evita que los clics del overlay activen su ventana Win32."""
        if os.name != "nt":
            return
        try:
            user32 = ctypes.windll.user32
            hwnd = self._get_hwnd(window)
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, ex_style | WS_EX_NOACTIVATE)
        except Exception:
            pass


    def _force_top(self, window=None):
        """Mantiene la ventana arriba sin activarla ni cambiar el foreground."""
        target = window or self.window
        if os.name != "nt":
            try:
                target.attributes("-topmost", True)
            except tk.TclError:
                pass
            return
        try:
            hwnd = self._get_hwnd(target)
            ctypes.windll.user32.SetWindowPos(
                hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        except Exception:
            pass

    def _reassert_floating_mode(self):
        """Restaura el modo flotante con el mecanismo estable de v0.1.14."""
        if self._closed or not self.visible:
            return
        self._make_no_activate()
        self._force_top()

    # ───────────────────── Estilo y geometría auxiliar ─────────────────

    def _style_native_dialog(self, window):
        """Iguala barra, borde y esquinas nativas con el editor."""
        try:
            if not window.winfo_exists():
                return
            hwnd = self._get_hwnd(window)
            dwmapi = ctypes.windll.dwmapi

            dark_mode = ctypes.c_int(1)
            for attribute in (20, 19):
                try:
                    dwmapi.DwmSetWindowAttribute(
                        hwnd, attribute, ctypes.byref(dark_mode),
                        ctypes.sizeof(dark_mode))
                except Exception:
                    pass

            do_not_round = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(do_not_round),
                ctypes.sizeof(do_not_round))

            def colorref(hex_color):
                value = hex_color.lstrip("#")
                red = int(value[0:2], 16)
                green = int(value[2:4], 16)
                blue = int(value[4:6], 16)
                return ctypes.c_int(red | (green << 8) | (blue << 16))

            for attribute, color in (
                    (34, BORDER), (35, BG2), (36, FG)):
                native_color = colorref(color)
                dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(native_color),
                    ctypes.sizeof(native_color))
        except Exception:
            pass

    def _physical_screen_size(self, window):
        """Obtiene píxeles físicos para no mezclar DPI lógico y geometría."""
        fallback = (window.winfo_screenwidth(), window.winfo_screenheight())
        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            user32.GetDC.restype = ctypes.c_void_p
            user32.GetDC.argtypes = [ctypes.c_void_p]
            user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            gdi32.GetDeviceCaps.argtypes = [ctypes.c_void_p, ctypes.c_int]
            screen_dc = user32.GetDC(0)
            if not screen_dc:
                return fallback
            try:
                width = gdi32.GetDeviceCaps(screen_dc, 118)
                height = gdi32.GetDeviceCaps(screen_dc, 117)
            finally:
                user32.ReleaseDC(0, screen_dc)
            if width > 0 and height > 0:
                return width, height
        except Exception:
            pass
        return fallback

    def _top_loop(self):
        """Refuerza solamente el z-order, con la frecuencia original."""
        if self.visible and not self._closed:
            self._force_top()
            try:
                self._top_after_id = self.window.after(1500, self._top_loop)
            except tk.TclError:
                self._top_after_id = None
        else:
            self._top_after_id = None
