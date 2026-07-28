"""Sistema visual compartido por todas las ventanas de la aplicación.

GUÍA RÁPIDA PARA EDITAR (pensada si venís de CSS/Tailwind)
======================================================================
Este archivo funciona como un ``tailwind.config.js`` muy pequeño:

* Los colores de abajo son equivalentes a variables CSS o tokens del tema.
* Las constantes ``FONT_*`` son la escala tipográfica.
* Las constantes ``PAD_*`` son la escala de spacing.
* Cambiar un valor acá modifica main, overlay y editor al mismo tiempo.

Los colores usan el formato hexadecimal habitual de CSS: ``#RRGGBB``.
Después de editar este archivo podés probar con ``python main.py``.
"""

import tkinter as tk
from tkinter import ttk

# ── EDITAR AQUÍ: PALETA ──────────────────────────────────────────
# BG / BG2 / BG3 se parecen a bg-slate-950/900/800 de Tailwind:
# BG = fondo principal, BG2 = barras/inputs, BG3 = botones/paneles.
BG = "#0f0f17"
BG2 = "#1a1a24"
BG3 = "#252530"
BORDER = "#262633"   # Bordes y divisores.
FG = "#f0f0f5"       # Texto principal.
MUTED = "#7a7a8a"    # Texto secundario/deshabilitado.
ACCENT = "#3d9eff"   # Azul para acciones importantes.
SUCCESS = "#3db366"  # Verde: iniciar/guardar/estado correcto.
WARN = "#f5a623"     # Naranja: avisos y atajo.
ERROR = "#ef5a5a"    # Rojo: cerrar/eliminar/error.

# ── EDITAR AQUÍ: TIPOGRAFÍA ──────────────────────────────────────
# Estructura de una fuente Tkinter: ("Familia", tamaño, "peso").
# Si una fuente no existe en Windows, Tkinter usa una alternativa.
FONT_DISPLAY = ("Segoe UI", 20, "bold")
FONT_HEADING = ("Segoe UI Semibold", 9)
FONT_BODY = ("Segoe UI", 8)
FONT_BODY_BOLD = ("Segoe UI Semibold", 8)
FONT_CAPTION = ("Segoe UI", 7)
FONT_MONO = ("Consolas", 8)

# ── EDITAR AQUÍ: ESPACIADO ───────────────────────────────────────
# Equivalente aproximado: PAD_XS=p-1, PAD_SM=p-2, PAD_MD=p-3...
# Tkinter mide estos valores en píxeles.
PAD_XS = 4
PAD_SM = 8
PAD_MD = 12
PAD_LG = 16
PAD_XL = 20


def mix_colors(color1, color2, ratio):
    """Mezcla dos colores hexadecimales."""
    ratio = max(0.0, min(1.0, ratio))
    c1 = int(color1.lstrip("#"), 16)
    c2 = int(color2.lstrip("#"), 16)
    channels = []
    for shift in (16, 8, 0):
        first = (c1 >> shift) & 0xff
        second = (c2 >> shift) & 0xff
        channels.append(round(first * (1 - ratio) + second * ratio))
    return "#{:02x}{:02x}{:02x}".format(*channels)


def refined_button(parent, text, command, *, bg=BG3, fg=FG, width=None,
                   font=FONT_BODY_BOLD, hover_bg=None, **kwargs):
    """Crea un botón plano reutilizable.

    Es similar a un componente ``<Button />`` de React:
    ``parent`` es el contenedor, ``command`` equivale a ``onClick`` y
    ``hover_bg`` sería el color usado por ``hover:bg-*`` en Tailwind.
    """
    if hover_bg is None:
        hover_bg = mix_colors(bg, ACCENT, 0.22)
    options = dict(
        text=text, command=command, bg=bg, fg=fg, bd=0,
        relief="flat", font=font, cursor="hand2",
        activebackground=hover_bg, activeforeground=FG,
        disabledforeground=MUTED, highlightthickness=0,
    )
    if width is not None:
        options["width"] = width
    options.update(kwargs)
    button = tk.Button(parent, **options)

    def enter(_event):
        if str(button.cget("state")) != "disabled":
            button.configure(bg=hover_bg)

    def leave(_event):
        if str(button.cget("state")) != "disabled":
            button.configure(bg=bg)

    button.bind("<Enter>", enter, add="+")
    button.bind("<Leave>", leave, add="+")
    return button


def configure_ttk(root):
    """Aplica el tema a Combobox y otros controles ttk nativos.

    ``style.configure`` define el estado normal y ``style.map`` define
    variantes como ``:hover``, ``:focus`` o ``:disabled`` en CSS.
    """
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        "TCombobox", fieldbackground=BG2, background=BG3,
        foreground=FG, arrowcolor=WARN, bordercolor=BORDER,
        lightcolor=BORDER, darkcolor=BORDER, padding=5,
        font=FONT_BODY)
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", BG2), ("focus", BG2)],
        foreground=[("readonly", FG)],
        bordercolor=[("focus", ACCENT)],
        arrowcolor=[("active", ACCENT)])
    style.configure(
        "TCheckbutton", background=BG, foreground=FG,
        focuscolor=BG, font=FONT_CAPTION)
    style.map(
        "TCheckbutton", background=[("active", BG)],
        foreground=[("active", ACCENT)])
    root.option_add("*TCombobox*Listbox.background", BG2)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", BG)
    return style
