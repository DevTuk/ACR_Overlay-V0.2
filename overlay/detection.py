"""Detección automática de ACRally y lanzamiento de la etapa resuelta."""

from ui_theme import ERROR as RED

from .constants import POLL_INTERVAL
from .helpers import resolve_stage


class OverlayDetectionMixin:
    def _detect_loop(self):
        from sharedmemory import SharedMemory, ACC_STATUS
        import psutil

        asm = None
        self._set_ui(self._tr("status_waiting"), "")

        try:
            while not self._stop_event.is_set():
                game_running = any(
                    process.info.get("name") == "acr.exe"
                    for process in psutil.process_iter(attrs=["name"])
                )
                if game_running:
                    break
                if self._stop_event.wait(1.0):
                    return

            if self._stop_event.is_set():
                return

            self._set_ui(self._tr("status_detected"), "")
            if self._stop_event.wait(3.0):
                return

            try:
                asm = SharedMemory()
            except Exception as exc:
                self._set_ui(self._tr("status_error", error=exc), "")
                return

            self._last_status = None

            while not self._stop_event.wait(POLL_INTERVAL):
                try:
                    sm = asm.read_shared_memory()
                except Exception as exc:
                    self._set_ui(self._tr("status_error", error=exc), "")
                    continue

                if sm is None:
                    self._set_ui(self._tr("status_running_stage"), "")
                    self._post_ui(self.odometer_var.set, "0.000 km")
                    continue

                dist_km = sm.Graphics.distance_traveled / 1000.0
                self._post_ui(self.odometer_var.set, f"{dist_km:.3f} km")

                track = str(sm.Static.track).strip("\0").strip()
                status = sm.Graphics.status

                if (self._cur_stage
                        and track == self._last_track
                        and status != self._last_status):
                    self._last_status = status
                    if status == ACC_STATUS.ACC_PAUSE:
                        self._set_ui(
                            f"{self._tr('status_paused')} {self._cur_stage}",
                            "",
                        )
                    elif status == ACC_STATUS.ACC_LIVE:
                        self._set_ui(
                            f"{self._tr('status_running')} {self._cur_stage}",
                            "",
                        )

                if not track:
                    self._set_ui(self._tr("status_running_stage"), "")
                    continue

                if track == self._last_track:
                    continue

                self._last_status = status
                self._raw_track = track
                self._post_ui(self.raw_track_var.set, track)

                resolved, confidence = resolve_stage(
                    track, self.stage_map, self.available)

                if not resolved:
                    self._set_ui(self._tr("status_no_map"), f'"{track}"')
                    self._last_track = track
                    continue

                self._last_track = track

                if confidence < 1.0:
                    self._write_stage_map(track, resolved)
                    label = self._tr(
                        "status_auto",
                        pct=int(confidence * 100),
                        stage=resolved,
                    )
                else:
                    label = f"{self._tr('status_running')} {resolved}"

                self._cur_stage = resolved
                self._set_ui(self._tr("status_loading"), resolved)
                self._post_ui(self._launch, resolved, label)
        finally:
            if asm is not None:
                try:
                    asm.close()
                except Exception:
                    pass

    def _launch(self, stage, label=None):
        if self._closed:
            return
        self._manual_override = False
        self.start_btn.config(text="■", bg=RED, activebackground="#c0392b")
        self._set_ui(
            label or f"{self._tr('status_running')} {stage}", "")
        self.main.start_stage(stage)

    def _set_ui(self, line1, line2=""):
        if self._closed:
            return
        full = f"{line1}  {line2}".strip() if line2 else line1
        self._post_ui(self.main.status_var.set, line1)
        self._post_ui(self.main.stage_var.set, line2)
        self._post_ui(self.ov_status_var.set, full)
