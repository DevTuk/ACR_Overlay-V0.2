"""Panel integrado de opciones de largada, control y apariencia."""

import threading
import time
import tkinter as tk

import yaml

from ui_theme import (
    ACCENT, BG, BG2, BG3, BORDER, ERROR, FG, FONT_BODY_BOLD,
    FONT_CAPTION, FONT_HEADING, MUTED, PAD_MD, PAD_SM, PAD_XS,
    SUCCESS, WARN,
)


class OverlaySettingsMixin:
    def _open_start_settings(self):
        """Muestra u oculta las opciones dentro del mismo overlay."""
        if self.collapsed:
            self._toggle_collapsed()
        if self._settings_area is None:
            self._build_inline_settings()
        if self._settings_visible:
            self._hide_inline_settings()
        else:
            self._show_inline_settings()

    def _build_inline_settings(self):
        """Construye una segunda fila alineada con las cuatro columnas.

        Esta disposición se parece a un grid responsive: cada grupo de
        opciones queda debajo de la parte del overlay a la que pertenece.
        """
        area = tk.Frame(self.window, bg=BG)
        area.configure(height=112)
        area.pack_propagate(False)
        self._settings_area = area

        # Las medidas y separadores replican exactamente el main_row.
        detect_col = tk.Frame(area, bg=BG, width=200)
        detect_col.pack(side="left", fill="y")
        detect_col.pack_propagate(False)

        tk.Frame(area, bg=BORDER, width=1).pack(
            side="left", fill="y", padx=PAD_MD)

        mode_col = tk.Frame(area, bg=BG, width=200)
        mode_col.pack(side="left", fill="y")
        mode_col.pack_propagate(False)

        tk.Frame(area, bg=BORDER, width=1).pack(
            side="left", fill="y", padx=PAD_MD)

        appearance_col = tk.Frame(area, bg=BG, width=200)
        appearance_col.pack(side="left", fill="both", expand=True)
        appearance_col.pack_propagate(False)

        tk.Frame(area, bg=BORDER, width=1).pack(
            side="left", fill="y", padx=PAD_MD)

        actions_col = tk.Frame(area, bg=BG, width=200)
        actions_col.pack(side="left", fill="y")
        actions_col.pack_propagate(False)

        # ── Columna 2: modo de inicio ──────────────────────────────
        # Se agrupa y ancla abajo para que no quede visualmente más alto
        # que Detectar, el volumen de largada y Guardar.
        mode_block = tk.Frame(mode_col, bg=BG)
        # Fila 1 queda vacía; el bloque comienza en la fila 2.
        mode_block.place(x=0, y=30, relwidth=1.0, height=82)
        tk.Label(
            mode_block, text=self._tr("start_mode_label"), bg=BG, fg=FG,
            font=FONT_HEADING
        ).pack(anchor="w", pady=(0, PAD_XS))

        mode_var = tk.StringVar(
            value=self.main.config.get("start_mode", "automatic"))
        for value, key in (("automatic", "start_mode_auto"),
                           ("handbrake", "start_mode_handbrake")):
            tk.Radiobutton(
                mode_block, text=self._tr(key), value=value,
                variable=mode_var, bg=BG, fg=FG, selectcolor=BG2,
                activebackground=BG, activeforeground=FG,
                font=FONT_CAPTION
            ).pack(anchor="w", pady=1)

        # ── Columna 1: detección del freno ─────────────────────────
        try:
            from handbrake import Handbrake
            device_names = Handbrake.device_names()
        except Exception:
            device_names = []

        saved_control = self.main.config.get("handbrake") or None
        saved_device = (
            int(saved_control.get("device", 0))
            if saved_control else -1)
        if (saved_control and 0 <= saved_device < len(device_names)):
            calibration_message = self._tr(
                "handbrake_detected_full",
                device=device_names[saved_device],
                input_type=saved_control.get("type", "axis"),
                number=saved_control.get("number", 0))
        else:
            calibration_message = (
                self._tr("handbrake_auto_ready") if device_names else
                self._tr("handbrake_missing"))
        calibration_var = tk.StringVar(value=calibration_message)
        tk.Label(
            detect_col, textvariable=calibration_var, bg=BG,
            fg=WARN if device_names else ERROR, wraplength=195,
            justify="left", anchor="w", font=FONT_CAPTION
        ).pack(fill="x", pady=(30, PAD_XS))

        calibration = {
            "result": saved_control, "listening": False,
            "released": None, "deadline": 0,
        }

        def poll_control():
            if (not calibration["listening"]
                    or self._settings_area is None
                    or not self._settings_area.winfo_exists()):
                return
            try:
                current = Handbrake.snapshot_all()
                result = Handbrake.strongest_change_all(
                    calibration["released"], current)
            except Exception as exc:
                calibration["listening"] = False
                calibration_var.set(str(exc))
                detect_btn.config(state="normal")
                return
            if result is not None:
                calibration["result"] = result
                calibration["listening"] = False
                name = device_names[result["device"]]
                calibration_var.set(self._tr(
                    "handbrake_detected_full", device=name,
                    input_type=result["type"], number=result["number"]))
                detect_btn.config(
                    text=self._tr("handbrake_detect_again"),
                    state="normal")
                return
            if time.monotonic() >= calibration["deadline"]:
                calibration["listening"] = False
                calibration_var.set(self._tr("handbrake_not_detected"))
                detect_btn.config(
                    text=self._tr("handbrake_detect_control"),
                    state="normal")
                return
            self.window.after(40, poll_control)

        def detect_control():
            if not device_names:
                calibration_var.set(self._tr("handbrake_missing"))
                return
            try:
                calibration["released"] = Handbrake.snapshot_all()
            except Exception as exc:
                calibration_var.set(str(exc))
                return
            calibration["result"] = None
            calibration["listening"] = True
            calibration["deadline"] = time.monotonic() + 8.0
            calibration_var.set(self._tr("handbrake_listening"))
            detect_btn.config(
                text=self._tr("handbrake_listening_button"),
                state="disabled")
            self.window.after(150, poll_control)

        detect_btn = tk.Button(
            detect_col, text=self._tr("handbrake_detect_control"),
            command=detect_control, bg=BG3, fg=ACCENT,
            activebackground="#253550", activeforeground=FG,
            relief="flat", bd=0, font=FONT_BODY_BOLD, pady=4)
        # Se ancla abajo para coincidir con el botón Guardar.
        detect_btn.pack(side="bottom", fill="x", pady=(PAD_XS, 2))

        # ── Columna 3: apariencia y cuenta regresiva ───────────────
        #mode_block = tk.Frame(mode_col, bg=BG)
                # Fila 1 queda vacía; el bloque comienza en la fila 2.
        #mode_block.place(x=0, y=30, relwidth=1.0, height=82)

        global_alpha_var = tk.IntVar(value=int(self.overlay_alpha * 100))
        alpha_header = tk.Frame(appearance_col, bg=BG)
        alpha_header.pack(fill="x")
        tk.Label(
            alpha_header, text=self._tr("global_alpha_label"),
            bg=BG, fg=MUTED, font=FONT_CAPTION
        ).pack(side="left")
        alpha_text = tk.StringVar(value=f"{global_alpha_var.get()}%")
        tk.Label(
            alpha_header, textvariable=alpha_text,
            bg=BG, fg=FG, font=FONT_CAPTION
        ).pack(side="right")
        tk.Scale(
            appearance_col, from_=60, to=100, orient="horizontal",
            variable=global_alpha_var, showvalue=False, width=10,
            bg=BG, troughcolor=BG2, highlightthickness=0,
            command=lambda value: alpha_text.set(
                f"{int(float(value))}%")
        ).pack(fill="x", pady=(0, PAD_XS))

        # Mismo patrón visual que transparencia: título y porcentaje arriba,
        # barra completa debajo.
        start_volume_var = tk.IntVar(value=int(round(float(
            self.main.config.get("start_beep_volume", 0.35)) * 100)))
        volume_block = tk.Frame(appearance_col, bg=BG)
        volume_block.pack(side="bottom", fill="x", pady=(PAD_XS, 0))
        volume_header = tk.Frame(volume_block, bg=BG)
        volume_header.pack(fill="x")
        tk.Label(
            volume_header, text=self._tr("start_volume_label"),
            bg=BG, fg=MUTED, font=FONT_CAPTION
        ).pack(side="left")
        start_volume_text = tk.StringVar(
            value=f"{start_volume_var.get()}%")
        tk.Label(
            volume_header, textvariable=start_volume_text,
            bg=BG, fg=FG, font=FONT_CAPTION
        ).pack(side="right")
        tk.Scale(
            volume_block, from_=0, to=100, orient="horizontal",
            variable=start_volume_var, showvalue=False, width=10,
            bg=BG, troughcolor=BG2, highlightthickness=0,
            command=lambda value: start_volume_text.set(
                f"{int(float(value))}%")
        ).pack(fill="x")

        # ── Columna 4: acciones ────────────────────────────────────
        def test_countdown():
            from acrally import ACRally
            preview_voice = (
                self.voice_dirs[self.voice_index]
                if self.voice_dirs else "")
            preview = ACRally(
                "", preview_voice, 0, 1, 1,
                start_beep_volume=start_volume_var.get() / 100.0)
            threading.Thread(
                target=preview._play_start_signal,
                args=(True,), daemon=True).start()

        test_btn = tk.Button(
            actions_col, text=self._tr("start_test_beeps"),
            command=test_countdown, bg=BG2, fg=WARN,
            activebackground=BG3, activeforeground=FG,
            relief="flat", bd=0, font=FONT_BODY_BOLD, pady=5
        )

        save_status_var = tk.StringVar(value="")

        def save_settings():
            if mode_var.get() == "handbrake":
                handbrake_config = (
                    calibration["result"]
                    or self.main.config.get("handbrake"))
                if not handbrake_config:
                    calibration_var.set(
                        self._tr("handbrake_calibrate_required"))
                    return
                self.main.config["handbrake"] = handbrake_config

            self.main.config["start_mode"] = mode_var.get()
            # Compatibilidad con config.yml antiguos: desde v0.1.14 la
            # cuenta regresiva siempre está activa.
            self.main.config["start_countdown"] = True
            self.main.config["start_beep_volume"] = (
                start_volume_var.get() / 100.0)
            self.overlay_alpha = global_alpha_var.get() / 100.0
            self.main.config["overlay_alpha"] = self.overlay_alpha
            self.main.config["editor_alpha"] = self.overlay_alpha
            self.main.config["overlay_x"] = self.window.winfo_x()
            self.main.config["overlay_y"] = self.window.winfo_y()
            try:
                with open("config.yml", "w", encoding="utf-8") as config_file:
                    yaml.safe_dump(
                        self.main.config, config_file,
                        allow_unicode=True, sort_keys=False)
            except Exception as exc:
                save_status_var.set(self._tr(
                    "settings_save_error", error=exc))
                save_btn.config(
                    text=self._tr("settings_save_error", error=""),
                    bg=ERROR, fg=FG)
                return

            if self.main.acrally:
                self.main.acrally.apply_start_settings(
                    mode_var.get(),
                    self.main.config.get("handbrake", {}),
                    True,
                    start_volume_var.get() / 100.0)

            self.window.attributes("-alpha", self.overlay_alpha)
            try:
                if (self._editor is not None
                        and self._editor.root is not None
                        and self._editor.root.winfo_exists()):
                    self._editor.root.attributes(
                        "-alpha", self.overlay_alpha)
            except tk.TclError:
                pass
            save_status_var.set("")
            save_btn.config(
                text=self._tr("settings_saved"),
                # Estado final confirmado: se invierten los colores.
                # ``disabledforeground`` evita que Tk vuelva gris el texto.
                bg=FG, fg=SUCCESS, disabledforeground=SUCCESS,
                activebackground=FG, activeforeground=SUCCESS,
                state="disabled")
            # Dejamos la confirmación visible un momento antes de cerrar.
            self.window.after(1400, self._hide_inline_settings)

        save_btn = tk.Button(
            actions_col, text=self._tr("btn_save_settings"),
            command=save_settings, bg=SUCCESS, fg=BG,
            activebackground="#339957", activeforeground=FG,
            relief="flat", bd=0, font=FONT_BODY_BOLD, pady=5
        )
        self._settings_save_btn = save_btn
        # ``side="bottom"`` equivale a anclar las acciones al pie del panel.
        save_btn.pack(side="bottom", fill="x", pady=(PAD_SM, 2))
        # La prueba ocupa la segunda fila; Guardar permanece en la última.
        test_btn.pack(side="top", fill="x", pady=(30, 0))
        tk.Label(
            actions_col, textvariable=save_status_var,
            bg=BG, fg=SUCCESS, font=FONT_CAPTION,
            wraplength=195
        ).pack(side="bottom", fill="x", pady=(PAD_XS, 0))

    def _show_inline_settings(self):
        # Al mostrar opciones se suma ``_settings_extra_width`` al ancho
        # normal. Es equivalente a desplegar un sidebar en una web.
        if self._settings_area is None or self._settings_visible:
            return
        if self._settings_save_btn is not None:
            self._settings_save_btn.config(
                text=self._tr("btn_save_settings"),
                bg=SUCCESS, fg=BG, disabledforeground=MUTED,
                activebackground="#339957", activeforeground=FG,
                state="normal")
        self._settings_area.pack(
            fill="x", padx=PAD_MD, pady=(0, PAD_SM))
        self._settings_visible = True
        # No usamos una altura rígida: cada idioma puede ocupar distinta
        # cantidad de líneas. Tk calcula el alto necesario antes de mostrarlo.
        self.window.update_idletasks()
        required_height = (
            self.title_bar.winfo_reqheight()
            + self.main_row.winfo_reqheight()
            + self._settings_area.winfo_reqheight()
            + PAD_SM * 4
        )
        self._settings_height = max(230, required_height)
        x = self.window.winfo_x()
        y = self.window.winfo_y()
        self.window.geometry(
            f"{self.overlay_width}x{self._settings_height}{x:+d}{y:+d}")
        self._make_no_activate()
        self._force_top()

    def _hide_inline_settings(self):
        if self._settings_area is None or not self._settings_visible:
            return
        self._settings_area.pack_forget()
        self._settings_visible = False
        x = self.window.winfo_x()
        y = self.window.winfo_y()
        height = (
            self.title_bar.winfo_reqheight()
            if self.collapsed else self._normal_height)
        self.window.geometry(
            f"{self.overlay_width}x{height}{x:+d}{y:+d}")
        self._make_no_activate()
        self._force_top()
