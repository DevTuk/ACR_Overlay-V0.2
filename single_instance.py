"""Bloqueo de instancia única para Windows.

Evita que un doble clic, un acceso directo duplicado o una instancia anterior
lancen dos copias del overlay al mismo tiempo.
"""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes


ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = r"Local\ACRallyPacenoteOverlay_Dienqn_0114"


class SingleInstance:
    """Mantiene un mutex de Windows durante toda la vida de la aplicación."""

    def __init__(self, name: str = MUTEX_NAME) -> None:
        self.name = name
        self.handle: int | None = None
        self.already_running = False

        if os.name != "nt":
            return

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = (
            ctypes.c_void_p,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        )
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.CreateMutexW(None, False, name)
        if not handle:
            raise ctypes.WinError()

        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            self.already_running = True
            return

        self.handle = int(handle)

    def close(self) -> None:
        handle = self.handle
        self.handle = None
        if handle and os.name == "nt":
            try:
                ctypes.windll.kernel32.CloseHandle(handle)
            except Exception:
                pass
