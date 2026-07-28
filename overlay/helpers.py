"""Funciones puras y adaptadores externos usados por el overlay."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import yaml


def load_stage_map(path: str | Path = "stage_map.yml") -> dict[str, str]:
    """Carga el mapa de nombres de ACRally y normaliza sus claves."""
    try:
        with open(path, encoding="utf-8") as stream:
            raw = yaml.safe_load(stream) or {}
    except FileNotFoundError:
        return {}
    return {str(key).lower(): value for key, value in raw.items()}


def resolve_voice(configured: str, available: Iterable[str]) -> str:
    """Devuelve una única voz válida para UI, config y motor de audio."""
    voices = list(available)
    if configured in voices:
        return configured
    return voices[0] if voices else ""


def _similarity(left: str, right: str) -> float:
    """Compara nombres de tramo ignorando acentos, prefijos y separadores."""
    def normalize(value: str) -> set[str]:
        value = value.lower()
        for old, new in [
            ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
            ("ú", "u"), ("ü", "u"), ("ñ", "n"), ("è", "e"),
            ("à", "a"), ("ê", "e"), ("î", "i"), ("ô", "o"),
            ("-", " "), ("_", " "),
        ]:
            value = value.replace(old, new)
        words = value.split()
        country_prefixes = {
            "gales", "grecia", "alsacia", "alemania", "francia",
            "italia", "montecarlo", "monte", "carlo",
        }
        if words and words[0] in country_prefixes:
            words = words[1:]
        return set(words)

    set_left, set_right = normalize(left), normalize(right)
    if not set_left or not set_right:
        return 0.0
    return len(set_left & set_right) / len(set_left | set_right)


def resolve_stage(
    track: str,
    stage_map: dict[str, str],
    available: Iterable[str],
) -> tuple[str | None, float]:
    """Resuelve un nombre del juego contra los YAML de pacenotes disponibles."""
    available_set = set(available)
    mapped = stage_map.get(track.lower())
    if mapped and mapped in available_set:
        return mapped, 1.0

    track_lower = track.lower()
    for name in available_set:
        if name.lower() == track_lower:
            return name, 1.0

    best_name, best_score = None, 0.0
    for name in available_set:
        score = _similarity(track, name)
        if score > best_score:
            best_score, best_name = score, name

    if best_score >= 0.4 and best_name:
        return best_name, best_score
    return None, 0.0


def get_app_volume() -> float:
    """Devuelve el volumen de la sesión de audio de este proceso."""
    current_pid = os.getpid()
    try:
        from pycaw import pycaw
        sessions = pycaw.AudioUtilities.GetAllSessions()
        for session in sessions:
            if session.Process and session.Process.pid == current_pid:
                endpoint = session._ctl.QueryInterface(pycaw.ISimpleAudioVolume)
                return endpoint.GetMasterVolume()
    except Exception:
        pass
    return 1.0


def set_app_volume(volume: float) -> bool:
    """Modifica el volumen de la sesión de audio de este proceso."""
    volume = max(0.0, min(1.0, volume))
    current_pid = os.getpid()
    try:
        from pycaw import pycaw
        sessions = pycaw.AudioUtilities.GetAllSessions()
        for session in sessions:
            if session.Process and session.Process.pid == current_pid:
                endpoint = session._ctl.QueryInterface(pycaw.ISimpleAudioVolume)
                endpoint.SetMasterVolume(volume, None)
                return True
    except Exception:
        pass
    return False
