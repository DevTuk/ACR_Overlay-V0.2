import ctypes
import os
import threading
import time
import tkinter as tk
import tkinter.messagebox as mb
from tkinter import ttk

import yaml
import natsort

import util
from acrally import ACRally
from i18n import t
from ui_theme import (
    ACCENT, BG, BG2, BG3, BORDER, ERROR, FG, FONT_BODY,
    FONT_BODY_BOLD, FONT_CAPTION, FONT_HEADING, MUTED,
    SUCCESS, WARN,
)


# Identidad visual compartida con el overlay
PANEL = BG3
DIM = MUTED
ORANGE = WARN
GREEN = SUCCESS
RED = ERROR

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010


def configure_editor_styles(root):
    """Configura ttk para que el editor comparta la estética del overlay.

    GUÍA PARA EDITAR:
    Cada nombre como ``"Accent.TButton"`` funciona parecido a una clase CSS.
    ``style.configure`` define el estilo normal y ``style.map`` sus estados.
    Los colores y fuentes generales se cambian en ``ui_theme.py``.
    """
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure("Editor.TFrame", background=BG)
    style.configure("Toolbar.TFrame", background=BG2)
    style.configure("Panel.TFrame", background=PANEL)

    style.configure(
        "Editor.TLabel", background=BG, foreground=FG,
        font=FONT_BODY)
    style.configure(
        "Toolbar.TLabel", background=BG2, foreground=DIM,
        font=FONT_CAPTION)
    style.configure(
        "Title.TLabel", background=BG2, foreground=ACCENT,
        font=("Segoe UI Semibold", 14))
    style.configure(
        "Token.TLabel", background=BG, foreground=FG,
        font=FONT_BODY)
    style.configure(
        "Pause.TLabel", background=BG, foreground=ACCENT,
        font=FONT_BODY)
    style.configure(
        "Error.TLabel", background=BG, foreground=RED,
        font=FONT_BODY_BOLD)

    style.configure(
        "Editor.TButton", background=BG2, foreground=FG,
        bordercolor=BORDER, lightcolor=BG2, darkcolor=BG2,
        relief="flat", padding=(10, 6), font=FONT_BODY_BOLD)
    style.map(
        "Editor.TButton",
        background=[("active", BG3), ("pressed", "#30303d")],
        foreground=[("disabled", DIM), ("active", "#ffffff")])

    style.configure(
        "Move.TButton", background=BG3, foreground=FG,
        bordercolor=BORDER, lightcolor=BG3, darkcolor=BG3,
        relief="flat", padding=(0, 2), font=FONT_BODY_BOLD)
    style.map(
        "Move.TButton",
        background=[("active", "#29334b"), ("pressed", "#32405e")],
        foreground=[("disabled", DIM), ("active", "#ffffff")])

    style.configure(
        "Accent.TButton", background=BG3, foreground=ACCENT,
        bordercolor=ACCENT, lightcolor=BG3, darkcolor=BG3,
        relief="flat", padding=(11, 6), font=FONT_BODY_BOLD)
    style.map(
        "Accent.TButton",
        background=[("active", "#253550"), ("pressed", ACCENT)],
        foreground=[("disabled", DIM), ("pressed", BG)])

    style.configure(
        "GameMode.TButton", background="#332815", foreground=ORANGE,
        bordercolor=ORANGE, lightcolor="#332815", darkcolor="#332815",
        relief="flat", padding=(11, 6), font=FONT_BODY_BOLD)
    style.map(
        "GameMode.TButton",
        background=[("active", ORANGE)], foreground=[("active", BG)])

    style.configure(
        "Success.TButton", background="#173127", foreground=GREEN,
        bordercolor=GREEN, lightcolor="#173127", darkcolor="#173127",
        relief="flat", padding=(11, 6), font=FONT_BODY_BOLD)
    style.map(
        "Success.TButton",
        background=[("active", GREEN), ("pressed", "#27ae60")],
        foreground=[("disabled", DIM), ("active", "#101014")])

    style.configure(
        "Danger.TButton", background="#342027", foreground=RED,
        bordercolor="#5a2933", lightcolor="#342027", darkcolor="#342027",
        relief="flat", padding=(0, 2),
        font=FONT_BODY_BOLD)
    style.map(
        "Danger.TButton",
        background=[("active", RED)], foreground=[("active", "#ffffff")])

    style.configure(
        "CompactAdd.TButton", background="#1e2d45", foreground=ACCENT,
        bordercolor=ACCENT, lightcolor="#1e2d45", darkcolor="#1e2d45",
        relief="flat", padding=(7, 3), font=FONT_BODY_BOLD)
    style.map(
        "CompactAdd.TButton",
        background=[("active", "#253550"), ("pressed", ACCENT)],
        foreground=[("pressed", BG)])

    style.configure(
        "Editor.TEntry", fieldbackground=BG2, foreground=FG,
        insertcolor=FG, bordercolor=BORDER, lightcolor=BORDER,
        darkcolor=BORDER, padding=6, font=FONT_BODY)
    style.map("Editor.TEntry", bordercolor=[("focus", ACCENT)])

    style.configure(
        "Editor.TCombobox", fieldbackground=BG2, background=BG2,
        foreground=FG, arrowcolor=ORANGE, bordercolor=BORDER,
        lightcolor=BORDER, darkcolor=BORDER, padding=5,
        font=FONT_BODY)
    style.map(
        "Editor.TCombobox",
        fieldbackground=[("readonly", BG2), ("focus", BG2)],
        foreground=[("readonly", FG)],
        bordercolor=[("focus", ACCENT)],
        arrowcolor=[("active", ACCENT)])

    style.configure(
        "Note.TCombobox", fieldbackground=BG2, background=BG2,
        foreground=FG, arrowcolor=ORANGE, bordercolor=BORDER,
        lightcolor=BORDER, darkcolor=BORDER, padding=(4, 2),
        font=FONT_BODY)
    style.map(
        "Note.TCombobox",
        fieldbackground=[("focus", BG2)],
        bordercolor=[("focus", ACCENT)],
        arrowcolor=[("active", ACCENT)])

    style.configure(
        "Editor.TCheckbutton", background=BG, foreground=FG,
        focuscolor=BG, font=FONT_CAPTION)
    style.map(
        "Editor.TCheckbutton",
        background=[("active", BG)], foreground=[("active", ACCENT)])

    style.configure(
        "Vertical.TScrollbar", background=BORDER, troughcolor=BG,
        bordercolor=BG, arrowcolor=FG, darkcolor=BORDER,
        lightcolor=BORDER, relief="flat")
    style.map("Vertical.TScrollbar", background=[("active", ACCENT)])

    style.configure("Editor.TNotebook", background=BG, bordercolor=BORDER)
    style.configure(
        "Editor.TNotebook.Tab", background=BG2, foreground=DIM,
        padding=(12, 6), font=FONT_BODY_BOLD)
    style.map(
        "Editor.TNotebook.Tab",
        background=[("selected", "#1e2d45")],
        foreground=[("selected", ACCENT)])

    # Colores de la lista desplegable nativa de los Combobox.
    root.option_add("*TCombobox*Listbox.background", BG2)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", BG)


class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        self.configure(style="Editor.TFrame")
        self.canvas = tk.Canvas(
            self, bg=BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview,
            style="Vertical.TScrollbar")
        self.scrollable_frame = ttk.Frame(
            self.canvas, style="Editor.TFrame")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        canvas_frame = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(canvas_frame, width=e.width)
        )

        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def get_scroll(self):
        return self.canvas.yview()[1]

    def set_scroll(self, previous_bottom):
        self.update_idletasks()
        new_top, new_bottom = self.canvas.yview()
        new_visible = new_bottom - new_top
        new_target_top = previous_bottom - new_visible
        new_target_top = max(0.0, min(1.0 - new_visible, new_target_top))
        self.canvas.yview_moveto(new_target_top)

class Editor:
    def __init__(self):
        self.root = None
        self.scroll_frame = None
        self.pacenotes_combo = None
        self.voices_combo = None
        self.load_button = None
        self.save_button = None
        self.new_button = None
        self.focus_mode_button = None
        self.header_label = None
        self.stage_label = None
        self.voice_label = None
        self.game_mode = True
        self._geometry_after_id = None
        self._geometry_ready = False
        self._desired_outer_left = None
        self._on_close_callback = None

        self.acrally = None
        self.pacenote_elements = []
        self.pacenote_vars = []

        self.token_sounds = None
        self.dictionary = None
        self.reverse_dictionary = None
        self.pacenotes = None
        self.pacenote_options = []
        self.lang = "en"

    def _tr(self, key, **kwargs):
        return t(self.lang, key, **kwargs)

    def _on_mousewheel(self, event):
        """Permite desplazar las notas desde cualquier zona del editor."""
        if not self.scroll_frame:
            return
        try:
            if event.widget.winfo_class() in ("TCombobox", "Listbox"):
                return
        except Exception:
            pass
        direction = -1 if event.delta > 0 else 1
        self.scroll_frame.canvas.yview_scroll(direction * 3, "units")
        return "break"

    def _schedule_geometry_save(self, event=None):
        if (not self._geometry_ready or not self.root
                or (event is not None and event.widget is not self.root)):
            return
        if self._geometry_after_id is not None:
            self.root.after_cancel(self._geometry_after_id)
        self._geometry_after_id = self.root.after(
            500, self._persist_editor_geometry)

    def _persist_editor_geometry(self):
        self._geometry_after_id = None
        if not self.root or not self.root.winfo_exists():
            return
        try:
            config = yaml.safe_load(open("config.yml", encoding="utf-8")) or {}
            config["editor_width"] = self.root.winfo_width()
            config["editor_height"] = self.root.winfo_height()
            config["editor_alpha"] = float(self.root.attributes("-alpha"))
            with open("config.yml", "w", encoding="utf-8") as config_file:
                yaml.safe_dump(config, config_file,
                               allow_unicode=True, sort_keys=False)
        except (OSError, yaml.YAMLError, tk.TclError):
            pass

    def _close_editor(self):
        callback = self._on_close_callback
        self._on_close_callback = None
        try:
            self._persist_editor_geometry()
            if self.root is not None and self.root.winfo_exists():
                self.root.destroy()
        finally:
            self.root = None
            if callback is not None:
                callback()

    def load(self):
        voice = self.voices_combo.get()
        self.acrally = ACRally(
            self.pacenotes_combo.get(),
            voice,
            1,
            5,
            1,
        )
        self.token_sounds = self.acrally.build_token_sounds()

        self.dictionary = {}
        if os.path.exists(f"voices\\{voice}\\dictionary.yml"):
            self.dictionary = yaml.safe_load(open(f"voices\\{voice}\\dictionary.yml", "r", encoding="utf-8"))
        self.reverse_dictionary = {}
        for key, value in self.dictionary.items():
            self.reverse_dictionary[value] = key

        items = []
        items.extend(self.token_sounds.keys())
        items.extend(["Pause0.1s", "Pause0.25s", "Pause0.5s", "Pause1.0s", "Pause1.5s"])

        self.pacenote_options = [self.reverse_dictionary.get(x, x) for x in items if "-" not in x]
        self.pacenote_options = natsort.natsorted(self.pacenote_options)
        self.save_button["state"] = "normal"
        self.draw_pacenotes_frame()

    def new_pacenotes(self):
        if self.pacenotes:
            res = mb.askyesno(
                self._tr("editor_dialog_new_title"),
                self._tr("editor_dialog_new_message"), parent=self.root)
            if not res:
                return
        self.pacenotes = []
        self.load()

    def load_pacenotes(self):
        if self.pacenotes:
            res = mb.askyesno(
                self._tr("editor_dialog_load_title"),
                self._tr("editor_dialog_load_message"), parent=self.root)
            if not res:
                return
        self.pacenotes = yaml.safe_load(open(f"pacenotes/{self.pacenotes_combo.get()}.yml", encoding="utf-8"))
        self.load()

    def save_pacenotes(self):
        res = mb.askyesno(
            self._tr("editor_dialog_save_title"),
            self._tr(
                "editor_dialog_save_message",
                filename=f"{self.pacenotes_combo.get()}.yml"),
            parent=self.root)

        if res:
            yaml.dump(
                self.pacenotes,
                open(f"pacenotes/{self.pacenotes_combo.get()}.yml", "w", encoding="utf-8"),
                default_flow_style=None,
                sort_keys=False
            )

    def draw_pacenotes_frame(self):
        [x.destroy() for x in self.pacenote_elements]
        self.pacenote_elements = []
        self.pacenote_vars = []

        def draw_pacenotes(frame, i, pacenote):
            def pacenote_remove(i=i):
                self.pacenotes.pop(i)
                self.draw_pacenotes_frame()
            remove_btn = ttk.Button(
                frame, text="×", width=3, command=pacenote_remove,
                style="Danger.TButton")
            remove_btn.grid(row=i, column=0, padx=5, pady=5)
            self.pacenote_elements.append(remove_btn)

            distance_var = tk.StringVar(value=str(int(pacenote["distance"])))
            distance_entry = ttk.Entry(
                frame, textvariable=distance_var, width=6,
                style="Editor.TEntry")
            distance_entry.grid(row=i, column=1, padx=5, pady=5)
            self.pacenote_elements.append(distance_entry)

            def distance_change(e, i=i):
                distance = distance_var.get().strip()
                if distance.isdigit():
                    key = lambda x: x["distance"]
                    self.pacenotes[i]["distance"] = int(distance)
                    sorted_list = sorted(self.pacenotes, key=key)
                    if self.pacenotes != sorted_list:
                        self.pacenotes.sort(key=key)
                        self.draw_pacenotes_frame()
            distance_entry.bind("<FocusOut>", distance_change)
            distance_entry.bind("<Return>", distance_change)
            # self.pacenote_vars.append(distance_var)

            link_var = tk.BooleanVar(value=pacenote["link_to_next"])
            def link_change(index, value, op, i=i):
                self.pacenotes[i]["link_to_next"] = link_var.get()
            link_var.trace("w", link_change)
            link_chk = ttk.Checkbutton(
                frame,
                variable=link_var,
                text=self._tr("editor_link_next"),
                style="Editor.TCheckbutton"
            )
            link_chk.grid(row=i, column=2, padx=5, pady=5)
            self.pacenote_elements.append(link_chk)
            self.pacenote_vars.append(link_var)

            pacenotes_frame = None
            combined_pacenotes_frame = None

            def draw_pacenotes(
                    i=i
            ):
                nonlocal pacenotes_frame

                if pacenotes_frame:
                    pacenotes_frame.destroy()
                pacenotes_frame = ttk.Frame(frame, style="Editor.TFrame")
                pacenotes_frame.grid(
                    row=i, column=3, padx=5, pady=3, sticky="w")
                pacenotes_frame.columnconfigure(0, weight=1)
                for action_column in (1, 2, 3):
                    pacenotes_frame.columnconfigure(
                        action_column, minsize=36, uniform="note_actions")

                def create_entry(note_idx, t):
                    note_var = tk.StringVar(value=self.reverse_dictionary.get(t, t))
                    note_combo = ttk.Combobox(
                        pacenotes_frame,
                        values=self.pacenote_options,
                        textvariable=note_var,
                        style="Note.TCombobox"
                    )
                    note_combo.grid(
                        row=note_idx, column=0, sticky="ew",
                        padx=(0, 1), pady=(0, 1))
                    note_combo.unbind_class("TCombobox", "<MouseWheel>")

                    def note_change(e, note_idx=note_idx):
                        new_note = self.dictionary.get(note_var.get(), note_var.get())
                        old_note = self.pacenotes[i]["notes"][note_idx]
                        if old_note != new_note:
                            scroll = self.scroll_frame.get_scroll()
                            self.pacenotes[i]["notes"][note_idx] = new_note
                            draw_playable_pacenotes(
                                i
                            )
                            self.scroll_frame.set_scroll(scroll)
                    note_combo.bind("<FocusOut>", note_change)
                    note_combo.bind("<<ComboboxSelected>>", note_change)
                    note_combo.bind("<Return>", note_change)
                    self.pacenote_vars.append(note_var)

                    def note_up(note_idx=note_idx):
                        scroll = self.scroll_frame.get_scroll()
                        self.pacenotes[i]["notes"].insert(note_idx - 1, self.pacenotes[i]["notes"].pop(note_idx))
                        draw_pacenotes(
                            i
                        )
                        self.scroll_frame.set_scroll(scroll)

                    note_up = ttk.Button(
                        pacenotes_frame, text="▲", width=2,
                        command=note_up, style="Move.TButton")
                    note_up.grid(
                        row=note_idx, column=1, sticky="nsew",
                        padx=(0, 1), pady=(0, 1))
                    if note_idx == 0:
                        note_up["state"] = "disabled"

                    def note_down(note_idx=note_idx):
                        scroll = self.scroll_frame.get_scroll()
                        self.pacenotes[i]["notes"].insert(note_idx + 1, self.pacenotes[i]["notes"].pop(note_idx))
                        draw_pacenotes(
                            i
                        )
                        self.scroll_frame.set_scroll(scroll)

                    note_down = ttk.Button(
                        pacenotes_frame, text="▼", width=2,
                        command=note_down, style="Move.TButton")
                    note_down.grid(
                        row=note_idx, column=2, sticky="nsew",
                        padx=(0, 1), pady=(0, 1))
                    if note_idx == len(pacenote["notes"]) - 1:
                        note_down["state"] = "disabled"

                    def note_remove(note_idx=note_idx):
                        scroll = self.scroll_frame.get_scroll()
                        self.pacenotes[i]["notes"].pop(note_idx)
                        draw_pacenotes(
                            i
                        )
                        self.scroll_frame.set_scroll(scroll)

                    note_remove = ttk.Button(
                        pacenotes_frame, text="×", width=2,
                        command=note_remove, style="Danger.TButton")
                    note_remove.grid(
                        row=note_idx, column=3, sticky="nsew",
                        pady=(0, 1))

                for note_idx, t in enumerate(pacenote["notes"]):
                    create_entry(note_idx, t)

                def add_note(i=i):
                    scroll = self.scroll_frame.get_scroll()
                    self.pacenotes[i]["notes"].append("")
                    draw_pacenotes(
                        i
                    )
                    self.scroll_frame.set_scroll(scroll)
                add_button = ttk.Button(
                    pacenotes_frame,
                    text=f"＋  {self._tr('editor_add')}", command=add_note,
                    style="CompactAdd.TButton")
                add_button.grid(
                    row=len(pacenote["notes"]), column=1, columnspan=3,
                    sticky="ew", pady=(3, 0))
                self.pacenote_elements.append(pacenotes_frame)
                draw_playable_pacenotes(
                    i
                )

            def draw_playable_pacenotes(
                    i=i
            ):
                nonlocal combined_pacenotes_frame
                if combined_pacenotes_frame:
                    combined_pacenotes_frame.destroy()
                playable_tokens = self.acrally.combine_tokens(self.pacenotes[i]["notes"], self.token_sounds)
                combined_pacenotes_frame = ttk.Frame(
                    frame, style="Editor.TFrame")
                combined_pacenotes_frame.grid(row=i, column=4, padx=5, pady=5, sticky="w")
                for t in playable_tokens:
                    lbl = ttk.Label(
                        combined_pacenotes_frame, text=t,
                        style="Token.TLabel")
                    lbl.pack(anchor="w")
                    if pause := self.acrally.match_pause(t):
                        lbl["text"] = self._tr(
                            "editor_pause", seconds=pause)
                        lbl.configure(style="Pause.TLabel")
                    elif t not in self.token_sounds:
                        lbl.configure(style="Error.TLabel")
                def play(t=playable_tokens):
                    def thread_func(t, token_sounds):
                        stream = util.open_stream(next(iter(self.token_sounds.values()))[0])
                        self.acrally.play_tokens(stream, t, token_sounds)
                        time.sleep(1)
                        stream.close()
                    threading.Thread(
                        target=thread_func,
                        args=(t, self.token_sounds), daemon=True
                    ).start()
                play_btn = ttk.Button(
                    combined_pacenotes_frame,
                    text=f"▶  {self._tr('editor_play')}", command=play,
                    style="Success.TButton")
                play_btn.pack(anchor="w")
                self.pacenote_elements.append(play_btn)
                self.pacenote_elements.append(combined_pacenotes_frame)

            draw_pacenotes()

        last_frame = self.scroll_frame.scrollable_frame
        if len(self.pacenotes) > 350:
            tab_frame = ttk.Notebook(
                self.scroll_frame.scrollable_frame,
                style="Editor.TNotebook")
            tab_frame.pack(anchor="nw", side="left", fill="both", expand=True)
            page_no = 0
            for i, pacenote in enumerate(self.pacenotes):
                if i % 350 == 0:
                    last_frame = ttk.Frame(tab_frame, style="Editor.TFrame")
                    page_no += 1
                    tab_frame.add(
                        last_frame,
                        text=self._tr("editor_page", number=page_no))
                draw_pacenotes(last_frame, i, pacenote)
            self.pacenote_elements.append(tab_frame)
        else:
            for i, pacenote in enumerate(self.pacenotes):
                draw_pacenotes(last_frame, i, pacenote)

        def pacenote_add():
            scroll = self.scroll_frame.get_scroll()
            self.pacenotes.append({
                "distance": 0,
                "link_to_next": False,
                "notes": [""]
            })
            add_btn.grid(row=len(self.pacenotes))
            draw_pacenotes(last_frame, len(self.pacenotes) - 1, self.pacenotes[len(self.pacenotes) - 1])
            self.scroll_frame.set_scroll(scroll)

            if len(self.pacenotes) % 400 == 0:
                self.draw_pacenotes_frame()

        add_btn = ttk.Button(
            last_frame,
            text=f"＋  {self._tr('editor_add_pacenote')}",
            command=pacenote_add,
            style="Accent.TButton")
        add_btn.grid(row=len(self.pacenotes), column=1, columnspan=2, padx=5, pady=5)
        self.pacenote_elements.append(add_btn)

    def _get_hwnd(self):
        """Obtiene el identificador nativo de la ventana del editor."""
        hwnd = self.root.winfo_id()
        parent = ctypes.windll.user32.GetParent(hwnd)
        return parent or hwnd

    def _set_game_mode(self, enabled):
        """Activa o libera el editor sin afectar sus controles de mouse."""
        try:
            user32 = ctypes.windll.user32
            hwnd = self._get_hwnd()
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

            if enabled:
                user32.SetWindowLongW(
                    hwnd, GWL_EXSTYLE, ex_style | WS_EX_NOACTIVATE)
                user32.SetWindowPos(
                    hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
                self.focus_mode_button.configure(
                    text=f"●  {self._tr('editor_game_mode')}",
                    style="GameMode.TButton")
                self.game_mode = True

                # Devolver el control a la ventana que estaba activa antes
                # de entrar al editor (normalmente ACRally).
                if self._previous_foreground_hwnd:
                    user32.SetForegroundWindow(self._previous_foreground_hwnd)
            else:
                # Guardar el juego como destino antes de activar el editor.
                foreground = user32.GetForegroundWindow()
                if foreground and foreground != hwnd:
                    self._previous_foreground_hwnd = foreground

                user32.SetWindowLongW(
                    hwnd, GWL_EXSTYLE, ex_style & ~WS_EX_NOACTIVATE)
                self.focus_mode_button.configure(
                    text=f"●  {self._tr('editor_edit_mode')}",
                    style="Accent.TButton")
                self.game_mode = False
                self.root.lift()
                self.root.focus_force()
        except Exception:
            # En sistemas que no sean Windows, el editor sigue funcionando
            # como una ventana convencional.
            self.game_mode = enabled

    def _detach_native_owner(self):
        """Evita que Windows restaure el main al mostrar el editor."""
        try:
            user32 = ctypes.windll.user32
            hwnd = self._get_hwnd()
            # GWLP_HWNDPARENT = -8. Para ventanas de nivel superior este
            # valor controla el owner, no la jerarquía interna de Tk.
            setter = getattr(user32, "SetWindowLongPtrW",
                             user32.SetWindowLongW)
            setter(hwnd, -8, 0)
        except Exception:
            pass

    def _toggle_focus_mode(self):
        self._set_game_mode(not self.game_mode)

    def _refresh_language(self):
        """Actualiza todos los textos sin descartar las notas cargadas."""
        self.root.title(self._tr("editor_window_title"))
        self.header_label.configure(text=self._tr("editor_header"))
        self.stage_label.configure(text=self._tr("editor_stage"))
        self.voice_label.configure(text=self._tr("editor_voice"))
        self.load_button.configure(text=f"↻  {self._tr('editor_load')}")
        self.save_button.configure(text=f"✓  {self._tr('editor_save')}")
        self.new_button.configure(text=f"＋  {self._tr('editor_new')}")

        mode_key = "editor_game_mode" if self.game_mode else "editor_edit_mode"
        self.focus_mode_button.configure(text=f"●  {self._tr(mode_key)}")

        if self.pacenotes is not None:
            scroll = self.scroll_frame.get_scroll()
            self.draw_pacenotes_frame()
            self.scroll_frame.set_scroll(scroll)

    def _watch_language(self):
        """Sincroniza el editor si el idioma cambia desde main.py."""
        try:
            config = yaml.safe_load(
                open("config.yml", encoding="utf-8")) or {}
            new_lang = config.get("lang", "en")
            if new_lang != self.lang:
                self.lang = new_lang
                self._refresh_language()
        except (FileNotFoundError, yaml.YAMLError):
            pass

        if self.root and self.root.winfo_exists():
            self.root.after(1000, self._watch_language)

    def _style_native_title_bar(self):
        """Aplica a la barra de Windows la paleta oscura del overlay."""
        try:
            hwnd = self._get_hwnd()
            dwmapi = ctypes.windll.dwmapi

            # Modo oscuro para botones de minimizar, maximizar y cerrar.
            dark_mode = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))

            # Mantener esquinas rectas. Es una preferencia nativa de Windows
            # y no requiere máscaras, regiones ni redibujado adicional.
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

            # Windows 11: borde, fondo de título y texto respectivamente.
            for attribute, color in (
                    (34, BORDER), (35, BG2), (36, FG)):
                native_color = colorref(color)
                dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(native_color),
                    ctypes.sizeof(native_color))
        except Exception:
            pass

    def _align_visible_left(self):
        """Alinea el borde visible con el overlay, compensando el marco DWM."""
        if self._desired_outer_left is None:
            return
        try:
            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

            hwnd = self._get_hwnd()
            window_rect = RECT()
            visible_rect = RECT()
            user32 = ctypes.windll.user32
            user32.GetWindowRect(hwnd, ctypes.byref(window_rect))
            # DWMWA_EXTENDED_FRAME_BOUNDS = 9: borde realmente visible, sin
            # la sombra/margen invisible que Windows reserva para redimensionar.
            ctypes.windll.dwmapi.DwmGetWindowAttribute(
                hwnd, 9, ctypes.byref(visible_rect), ctypes.sizeof(visible_rect))
            correction = int(self._desired_outer_left - visible_rect.left)
            if correction:
                user32.SetWindowPos(
                    hwnd, 0, window_rect.left + correction, window_rect.top,
                    0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)
        except Exception:
            pass

    def main(self, preset_stage=None, preset_voice=None, preset_lang=None,
             preset_position=None, preset_width=None, preset_height=None,
             preset_alpha=None, parent=None, run_mainloop=True,
             on_close=None, preset_foreground_hwnd=None):
        try:
            config = yaml.safe_load(
                open("config.yml", encoding="utf-8")) or {}
        except (FileNotFoundError, yaml.YAMLError):
            config = {}
        self.lang = preset_lang or config.get("lang", "en")

        self._previous_foreground_hwnd = preset_foreground_hwnd
        if (self._previous_foreground_hwnd is None
                and hasattr(ctypes, "windll")):
            self._previous_foreground_hwnd = (
                ctypes.windll.user32.GetForegroundWindow())
        self._on_close_callback = on_close
        self.root = tk.Toplevel(parent)
        self.root.withdraw()
        self.root.title(self._tr("editor_window_title"))
        self.root.iconbitmap(util.resource_path("icon.ico"))
        # ── EDITAR AQUÍ: TAMAÑO INICIAL DEL EDITOR ─────────────────
        # Es el equivalente a width/height en CSS. Después el usuario puede
        # redimensionarlo manualmente porque es una ventana nativa.
        width = int(preset_width or config.get("editor_width", 980))
        height = int(preset_height or config.get("editor_height", 680))
        width = max(800, min(1800, width))
        height = max(420, min(1100, height))
        if preset_position:
            x, y = preset_position
        else:
            x, y = 60, 220
        self.root.geometry(f"{width}x{height}{int(x):+d}{int(y):+d}")
        self._desired_outer_left = int(x)
        self.root.minsize(800, 500)
        self.root.resizable(True, True)
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", True)
        alpha = float(preset_alpha if preset_alpha is not None
                      else config.get("editor_alpha", 1.0))
        self.root.attributes("-alpha", max(0.60, min(1.0, alpha)))
        self.root.protocol("WM_DELETE_WINDOW", self._close_editor)
        self.root.bind("<Configure>", self._schedule_geometry_save, add="+")
        self.root.bind("<MouseWheel>", self._on_mousewheel, add="+")
        configure_editor_styles(self.root)

        top_frame = ttk.Frame(
            self.root, padding=(16, 12), style="Toolbar.TFrame")
        top_frame.pack(fill="x")
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)

        self.header_label = ttk.Label(
            top_frame, text=self._tr("editor_header"),
            style="Title.TLabel"
        )
        self.header_label.grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        self.focus_mode_button = ttk.Button(
            top_frame, text=f"●  {self._tr('editor_game_mode')}",
            command=self._toggle_focus_mode, style="GameMode.TButton")
        self.focus_mode_button.grid(
            row=0, column=4, sticky="e", pady=(0, 8))

        separator = tk.Frame(top_frame, bg=BORDER, height=1)
        separator.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(0, 10))

        self.stage_label = ttk.Label(
            top_frame, text=self._tr("editor_stage"),
            style="Toolbar.TLabel"
        )
        self.stage_label.grid(row=2, column=0, sticky="w", padx=(0, 8))
        self.voice_label = ttk.Label(
            top_frame, text=self._tr("editor_voice"),
            style="Toolbar.TLabel"
        )
        self.voice_label.grid(row=2, column=1, sticky="w", padx=(0, 8))

        stages = sorted(
            x.replace(".yml", "") for x in os.listdir("pacenotes")
            if x.endswith(".yml"))
        voices = sorted(
            x for x in os.listdir("voices")
            if os.path.isdir(os.path.join("voices", x)))

        self.pacenotes_combo = ttk.Combobox(
            top_frame, values=stages, width=30,
            style="Editor.TCombobox", state="readonly")
        self.voices_combo = ttk.Combobox(
            top_frame, values=voices, width=20,
            style="Editor.TCombobox", state="readonly")

        # Pre-seleccionar si se pasaron parámetros, si no usar el primero
        if preset_stage and preset_stage in stages:
            self.pacenotes_combo.set(preset_stage)
        else:
            self.pacenotes_combo.current(0)

        if preset_voice and preset_voice in voices:
            self.voices_combo.set(preset_voice)
        else:
            self.voices_combo.current(0)

        self.pacenotes_combo.grid(
            row=3, column=0, sticky="ew", padx=(0, 8), pady=(3, 0))
        self.voices_combo.grid(
            row=3, column=1, sticky="ew", padx=(0, 12), pady=(3, 0))

        self.load_button = ttk.Button(
            top_frame, text=f"↻  {self._tr('editor_load')}",
            command=self.load_pacenotes,
            style="Accent.TButton")
        self.load_button.grid(row=3, column=2, padx=(0, 6), pady=(3, 0))

        self.save_button = ttk.Button(
            top_frame, text=f"✓  {self._tr('editor_save')}",
            command=self.save_pacenotes,
            style="Success.TButton")
        self.save_button.grid(row=3, column=3, padx=6, pady=(3, 0))
        self.save_button["state"] = "disabled"

        self.new_button = ttk.Button(
            top_frame, text=f"＋  {self._tr('editor_new')}",
            command=self.new_pacenotes,
            style="Editor.TButton")
        self.new_button.grid(row=3, column=4, padx=(6, 0), pady=(3, 0))

        # Scrollable frame
        content_border = tk.Frame(self.root, bg=BORDER, height=1)
        content_border.pack(fill="x")
        self.scroll_frame = ScrollableFrame(
            self.root, style="Editor.TFrame", padding=(10, 8))
        self.scroll_frame.pack(fill="both", expand=True)

        # Mostrar inicialmente sin tomar el foco del juego. El botón de la
        # cabecera permite habilitar el teclado cuando sea necesario editar.
        self.root.update_idletasks()
        self._detach_native_owner()
        self._set_game_mode(True)
        # Mostrar sin activación: deiconify() puede restaurar el main y robar
        # el foco del juego cuando la ventana tiene un owner minimizado.
        try:
            ctypes.windll.user32.ShowWindow(
                self._get_hwnd(), 4)  # SW_SHOWNOACTIVATE
        except Exception:
            self.root.deiconify()
        self._style_native_title_bar()
        self._set_game_mode(True)
        self.root.after(100, self._style_native_title_bar)
        self.root.after(120, self._align_visible_left)
        self.root.after(300, self._align_visible_left)
        self.root.after(1000, self._watch_language)
        self.root.after(300, lambda: setattr(self, "_geometry_ready", True))

        if run_mainloop:
            self.root.mainloop()

if __name__ == "__main__":
    editor = Editor()
    editor.main()
