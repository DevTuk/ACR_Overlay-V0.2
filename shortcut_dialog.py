"""Ventana de captura del atajo configurable del overlay."""

from __future__ import annotations

import time
import tkinter as tk
from typing import Any, Callable

from shortcut import (
    keyboard_shortcut_from_event,
    normalize_shortcut,
    shortcut_display,
)
from ui_theme import (
    ACCENT, BG, BG2, BG3, ERROR, FG, FONT_BODY, FONT_BODY_BOLD,
    FONT_CAPTION, FONT_HEADING, MUTED, PAD_MD, PAD_SM, PAD_XS, SUCCESS, WARN,
)


class ShortcutCaptureDialog:
    """Captura una combinación de teclado o un control físico conectado."""

    def __init__(
        self,
        parent: tk.Misc,
        current: object,
        on_save: Callable[[dict[str, Any]], None],
        translate: Callable[..., str],
    ) -> None:
        self.parent = parent
        self.on_save = on_save
        self.tr = translate
        self.candidate = normalize_shortcut(current)
        self._poll_after_id: str | None = None
        self._listening_device = False
        self._device_names: list[str] = []
        self._released_states = None
        self._deadline = 0.0

        window = tk.Toplevel(parent)
        self.window = window
        window.title(self.tr("shortcut_dialog_title"))
        window.configure(bg=BG)
        window.resizable(False, False)
        window.geometry("500x285")
        window.transient(parent)
        window.protocol("WM_DELETE_WINDOW", self.close)

        container = tk.Frame(window, bg=BG)
        container.pack(fill="both", expand=True, padx=PAD_MD, pady=PAD_MD)

        tk.Label(
            container,
            text=self.tr("shortcut_dialog_heading"),
            bg=BG,
            fg=FG,
            font=FONT_HEADING,
        ).pack(anchor="w")
        tk.Label(
            container,
            text=self.tr("shortcut_dialog_help"),
            bg=BG,
            fg=MUTED,
            justify="left",
            wraplength=460,
            font=FONT_CAPTION,
        ).pack(anchor="w", pady=(PAD_XS, PAD_SM))

        candidate_frame = tk.Frame(container, bg=BG2)
        candidate_frame.pack(fill="x", pady=(PAD_XS, PAD_SM))
        tk.Label(
            candidate_frame,
            text=self.tr("shortcut_current_label"),
            bg=BG2,
            fg=MUTED,
            font=FONT_CAPTION,
        ).pack(anchor="w", padx=PAD_SM, pady=(PAD_SM, 0))
        self.candidate_var = tk.StringVar()
        tk.Label(
            candidate_frame,
            textvariable=self.candidate_var,
            bg=BG2,
            fg=WARN,
            font=FONT_BODY_BOLD,
            anchor="w",
        ).pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))

        self.status_var = tk.StringVar(value=self.tr("shortcut_keyboard_ready"))
        self.status_label = tk.Label(
            container,
            textvariable=self.status_var,
            bg=BG,
            fg=MUTED,
            font=FONT_CAPTION,
            justify="left",
            anchor="w",
            wraplength=460,
        )
        self.status_label.pack(fill="x", pady=(0, PAD_SM))

        self.detect_button = tk.Button(
            container,
            text=self.tr("shortcut_detect_device"),
            command=self._start_device_capture,
            bg=BG3,
            fg=ACCENT,
            activebackground=BG2,
            activeforeground=FG,
            relief="flat",
            bd=0,
            font=FONT_BODY_BOLD,
            pady=6,
        )
        self.detect_button.pack(fill="x")

        actions = tk.Frame(container, bg=BG)
        actions.pack(side="bottom", fill="x", pady=(PAD_MD, 0))
        tk.Button(
            actions,
            text=self.tr("shortcut_cancel"),
            command=self.close,
            bg=BG3,
            fg=FG,
            activebackground=BG2,
            activeforeground=FG,
            relief="flat",
            bd=0,
            font=FONT_BODY,
            padx=PAD_MD,
            pady=6,
        ).pack(side="right")
        tk.Button(
            actions,
            text=self.tr("shortcut_save"),
            command=self._save,
            bg=SUCCESS,
            fg=BG,
            activebackground="#339957",
            activeforeground=FG,
            relief="flat",
            bd=0,
            font=FONT_BODY_BOLD,
            padx=PAD_MD,
            pady=6,
        ).pack(side="right", padx=(0, PAD_SM))

        self._refresh_candidate_text()
        window.bind("<KeyPress>", self._capture_keyboard, add="+")
        window.after_idle(self._focus_window)

    def _focus_window(self) -> None:
        try:
            self.window.lift()
            self.window.focus_force()
        except tk.TclError:
            pass

    def _capture_keyboard(self, event: tk.Event) -> str | None:
        if self._listening_device:
            return None
        shortcut = keyboard_shortcut_from_event(event)
        if shortcut is None:
            return None
        self.candidate = shortcut
        self.status_var.set(self.tr("shortcut_keyboard_captured"))
        self.status_label.config(fg=SUCCESS)
        self._refresh_candidate_text()
        return "break"

    def _start_device_capture(self) -> None:
        try:
            from handbrake import Handbrake

            self._device_names = Handbrake.device_names()
            if not self._device_names:
                self.status_var.set(self.tr("shortcut_no_device"))
                self.status_label.config(fg=ERROR)
                return
            self._released_states = Handbrake.snapshot_all()
        except Exception as exc:
            self.status_var.set(str(exc))
            self.status_label.config(fg=ERROR)
            return

        self._listening_device = True
        self._deadline = time.monotonic() + 8.0
        self.status_var.set(self.tr("shortcut_device_listening"))
        self.status_label.config(fg=WARN)
        self.detect_button.config(
            text=self.tr("shortcut_device_listening_button"),
            state="disabled",
        )
        self._poll_after_id = self.window.after(150, self._poll_device)

    def _poll_device(self) -> None:
        self._poll_after_id = None
        if not self._listening_device:
            return
        try:
            from handbrake import Handbrake

            current = Handbrake.snapshot_all()
            result = Handbrake.strongest_change_all(
                self._released_states,
                current,
            )
        except Exception as exc:
            self._finish_device_capture(error=str(exc))
            return

        if result is not None:
            device = int(result["device"])
            self.candidate = {
                "type": "joystick",
                "device": device,
                "device_name": self._device_names[device],
                "input_type": result["type"],
                "number": int(result["number"]),
                "released": float(result["released"]),
                "pressed": float(result["pressed"]),
                "threshold": float(result.get("threshold", 0.7)),
            }
            self._finish_device_capture(success=True)
            return

        if time.monotonic() >= self._deadline:
            self._finish_device_capture(error=self.tr("shortcut_not_detected"))
            return

        self._poll_after_id = self.window.after(40, self._poll_device)

    def _finish_device_capture(
        self,
        *,
        success: bool = False,
        error: str | None = None,
    ) -> None:
        self._listening_device = False
        self.detect_button.config(
            text=self.tr("shortcut_detect_device"),
            state="normal",
        )
        if success:
            self.status_var.set(self.tr("shortcut_device_captured"))
            self.status_label.config(fg=SUCCESS)
            self._refresh_candidate_text()
        else:
            self.status_var.set(error or self.tr("shortcut_not_detected"))
            self.status_label.config(fg=ERROR)

    def _refresh_candidate_text(self) -> None:
        self.candidate_var.set(shortcut_display(
            self.candidate,
            device_names=self._device_names or None,
            button_word=self.tr("shortcut_button_word"),
            axis_word=self.tr("shortcut_axis_word"),
        ))

    def _save(self) -> None:
        self.on_save(normalize_shortcut(self.candidate))
        self.close()

    def close(self) -> None:
        self._listening_device = False
        if self._poll_after_id is not None:
            try:
                self.window.after_cancel(self._poll_after_id)
            except tk.TclError:
                pass
            self._poll_after_id = None
        try:
            self.window.grab_release()
        except tk.TclError:
            pass
        try:
            self.window.destroy()
        except tk.TclError:
            pass
