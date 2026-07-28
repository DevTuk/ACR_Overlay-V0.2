import ctypes
import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk

import yaml

import util
from acrally import ACRally
from overlay import Overlay
from i18n import t, LANG_NAMES
from single_instance import SingleInstance
from shortcut import normalize_shortcut, shortcut_display
from shortcut_dialog import ShortcutCaptureDialog
from ui_theme import (
    ACCENT, BG, BG2, FG, FONT_BODY, FONT_BODY_BOLD,
    FONT_CAPTION, MUTED, PAD_MD, PAD_SM, PAD_XS, WARN,
    configure_ttk,
)


def _set_runtime_directory() -> None:
    """Hace que YAML, voces y pacenotes se lean junto al EXE/proyecto."""
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent
    os.chdir(base_dir)


_set_runtime_directory()


class Main:
    def __init__(self, instance_guard=None):
        # ``config.yml`` cumple el papel de localStorage: conserva idioma,
        # posición, transparencia y demás preferencias entre ejecuciones.
        self.config = yaml.safe_load(open("config.yml", encoding="utf-8"))
        self.acrally = None
        self.overlay = None
        self._closing = False
        self._instance_guard = instance_guard
        self._shortcut_dialog = None

        root = tk.Tk()
        root.title("ACRally Pacenote Overlay V 0.2")
        root.iconbitmap(util.resource_path("icon.ico"))
        root.geometry("430x285")
        root.resizable(False, False)
        root.configure(bg=BG)
        configure_ttk(root)
        self.root = root
        root.protocol("WM_DELETE_WINDOW", self.close)

        lang = self.config.get("lang", "es")

        # ── LAYOUT DE LA VENTANA PRINCIPAL ─────────────────────────
        # Frame = div, Label = texto y pack() ≈ un layout flex sencillo.
        # Los colores/fuentes globales se editan en ui_theme.py.
        title_row = tk.Frame(root, bg=BG)
        title_row.pack(pady=(14, 2))
        tk.Label(title_row, text="ACR Pacenote Overlay",
                 bg=BG, fg=ACCENT,
                 font=("Segoe UI Semibold", 14)).pack(side="left")
        tk.Label(title_row, text="  ·  Mod: Dienqn",
                 bg=BG, font=FONT_CAPTION,
                 fg=MUTED).pack(side="bottom", padx=(1,0))

        self.status_var = tk.StringVar(value=t(lang, "status_waiting"))
        self.status_label = tk.Label(
            root, textvariable=self.status_var,
            bg=BG, font=FONT_BODY_BOLD, fg=MUTED, wraplength=350)
        self.status_label.pack(pady=PAD_XS)

        self.stage_var = tk.StringVar(value="")
        tk.Label(root, textvariable=self.stage_var,
                 bg=BG, font=FONT_BODY, fg=FG, wraplength=350).pack()
        
        self.open_overlay = tk.StringVar(value=t(lang, "open_overlay"))
        self.overlay_label = tk.Label(
            root, textvariable=self.open_overlay,
            bg=BG, font=FONT_BODY_BOLD, fg=MUTED, wraplength=380)
        self.overlay_label.pack(pady=PAD_XS)

        # ── Atajo configurable ─────────────────────────────────────
        shortcut_frame = tk.Frame(root, bg=BG2)
        shortcut_frame.pack(fill="x", padx=22, pady=(PAD_SM, 0))
        shortcut_texts = tk.Frame(shortcut_frame, bg=BG2)
        shortcut_texts.pack(side="left", fill="x", expand=True,
                            padx=PAD_MD, pady=PAD_SM)
        self.shortcut_title_label = tk.Label(
            shortcut_texts, text=t(lang, "shortcut_label"),
            bg=BG2, fg=MUTED, font=FONT_CAPTION)
        self.shortcut_title_label.pack(anchor="w")
        self.shortcut_var = tk.StringVar(value=self.shortcut_text())
        tk.Label(
            shortcut_texts, textvariable=self.shortcut_var,
            bg=BG2, fg=WARN, font=FONT_BODY_BOLD).pack(anchor="w")
        self.shortcut_change_btn = tk.Button(
            shortcut_frame, text=t(lang, "shortcut_change"),
            command=self._open_shortcut_dialog,
            bg=BG2, fg=ACCENT, activebackground="#253550",
            activeforeground=FG, relief="flat", bd=0,
            font=FONT_BODY_BOLD, padx=PAD_MD, pady=PAD_XS)
        self.shortcut_change_btn.pack(side="right", padx=PAD_SM)

        # ── Selector de idioma ──
        lang_frame = tk.Frame(root, bg=BG)
        lang_frame.pack(pady=(10, 0))

        self.lang_label = tk.Label(
            lang_frame, text=t(lang, "lang_label"),
            bg=BG, font=FONT_CAPTION, fg=MUTED)
        self.lang_label.pack(side="left", padx=(0, 6))

        self.lang_var = tk.StringVar(value=LANG_NAMES.get(lang, "Español"))
        lang_combo = ttk.Combobox(
            lang_frame, textvariable=self.lang_var,
            values=list(LANG_NAMES.values()),
            state="readonly", font=FONT_BODY, width=13)
        lang_combo.pack(side="left")
        lang_combo.bind("<<ComboboxSelected>>", self._on_lang_change)

        threading.Thread(target=util.initialise_audio, daemon=True).start()

        self.overlay = Overlay(self)
        shortcut_error = getattr(self.overlay, "_shortcut_error", None)
        if shortcut_error:
            self.set_status(
                t(lang, "shortcut_registration_error", error=shortcut_error),
                color=WARN,
            )

        try:
            root.mainloop()
        finally:
            # También cubre cierres externos de Tk o errores que terminen el
            # mainloop sin pasar por el botón X.
            self.close()

    def close(self):
        """Cierra toda la aplicación, no solamente la ventana principal.

        El ``root`` era destruido por Tk, pero el hotkey global y otros
        recursos seguían vivos porque nunca se ejecutaba ``Overlay.close()``.
        La secuencia importa: primero se detienen trabajadores y hooks, y al
        final se destruye Tk.
        """
        if self._closing:
            return
        self._closing = True

        # Evita nuevos clics y nuevos eventos mientras se libera el proceso.
        try:
            self.root.withdraw()
        except tk.TclError:
            pass

        if self._shortcut_dialog is not None:
            try:
                self._shortcut_dialog.close()
            except Exception:
                pass
            self._shortcut_dialog = None

        overlay = self.overlay
        self.overlay = None
        if overlay is not None:
            try:
                overlay.close()
            except Exception:
                # El cierre debe continuar aunque una ventana secundaria ya
                # haya sido destruida por Windows/Tk.
                pass

        self.stop_stage()

        # Libera PortAudio y pygame si fueron inicializados. Ambos son
        # opcionales y no deben impedir el cierre si no están disponibles.
        try:
            util.shutdown_audio()
        except Exception:
            pass
        try:
            from handbrake import Handbrake
            Handbrake.shutdown()
        except Exception:
            pass

        try:
            self.root.quit()
        except tk.TclError:
            pass
        try:
            self.root.destroy()
        except tk.TclError:
            pass

        # Libera el mutex de instancia única antes de terminar.
        guard = self._instance_guard
        self._instance_guard = None
        if guard is not None:
            try:
                guard.close()
            except Exception:
                pass

        # En el ejecutable compilado no esperamos a que librerías nativas o
        # hilos daemon terminen por su cuenta. ExitProcess finaliza el único
        # proceso de la versión --onedir inmediatamente después de la limpieza.
        if getattr(sys, "frozen", False):
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            except Exception:
                pass
            if os.name == "nt":
                ctypes.windll.kernel32.ExitProcess(0)
            os._exit(0)

    def minimize_to_taskbar(self):
        """Minimiza el main sin activarlo y conserva su icono en la barra.

        El overlay se ejecuta como una ventana flotante independiente. El main
        no se retira con ``withdraw()`` porque eso lo convierte en una
        aplicación invisible: sigue ejecutándose, pero el usuario no tiene una
        entrada visible desde la que restaurarlo o cerrarlo.

        En Windows usamos ``SW_SHOWMINNOACTIVE`` para que minimizar el main no
        le quite el foco al juego. Al hacer clic en su icono de la barra de
        tareas, Windows lo restaura normalmente.
        """
        if self._closing:
            return

        try:
            self.root.update_idletasks()
            if os.name == "nt":
                user32 = ctypes.windll.user32
                content_hwnd = int(self.root.winfo_id())
                wrapper_hwnd = int(user32.GetParent(content_hwnd) or 0)
                hwnd = wrapper_hwnd or content_hwnd
                SW_SHOWMINNOACTIVE = 7
                user32.ShowWindow(hwnd, SW_SHOWMINNOACTIVE)
            else:
                self.root.iconify()
        except (tk.TclError, RuntimeError, ValueError):
            try:
                self.root.iconify()
            except tk.TclError:
                pass

    def shortcut_text(self):
        """Devuelve el atajo persistido en un formato legible."""
        lang = self.config.get("lang", "es")
        return shortcut_display(
            self.config.get("shortcut"),
            button_word=t(lang, "shortcut_button_word"),
            axis_word=t(lang, "shortcut_axis_word"),
        )

    def _open_shortcut_dialog(self):
        if self._closing:
            return
        dialog = self._shortcut_dialog
        if dialog is not None:
            try:
                if dialog.window.winfo_exists():
                    dialog.window.lift()
                    dialog.window.focus_force()
                    return
            except tk.TclError:
                pass

        lang = self.config.get("lang", "es")

        def translate(key, **kwargs):
            return t(lang, key, **kwargs)

        self._shortcut_dialog = ShortcutCaptureDialog(
            self.root,
            self.config.get("shortcut"),
            self._apply_shortcut,
            translate,
        )

    def _apply_shortcut(self, shortcut):
        """Guarda y activa el atajo sin reiniciar la aplicación."""
        if self._closing:
            return

        previous = normalize_shortcut(self.config.get("shortcut"))
        candidate = normalize_shortcut(shortcut)
        self.config["shortcut"] = candidate

        error = None
        if self.overlay:
            error = self.overlay.reload_shortcut()

        lang = self.config.get("lang", "es")
        if error:
            # Un atajo ocupado o un dispositivo desconectado no debe dejar al
            # usuario sin forma de volver a abrir el overlay.
            self.config["shortcut"] = previous
            if self.overlay:
                self.overlay.reload_shortcut()
            self.shortcut_var.set(self.shortcut_text())
            self.set_status(
                t(lang, "shortcut_registration_error", error=error),
                color=WARN,
            )
            return

        with open("config.yml", "w", encoding="utf-8") as config_file:
            yaml.safe_dump(
                self.config, config_file,
                allow_unicode=True, sort_keys=False)

        self.shortcut_var.set(self.shortcut_text())
        self.set_status(t(lang, "shortcut_saved"), color=ACCENT)

    def _on_lang_change(self, event=None):
        if self._closing:
            return
        name = self.lang_var.get()
        code = next((k for k, v in LANG_NAMES.items() if v == name), "es")
        self.config["lang"] = code
        yaml.dump(self.config, open("config.yml", "w", encoding="utf-8"))
        self.lang_label.config(text=t(code, "lang_label"))
        self.status_var.set(t(code, "status_waiting"))
        self.stage_var.set("")
        self.open_overlay.set(t(code,"open_overlay"))
        self.shortcut_title_label.config(text=t(code, "shortcut_label"))
        self.shortcut_change_btn.config(text=t(code, "shortcut_change"))
        self.shortcut_var.set(self.shortcut_text())
        if self._shortcut_dialog is not None:
            try:
                self._shortcut_dialog.close()
            except Exception:
                pass
            self._shortcut_dialog = None
        # Reconstruir el overlay con el nuevo idioma
        if self.overlay:
            self.overlay.close()
            self.overlay = Overlay(self)

    def set_status(self, line1, line2="", color=MUTED):
        if self._closing:
            return
        self.root.after(0, lambda: self.status_var.set(line1))
        self.root.after(0, lambda: self.stage_var.set(line2))
        self.root.after(0, lambda: self.status_label.config(fg=color))
        

    def start_stage(
            self, stage_name, start_from_distance=0,
            resume_started=False):
        if self._closing:
            return
        if self.acrally:
            self.acrally.exit()
            self.acrally = None

        self.acrally = ACRally(
            stage_name,
            self.config.get("voice", "English"),
            float(self.config.get("call_distance", 3.0)),
            int(self.config.get("calls_ahead", 4)),
            float(self.config.get("call_speed_multiplier", 1.0)),
            start_from_distance=start_from_distance,
            start_mode=self.config.get("start_mode", "automatic"),
            handbrake_config=self.config.get("handbrake", {}),
            countdown_enabled=True,
            start_beep_volume=float(self.config.get("start_beep_volume", 0.35)),
        )
        if resume_started:
            # Cambio de voz en caliente: la etapa ya fue largada. La nueva
            # instancia debe continuar desde el odómetro actual sin depender
            # de Guardar configuración ni reproducir otra cuenta regresiva.
            self.acrally.start_authorized = True
            self.acrally.started = True
            self.acrally.started_event.set()
        self.acrally.start()

    def stop_stage(self):
        acrally = self.acrally
        self.acrally = None
        if acrally:
            try:
                acrally.exit()
            except Exception:
                pass


def _show_already_running_message():
    if os.name != "nt":
        return
    try:
        ctypes.windll.user32.MessageBoxW(
            None,
            "ACRally Pacenote Overlay ya está abierto.",
            "ACRally Pacenote Overlay",
            0x00000040,
        )
    except Exception:
        pass


if __name__ == '__main__':
    instance_guard = SingleInstance()
    if instance_guard.already_running:
        _show_already_running_message()
        raise SystemExit(0)
    app = Main(instance_guard=instance_guard)
