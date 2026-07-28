"""Lectura liviana y opcional de un freno de mano mediante pygame."""

import os
import threading

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "hide")
os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")


class Handbrake:
    _pygame = None
    _joysticks = None
    _lock = threading.RLock()

    @classmethod
    def _module(cls):
        if cls._pygame is None:
            import pygame
            cls._pygame = pygame
        return cls._pygame

    @classmethod
    def get_joysticks(cls):
        with cls._lock:
            pygame = cls._module()
            if not pygame.get_init():
                pygame.init()
            if not pygame.joystick.get_init():
                pygame.joystick.init()
            if cls._joysticks is None:
                cls._joysticks = []
                for index in range(pygame.joystick.get_count()):
                    joystick = pygame.joystick.Joystick(index)
                    joystick.init()
                    cls._joysticks.append(joystick)
            return cls._joysticks

    @classmethod
    def device_names(cls):
        return [joystick.get_name() for joystick in cls.get_joysticks()]

    def __init__(self, config):
        joysticks = self.get_joysticks()
        index = int(config.get("device", 0))
        if index < 0 or index >= len(joysticks):
            raise RuntimeError("El dispositivo de freno de mano no está conectado")
        self.joystick = joysticks[index]
        self.input_type = config.get("type", "axis")
        self.number = int(config.get("number", 0))
        self.released = float(config.get("released", -1.0))
        self.pressed = float(config.get("pressed", 1.0))
        self.threshold = float(config.get("threshold", 0.7))

    def get_value(self):
        with self._lock:
            pygame = self._module()
            pygame.event.pump()
            if self.input_type == "button":
                return float(self.joystick.get_button(self.number))
            return float(self.joystick.get_axis(self.number))

    def get_pressed(self):
        value = self.get_value()
        trigger = self.released + (self.pressed - self.released) * self.threshold
        if self.pressed >= self.released:
            return value >= trigger
        return value <= trigger

    @classmethod
    def snapshot(cls, device):
        with cls._lock:
            pygame = cls._module()
            joystick = cls.get_joysticks()[device]
            pygame.event.pump()
            values = {}
            for number in range(joystick.get_numaxes()):
                values[("axis", number)] = float(joystick.get_axis(number))
            for number in range(joystick.get_numbuttons()):
                values[("button", number)] = float(joystick.get_button(number))
            return values

    @classmethod
    def read_input(cls, device, input_type, number):
        """Lee un botón o eje concreto de forma segura entre hilos."""
        with cls._lock:
            pygame = cls._module()
            joystick = cls.get_joysticks()[device]
            pygame.event.pump()
            if input_type == "button":
                return float(joystick.get_button(number))
            return float(joystick.get_axis(number))

    @classmethod
    def snapshot_all(cls):
        return [cls.snapshot(index)
                for index in range(len(cls.get_joysticks()))]

    @staticmethod
    def strongest_change(released, pressed):
        candidates = []
        for key, pressed_value in pressed.items():
            released_value = released.get(key, pressed_value)
            candidates.append((abs(pressed_value - released_value), key,
                               released_value, pressed_value))
        if not candidates:
            return None
        change, key, released_value, pressed_value = max(candidates)
        if change < 0.35:
            return None
        return {
            "type": key[0], "number": key[1],
            "released": released_value, "pressed": pressed_value,
            "threshold": 0.7,
        }

    @classmethod
    def shutdown(cls):
        """Libera joysticks y SDL si pygame llegó a inicializarse."""
        with cls._lock:
            pygame = cls._pygame
            joysticks = cls._joysticks or []
            for joystick in joysticks:
                try:
                    joystick.quit()
                except Exception:
                    pass
            cls._joysticks = None

            if pygame is not None:
                try:
                    if pygame.joystick.get_init():
                        pygame.joystick.quit()
                except Exception:
                    pass
                try:
                    if pygame.get_init():
                        pygame.quit()
                except Exception:
                    pass
            cls._pygame = None

    @classmethod
    def strongest_change_all(cls, released_states, pressed_states):
        best = None
        best_change = 0.0
        for device, (released, pressed) in enumerate(
                zip(released_states, pressed_states)):
            result = cls.strongest_change(released, pressed)
            if result is None:
                continue
            key = (result["type"], result["number"])
            change = abs(pressed[key] - released[key])
            if change > best_change:
                best_change = change
                best = result
                best["device"] = device
        return best
