"""Controles de voz, anticipación y volumen general."""

from .helpers import set_app_volume


class OverlayControlsMixin:
    def _voice_prev(self):
        if not self.voice_dirs:
            return
        self.voice_index = (self.voice_index - 1) % len(self.voice_dirs)
        self._apply_voice()

    def _voice_next(self):
        if not self.voice_dirs:
            return
        self.voice_index = (self.voice_index + 1) % len(self.voice_dirs)
        self._apply_voice()

    def _apply_voice(self):
        voice = self.voice_dirs[self.voice_index]
        self.voice_label_var.set(voice)
        self._save("voice", voice)
        # Reiniciar desde la distancia actual para no repetir notas ya pasadas
        if self.main.acrally and self._cur_stage:
            current_copilot = self.main.acrally
            current_dist = current_copilot.distance
            # La distancia por sí sola no expresa si ya se largó: todavía
            # puede valer 0.0. Conservar explícitamente el estado evita que
            # cambiar de voz deje la nueva instancia esperando otra cuenta o
            # el botón Guardar configuración.
            resume_started = bool(
                current_copilot.started
                or current_copilot.started_event.is_set()
            )
            self.main.start_stage(
                self._cur_stage,
                start_from_distance=current_dist,
                resume_started=resume_started,
            )

    def _step_timing(self, delta):
        v = round(max(0.1, min(10.0, self.dist_var.get() + delta)), 1)
        self.dist_var.set(v)
        self.dist_label_var.set(f"{v:.1f}s")
        self._save("call_distance", v)
        if self.main.acrally:
            self.main.acrally.call_earliness = v

    def _on_volume_change(self, value):
        percent = max(0.0, min(100.0, float(value)))
        # Curva perceptual: ofrece más control en volúmenes bajos y medios.
        # 75% -> 56%, 50% -> 25%, 25% -> 6% de amplitud real.
        scalar = (percent / 100.0) ** 2
        set_app_volume(scalar)
        self.volume_label_var.set(f"{int(round(percent))}%")
