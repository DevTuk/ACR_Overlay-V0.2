"""Configuración y captura del atajo global del overlay.

El módulo mantiene separados tres conceptos:

* el formato persistido en ``config.yml``;
* la representación legible que se muestra en la interfaz;
* la conversión a modificadores y virtual keys de Win32.

Los controles de joystick reutilizan la lectura liviana de ``handbrake.py`` y
se activan únicamente al pasar de liberado a presionado. De ese modo un botón
mantenido no abre y cierra el overlay repetidamente.
"""

from __future__ import annotations

import ctypes
import os
from typing import Any, Mapping


DEFAULT_SHORTCUT: dict[str, Any] = {
    "type": "keyboard",
    "modifiers": ["ctrl", "alt"],
    "key": "F9",
    "vk": 0x78,
}

MODIFIER_FLAGS = {
    "alt": 0x0001,
    "ctrl": 0x0002,
    "shift": 0x0004,
    "win": 0x0008,
}

_MODIFIER_VKS = {
    "shift": 0x10,
    "ctrl": 0x11,
    "alt": 0x12,
    "win": (0x5B, 0x5C),
}

_MODIFIER_KEYSYMS = {
    "Shift_L", "Shift_R", "Control_L", "Control_R",
    "Alt_L", "Alt_R", "Meta_L", "Meta_R", "Super_L", "Super_R",
}

_KEY_NAMES = {
    "Return": "Enter",
    "Escape": "Esc",
    "BackSpace": "Backspace",
    "Tab": "Tab",
    "space": "Espacio",
    "Delete": "Supr",
    "Insert": "Insert",
    "Home": "Inicio",
    "End": "Fin",
    "Prior": "Page Up",
    "Next": "Page Down",
    "Left": "←",
    "Right": "→",
    "Up": "↑",
    "Down": "↓",
    "Caps_Lock": "Caps Lock",
    "Num_Lock": "Num Lock",
    "Scroll_Lock": "Scroll Lock",
    "Print": "Print Screen",
    "Pause": "Pause",
}


def normalize_shortcut(value: object) -> dict[str, Any]:
    """Devuelve una copia válida y compatible del atajo persistido."""
    if not isinstance(value, Mapping):
        return dict(DEFAULT_SHORTCUT)

    shortcut_type = str(value.get("type", "keyboard")).lower()
    if shortcut_type == "joystick":
        try:
            return {
                "type": "joystick",
                "device": max(0, int(value.get("device", 0))),
                "device_name": str(value.get("device_name", "")),
                "input_type": (
                    "button" if value.get("input_type", value.get("control_type")) == "button"
                    else "axis"
                ),
                "number": max(0, int(value.get("number", 0))),
                "released": float(value.get("released", 0.0)),
                "pressed": float(value.get("pressed", 1.0)),
                "threshold": min(0.95, max(0.05, float(value.get("threshold", 0.7)))),
            }
        except (TypeError, ValueError):
            return dict(DEFAULT_SHORTCUT)

    try:
        vk = int(value.get("vk", DEFAULT_SHORTCUT["vk"]))
    except (TypeError, ValueError):
        vk = int(DEFAULT_SHORTCUT["vk"])
    if not 1 <= vk <= 0xFF:
        vk = int(DEFAULT_SHORTCUT["vk"])

    raw_modifiers = value.get("modifiers", DEFAULT_SHORTCUT["modifiers"])
    if not isinstance(raw_modifiers, (list, tuple)):
        raw_modifiers = []
    modifiers = [
        name for name in ("ctrl", "alt", "shift", "win")
        if name in {str(item).lower() for item in raw_modifiers}
    ]
    key = str(value.get("key") or virtual_key_name(vk))
    return {
        "type": "keyboard",
        "modifiers": modifiers,
        "key": key,
        "vk": vk,
    }


def shortcut_display(
    shortcut: object,
    *,
    device_names: list[str] | None = None,
    button_word: str = "Botón",
    axis_word: str = "Eje",
) -> str:
    """Genera el texto corto mostrado en el main y en el overlay."""
    value = normalize_shortcut(shortcut)
    if value["type"] == "keyboard":
        labels = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win"}
        parts = [labels[name] for name in value["modifiers"]]
        parts.append(str(value["key"]))
        return "+".join(parts)

    device_index = int(value["device"])
    device_name = value.get("device_name", "")
    if device_names and 0 <= device_index < len(device_names):
        device_name = device_names[device_index]
    if not device_name:
        device_name = f"Dispositivo {device_index + 1}"
    if len(device_name) > 32:
        device_name = device_name[:31].rstrip() + "…"

    number = int(value["number"]) + 1
    if value["input_type"] == "button":
        control = f"{button_word} {number}"
    else:
        direction = "+" if float(value["pressed"]) >= float(value["released"]) else "−"
        control = f"{axis_word} {number} {direction}"
    return f"{device_name} · {control}"


def win32_hotkey_values(shortcut: object) -> tuple[int, int]:
    """Convierte un atajo de teclado a ``(modifiers, virtual_key)``."""
    value = normalize_shortcut(shortcut)
    if value["type"] != "keyboard":
        raise ValueError("El atajo configurado no es de teclado")
    modifiers = 0
    for name in value["modifiers"]:
        modifiers |= MODIFIER_FLAGS[name]
    return modifiers, int(value["vk"])


def joystick_input_active(shortcut: object, current_value: float) -> bool:
    """Indica si el control ya cruzó su umbral de activación."""
    value = normalize_shortcut(shortcut)
    released = float(value.get("released", 0.0))
    pressed = float(value.get("pressed", 1.0))
    threshold = float(value.get("threshold", 0.7))
    trigger = released + (pressed - released) * threshold
    if pressed >= released:
        return current_value >= trigger
    return current_value <= trigger


def keyboard_shortcut_from_event(event: Any) -> dict[str, Any] | None:
    """Convierte un ``<KeyPress>`` de Tk en un atajo persistible.

    Las teclas modificadoras por sí solas se ignoran. En Windows se consulta
    el estado nativo para capturar correctamente Alt y la tecla Windows, cuyo
    estado no siempre aparece de forma consistente en ``event.state``.
    """
    keysym = str(getattr(event, "keysym", ""))
    if not keysym or keysym in _MODIFIER_KEYSYMS:
        return None

    try:
        vk = int(getattr(event, "keycode"))
    except (TypeError, ValueError):
        return None
    if not 1 <= vk <= 0xFF:
        return None

    state = int(getattr(event, "state", 0) or 0)
    pressed = {
        "shift": bool(state & 0x0001),
        "ctrl": bool(state & 0x0004),
        "alt": bool(state & 0x0008 or state & 0x20000),
        "win": bool(state & 0x0040),
    }

    if os.name == "nt":
        try:
            user32 = ctypes.windll.user32
            for name, native_vks in _MODIFIER_VKS.items():
                if not isinstance(native_vks, tuple):
                    native_vks = (native_vks,)
                pressed[name] = pressed[name] or any(
                    bool(user32.GetKeyState(native_vk) & 0x8000)
                    for native_vk in native_vks
                )
        except Exception:
            pass

    modifiers = [
        name for name in ("ctrl", "alt", "shift", "win")
        if pressed[name]
    ]
    return {
        "type": "keyboard",
        "modifiers": modifiers,
        "key": _KEY_NAMES.get(keysym, _clean_keysym(keysym)),
        "vk": vk,
    }


def virtual_key_name(vk: int) -> str:
    """Obtiene un nombre estable aun fuera de Windows."""
    if 0x70 <= vk <= 0x87:
        return f"F{vk - 0x6F}"
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    known = {
        0x08: "Backspace", 0x09: "Tab", 0x0D: "Enter", 0x1B: "Esc",
        0x20: "Espacio", 0x21: "Page Up", 0x22: "Page Down",
        0x23: "Fin", 0x24: "Inicio", 0x25: "←", 0x26: "↑",
        0x27: "→", 0x28: "↓", 0x2D: "Insert", 0x2E: "Supr",
    }
    return known.get(vk, f"VK {vk}")


def resolve_joystick_device(shortcut: object, device_names: list[str]) -> int:
    """Resuelve el dispositivo guardado, priorizando su nombre estable."""
    value = normalize_shortcut(shortcut)
    saved_name = str(value.get("device_name", ""))
    if saved_name:
        try:
            return device_names.index(saved_name)
        except ValueError:
            pass
    index = int(value.get("device", 0))
    if 0 <= index < len(device_names):
        return index
    raise RuntimeError("El dispositivo configurado no está conectado")


def _clean_keysym(keysym: str) -> str:
    if len(keysym) == 1:
        return keysym.upper()
    if keysym.startswith("KP_"):
        return "Numpad " + keysym[3:].replace("_", " ")
    return keysym.replace("_", " ")
