"""Construcción visual, alineación y geometría del overlay."""

import math
import tkinter as tk
from tkinter import ttk

import yaml

from shortcut import shortcut_display

from ui_theme import (
    ACCENT, BG, BG2, BG3, BORDER, ERROR, FG, FONT_BODY,
    FONT_BODY_BOLD, FONT_CAPTION, FONT_DISPLAY, FONT_HEADING,
    MUTED, PAD_MD, PAD_SM, PAD_XS, SUCCESS, WARN,
    configure_ttk, refined_button,
)

from .helpers import get_app_volume


class OverlayViewMixin:
    def _build_window(self):
        """Crea la ventana y monta la vista principal alineada una sola vez."""
        window = tk.Toplevel(self.root)
        window.withdraw()
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        window.attributes("-alpha", self.overlay_alpha)
        window.configure(bg=BG)
        configure_ttk(window)
        window.bind("<Escape>", lambda _event: self.hide())
        self.window = window

        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        start_x = int(self.main.config.get("overlay_x", 60))
        start_y = int(self.main.config.get("overlay_y", 60))
        start_x = max(0, min(screen_w - self.overlay_width, start_x))
        start_y = max(0, min(screen_h - self._normal_height, start_y))
        window.geometry(
            f"{self.overlay_width}x{self._normal_height}"
            f"{start_x:+d}{start_y:+d}"
        )

        window.update_idletasks()
        self._make_no_activate()

        bar = tk.Frame(window, bg=BG2)
        bar.pack(fill="x")
        self.title_bar = bar

        title = tk.Label(
            bar,
            text="🎙  ACR PACENOTE OVERLAY",
            bg=BG2,
            fg=FG,
            font=FONT_BODY_BOLD,
        )
        title.pack(side="left", padx=(PAD_MD, PAD_XS), pady=PAD_SM)

        version = tk.Label(
            bar, text="v0.2", bg=BG2, fg=MUTED, font=FONT_CAPTION
        )
        version.pack(side="left", padx=(0, PAD_SM))

        shortcut_text = (
            self.main.shortcut_text()
            if hasattr(self.main, "shortcut_text")
            else shortcut_display(self.main.config.get("shortcut"))
        )
        shortcut = tk.Label(
            bar, text=shortcut_text, bg=BG2, fg=WARN,
            font=FONT_BODY_BOLD
        )
        shortcut.pack(side="left", pady=PAD_SM)
        self.shortcut_label = shortcut

        refined_button(
            bar,
            "✕",
            self.hide,
            bg=BG3,
            fg=ERROR,
            width=3,
            font=("Segoe UI", 11, "bold"),
            hover_bg=ERROR,
        ).pack(side="right", padx=(PAD_XS, PAD_SM), pady=PAD_XS)

        refined_button(
            bar,
            "⚙",
            self._open_start_settings,
            bg=BG3,
            fg=ACCENT,
            width=3,
            font=("Segoe UI Symbol", 11, "bold"),
            hover_bg=ACCENT,
        ).pack(side="right", padx=(PAD_XS, 0), pady=PAD_XS)

        self.collapse_btn = refined_button(
            bar,
            "−",
            self._toggle_collapsed,
            bg=BG3,
            fg=WARN,
            width=3,
            font=("Segoe UI", 11, "bold"),
            hover_bg=WARN,
        )
        self.collapse_btn.pack(side="right", pady=PAD_XS)

        for draggable in (bar, title, version, shortcut):
            self._make_draggable(draggable)

        self._build_aligned_main_row()

        resize_grip = tk.Frame(
            window, bg=BG2, width=6, cursor="sb_h_double_arrow"
        )
        resize_grip.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")
        resize_grip.bind("<Button-1>", self._begin_width_resize)
        resize_grip.bind("<B1-Motion>", self._resize_width)
        resize_grip.bind("<ButtonRelease-1>", self._finish_width_resize)

        window.update_idletasks()
        self._normal_height = max(
            160,
            self.title_bar.winfo_reqheight()
            + self.main_row.winfo_reqheight()
            + PAD_SM * 3,
        )
        start_y = max(0, min(screen_h - self._normal_height, start_y))
        window.geometry(
            f"{self.overlay_width}x{self._normal_height}"
            f"{start_x:+d}{start_y:+d}"
        )
        window.update_idletasks()
        self._make_no_activate()
        self._force_top()

    def _build_aligned_main_row(self):
        """Fila principal construida como una tabla de 4 × 3.

        Las cuatro columnas usan exactamente las mismas tres alturas:
        encabezado, control principal y control secundario.
        """
        table = tk.Frame(self.window, bg=BG, height=104)
        table.pack(fill="x", padx=PAD_MD, pady=PAD_SM)
        table.grid_propagate(False)
        self.main_row = table

        # 200 | divisor | 200 | divisor | flexible | divisor | 200
        for column in (0, 2, 6):
            table.grid_columnconfigure(column, minsize=200)
        table.grid_columnconfigure(4, minsize=200, weight=1)
        for column in (1, 3, 5):
            table.grid_columnconfigure(column, minsize=25)
            tk.Frame(table, bg=BORDER, width=1).grid(
                row=0, column=column, rowspan=3, sticky="ns",
                padx=PAD_MD)

        # Filas compartidas por todas las columnas.
        for row, height in enumerate((24, 40, 40)):
            table.grid_rowconfigure(row, minsize=height)

        def cell(column, row, rowspan=1):
            frame = tk.Frame(table, bg=BG)
            frame.grid(
                row=row, column=column, rowspan=rowspan,
                sticky="nsew")
            return frame

        # ── Columna 1: selección manual ────────────────────────────
        select_head = cell(0, 0)
        tk.Label(
            select_head, text=self._tr("manual_select"),
            bg=BG, fg=ACCENT, font=FONT_HEADING
        ).pack(anchor="w")

        select_input = cell(0, 1)
        self.manual_stage_var = tk.StringVar()
        self.manual_combo = ttk.Combobox(
            select_input, textvariable=self.manual_stage_var,
            values=sorted(self.available), state="readonly",
            font=FONT_BODY)
        self.manual_combo.pack(fill="x", pady=(2, 4))

        select_actions = cell(0, 2)
        refined_button(
            select_actions, "◆", self._save_mapping_manual,
            bg=WARN, fg=BG, width=3, hover_bg="#d98b16",
            font=("Segoe UI Symbol", 10)
        ).pack(side="left", pady=(2, 0))
        self.start_btn = tk.Button(
            select_actions, text="▶", command=self._on_manual_start,
            bg=SUCCESS, fg=BG, relief="flat", bd=0, width=3,
            activebackground="#339957", activeforeground=FG,
            font=("Segoe UI Symbol", 10), cursor="hand2")
        self.start_btn.pack(side="left", padx=(PAD_XS, 0), pady=(2, 0))

        # ── Columna 2: etapa, voz y adelanto ───────────────────────
        stage_cell = cell(2, 0)
        tk.Label(
            stage_cell, text=self._tr("stage_label"),
            bg=BG, fg=MUTED, font=FONT_CAPTION
        ).pack(side="left")
        self.raw_track_var = tk.StringVar(value="—")
        tk.Label(
            stage_cell, textvariable=self.raw_track_var,
            bg=BG, fg=WARN, font=FONT_BODY_BOLD,
            wraplength=145
        ).pack(side="left", padx=(PAD_XS, 0))

        voice_cell = cell(2, 1)
        tk.Label(
            voice_cell, text=self._tr("voice_label"), bg=BG, fg=MUTED,
            font=FONT_CAPTION, width=10, anchor="w"
        ).pack(side="left")
        refined_button(
            voice_cell, "◀", self._voice_prev,
            bg=BG3, fg=FG, width=2
        ).pack(side="left", pady=(1, 4))
        self.voice_label_var = tk.StringVar(
            value=self.voice_dirs[self.voice_index]
            if self.voice_dirs else "-")
        tk.Label(
            voice_cell, textvariable=self.voice_label_var,
            bg=BG, fg=FG, font=FONT_BODY, width=10
        ).pack(side="left", fill="x", expand=True)
        refined_button(
            voice_cell, "▶", self._voice_next,
            bg=BG3, fg=FG, width=2
        ).pack(side="right", pady=(1, 4))

        timing_cell = cell(2, 2)
        tk.Label(
            timing_cell, text=self._tr("timing_label"),
            bg=BG, fg=MUTED, font=FONT_CAPTION,
            width=10, anchor="w"
        ).pack(side="left")
        refined_button(
            timing_cell, "−", lambda: self._step_timing(-0.5),
            bg=BG3, fg=FG, width=2
        ).pack(side="left", pady=(2, 4))
        self.dist_label_var = tk.StringVar(
            value=f"{self.dist_var.get():.1f}s")
        tk.Label(
            timing_cell, textvariable=self.dist_label_var,
            bg=BG, fg=FG, font=FONT_BODY, width=10
        ).pack(side="left", fill="x", expand=True)
        refined_button(
            timing_cell, "+", lambda: self._step_timing(0.5),
            bg=BG3, fg=FG, width=2
        ).pack(side="right", pady=(2, 4))

        # ── Columna 3: estado y editor ─────────────────────────────
        status_cell = cell(4, 0)
        self.ov_status_var = tk.StringVar(
            value=self._tr("status_starting"))
        tk.Label(
            status_cell, textvariable=self.ov_status_var,
            bg=BG, fg=SUCCESS, font=FONT_HEADING,
            anchor="w", justify="left"
        ).pack(fill="x")

        editor_cell = cell(4, 1)
        tk.Button(
            editor_cell, text=self._tr("btn_editor"),
            command=self._open_editor, bg=BG3, fg=ACCENT,
            relief="solid", bd=1, highlightbackground=BORDER,
            highlightthickness=1, activebackground="#253550",
            activeforeground=FG, font=FONT_BODY_BOLD,
            justify="center"
        ).pack(fill="both", expand=True, pady=(2, 4))

        # El volumen general pertenece a esta columna: comparte el mismo
        # patrón visual que los sliders que aparecen al expandir opciones.
        volume_cell = cell(4, 2)
        volume_head = tk.Frame(volume_cell, bg=BG)
        volume_head.pack(fill="x")
        tk.Label(
            volume_head, text=self._tr("volume_label").title(),
            bg=BG, fg=MUTED, font=FONT_CAPTION
        ).pack(side="left")
        current_volume = get_app_volume()
        self.volume_var = tk.IntVar(
            value=int(round(math.sqrt(current_volume) * 100)))
        self.volume_label_var = tk.StringVar(
            value=f"{self.volume_var.get()}%")
        tk.Label(
            volume_head, textvariable=self.volume_label_var,
            bg=BG, fg=FG, font=FONT_CAPTION
        ).pack(side="right")
        self.volume_scale = tk.Scale(
            volume_cell, from_=0, to=100, orient="horizontal",
            variable=self.volume_var, command=self._on_volume_change,
            bg=BG, troughcolor=BG2, highlightthickness=0,
            showvalue=False, width=10)
        self.volume_scale.pack(fill="x")

        # ── Columna 4: odómetro ────────────────────────────────────
        odo_cell = cell(6, 0, rowspan=3)
        tk.Label(
            odo_cell, text=self._tr("odometer_label"),
            bg=BG, fg=MUTED, font=FONT_CAPTION
        ).pack(anchor="center")
        self.odometer_var = tk.StringVar(value="0.000 km")
        tk.Label(
            odo_cell, textvariable=self.odometer_var,
            bg=BG, fg=ACCENT, font=FONT_DISPLAY
        ).pack(anchor="center")

    def _make_draggable(self, widget):
        widget.bind("<Button-1>",
                    lambda e: (setattr(self, "_drag_x", e.x),
                               setattr(self, "_drag_y", e.y)))
        widget.bind("<B1-Motion>", self._do_drag)
        widget.bind("<ButtonRelease-1>", self._save_window_position)

    def _begin_width_resize(self, event):
        self._resize_start_root_x = event.x_root
        self._resize_start_width = self.overlay_width

    def _resize_width(self, event):
        delta = event.x_root - self._resize_start_root_x
        screen_width = self.window.winfo_screenwidth()
        max_width = max(900, screen_width - self.window.winfo_x())
        new_width = max(
            900, min(max_width, self._resize_start_width + delta))
        self.overlay_width = int(new_width)
        visible_extra = (
            self._settings_extra_width if self._settings_visible else 0)
        height = (
            self._settings_height
            if self._settings_visible else self._normal_height)
        self.window.geometry(
            f"{self.overlay_width + visible_extra}x{height}"
            f"{self.window.winfo_x():+d}{self.window.winfo_y():+d}")

    def _finish_width_resize(self, _event=None):
        self.main.config["overlay_width"] = self.overlay_width
        self.main.config["overlay_x"] = self.window.winfo_x()
        self.main.config["overlay_y"] = self.window.winfo_y()
        try:
            with open("config.yml", "w", encoding="utf-8") as config_file:
                yaml.safe_dump(
                    self.main.config, config_file,
                    allow_unicode=True, sort_keys=False)
        except Exception:
            pass

    def _do_drag(self, event):
        x = self.window.winfo_x() + (event.x - self._drag_x)
        y = self.window.winfo_y() + (event.y - self._drag_y)
        self.window.geometry(f"{x:+d}{y:+d}")

    def _save_window_position(self, event=None):
        self.main.config["overlay_x"] = self.window.winfo_x()
        self.main.config["overlay_y"] = self.window.winfo_y()
        with open("config.yml", "w", encoding="utf-8") as config_file:
            yaml.safe_dump(self.main.config, config_file,
                           allow_unicode=True, sort_keys=False)

    def _save(self, key, value):
        self.main.config[key] = value
        with open("config.yml", "w", encoding="utf-8") as config_file:
            yaml.safe_dump(
                self.main.config, config_file,
                allow_unicode=True, sort_keys=False)
