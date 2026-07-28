"""Mapeo de tramos y control manual de reproducción."""

import yaml

from ui_theme import SUCCESS as GREEN, ERROR as RED


class OverlayStageMixin:
    def _write_stage_map(self, raw_track, chosen):
        try:
            raw = yaml.safe_load(open("stage_map.yml", encoding="utf-8")) or {}
        except FileNotFoundError:
            raw = {}
        raw[raw_track] = chosen
        yaml.dump(raw, open("stage_map.yml", "w", encoding="utf-8"),
                  allow_unicode=True, default_flow_style=False)
        self.stage_map[raw_track.lower()] = chosen

    def _save_mapping_manual(self):
        track = self._raw_track
        chosen = self.manual_stage_var.get()

        if not track:
            self._set_ui(self._tr("status_no_track"), "")
            return
        if not chosen:
            self._set_ui(self._tr("status_no_stage"), "")
            return

        self._write_stage_map(track, chosen)
        self._last_track = None  # fuerza al loop a re-evaluar este mismo track
        self._set_ui(
            self._tr("status_linked", track=track, stage=chosen), "")

    def _on_manual_start(self):
        if self.main.acrally:
            self.main.stop_stage()
            self._cur_stage = None
            self._manual_override = False
            self.start_btn.config(text="▶", bg=GREEN, activebackground="#27ae60")
            self._set_ui(self._tr("status_stopped"), "")
            return

        stage = self.manual_stage_var.get()
        if not stage:
            self._set_ui(self._tr("status_no_combo"), "")
            return

        self._cur_stage = stage
        self._manual_override = True
        self.main.start_stage(stage)
        self.start_btn.config(text="■", bg=RED, activebackground="#c0392b")
        self._set_ui(self._tr("status_manual"), stage)
