"""Apertura, posicionamiento y cierre del editor de pacenotes."""

import ctypes
import tkinter as tk


class OverlayEditorMixin:
    def _open_editor(self):
        # Bloquear también los clics que llegan antes de que Tk alcance a
        # construir la primera ventana.
        if self._editor_open_pending:
            return
        try:
            if (self._editor is not None and self._editor.root is not None
                    and self._editor.root.winfo_exists()):
                self._force_top(self._editor.root)
                self._editor_open_pending = False
                return
        except tk.TclError:
            self._editor = None
        try:
            self._editor_foreground_hwnd = (
                ctypes.windll.user32.GetForegroundWindow())
        except Exception:
            self._editor_foreground_hwnd = None
        self._editor_open_pending = True
        self.root.after(0, self._open_editor_safely)

    def _open_editor_safely(self):
        try:
            self._open_editor_now()
        except Exception as exc:
            self._editor = None
            self._set_ui(self._tr("status_error", error=exc), "")
        finally:
            # También se libera si falla la construcción a mitad de camino.
            self._editor_open_pending = False

    def _open_editor_now(self):
        from editor import Editor
        try:
            if (self._editor is not None and self._editor.root is not None
                    and self._editor.root.winfo_exists()):
                self._force_top(self._editor.root)
                return
        except tk.TclError:
            self._editor = None

        self.window.update_idletasks()
        editor_width = int(self.main.config.get("editor_width", 980))
        editor_height = int(self.main.config.get("editor_height", 680))
        editor_alpha = float(self.main.config.get("editor_alpha", 1.0))
        editor_width = max(800, min(1800, editor_width))
        editor_height = max(420, min(1100, editor_height))

        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        overlay_height = self.window.winfo_height()
        overlay_x = self.window.winfo_x()
        overlay_y = self.window.winfo_y()
        editor_y = overlay_y + overlay_height + 6

        if overlay_x + editor_width > screen_w:
            overlay_x = max(0, screen_w - editor_width)
            self.window.geometry(f"{overlay_x:+d}{overlay_y:+d}")
            self._save_window_position()

        # Si ambas ventanas no entran, subir el conjunto manteniendo al editor
        # exactamente debajo del overlay.
        if editor_y + editor_height > screen_h:
            overlay_y = max(0, screen_h - editor_height - overlay_height - 6)
            self.window.geometry(f"{overlay_x:+d}{overlay_y:+d}")
            self._save_window_position()
            editor_y = overlay_y + overlay_height + 6

        # Mantener el main minimizado antes de crear la ventana secundaria.
        try:
            self.root.iconify()
        except tk.TclError:
            pass

        editor = Editor()
        self._editor = editor
        try:
            editor.main(
                preset_stage=self._cur_stage,
                preset_voice=(self.voice_dirs[self.voice_index]
                              if self.voice_dirs else None),
                preset_lang=self.lang,
                preset_position=(overlay_x, editor_y),
                preset_width=editor_width,
                preset_height=editor_height,
                preset_alpha=editor_alpha,
                parent=self.root,
                run_mainloop=False,
                on_close=self._editor_closed,
                preset_foreground_hwnd=self._editor_foreground_hwnd,
            )
        except Exception:
            try:
                if editor.root is not None and editor.root.winfo_exists():
                    editor.root.destroy()
            except tk.TclError:
                pass
            self._editor = None
            raise

    def _editor_closed(self):
        self._editor = None
        self._editor_open_pending = False
