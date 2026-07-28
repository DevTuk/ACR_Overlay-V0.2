import math
import os.path
import random
import re
import threading
import time
import unicodedata
import wave
from threading import Thread

import psutil
import yaml
import numpy as np
import sounddevice as sd

import util
from sharedmemory import SharedMemory


class ACRally:
    _COUNTDOWN_ALIASES = {
        5: ("5", "five", "cinco", "cinq", "cinque", "piec", "pięć"),
        4: ("4", "four", "cuatro", "quatre", "quattro", "cztery"),
        3: ("3", "three", "tres", "trois", "tre", "trzy"),
        2: ("2", "two", "dos", "deux", "due", "dwa"),
        1: ("1", "one", "uno", "un", "une", "jeden"),
        "go": (
            "go", "gogo", "go go", "vamos", "va", "allez",
            "andiamo", "start", "jazda", "jedziemy",
        ),
    }

    def __init__(
            self,
            stage,
            voice,
            call_earliness,
            max_calls_ahead,
            call_speed_multiplier,
            start_from_distance=0,
            start_mode="automatic",
            handbrake_config=None,
            countdown_enabled=True,
            start_beep_volume=0.65,
    ):
        self.stage = stage
        self.voice = voice
        self.call_earliness = call_earliness
        self.max_calls_ahead = max_calls_ahead
        self.call_speed_multiplier = call_speed_multiplier
        self.start_from_distance = start_from_distance
        self.start_mode = start_mode
        self.handbrake_config = handbrake_config or {}
        # La cuenta 5…1…GO es parte del flujo de largada, no una opción.
        # Conservamos el argumento por compatibilidad con versiones viejas.
        self.countdown_enabled = True
        self.start_beep_volume = max(0.0, min(1.0, float(start_beep_volume)))
        self.notes_list = []
        self.exit_all = False
        self.started = False
        self.restarted = False
        self.last_retrieve = time.time()
        self.speed_kmh = 0
        self.distance = 0
        self.time = 0
        self.track = ""
        # Un cambio de voz en plena etapa usa un offset y no debe volver a
        # exigir el freno; los reinicios reales sí vuelven a armarlo.
        self.start_authorized = start_from_distance > 0
        self.start_signal_played = False
        self.start_signal_running = False
        self.handbrake_error = None
        self.started_event = threading.Event()
        self.restart_event = threading.Event()
        self.start_generation = 0
        self.handbrake_needs_release = False
        self.automatic_needs_release = True
        self.handbrake_rearm_event = threading.Event()
        self.handbrake_thread_started = False
        self._restart_cooldown_until = 0.0

    def load_notes_list(self):
        self.notes_list = yaml.safe_load(open(f"pacenotes/{self.stage}.yml", encoding="utf-8"))
        if self.notes_list is None:
            self.notes_list = []

    def start(self):
        retrieve = Thread(target=self.retrieve_thread, daemon=True)
        speak = Thread(target=self.speak_thread, daemon=True)
        retrieve.start()
        speak.start()

    def retrieve_thread(self):
        first_iteration = True
        while not self.exit_all:
            if "acr.exe" in (p.name() for p in psutil.process_iter(attrs=["name"])):
                if not first_iteration:
                    # This likely means the game has just started, give it some time to start up,
                    # or else it might cause a "MapViewOfFile failed" error
                    time.sleep(15)
                break
            else:
                first_iteration = False
                time.sleep(1)

        asm = None
        while not self.exit_all and asm is None:
            try:
                asm = SharedMemory()
            except Exception:
                # Assetto Corsa puede crear el mapa unos instantes después
                # que el proceso. Reintentar sin perder el hilo de detección.
                time.sleep(0.50)
        if self.exit_all:
            return
        last_shared_memory = None

        previous_time = 0
        previous_distance = None

        if self.start_mode == "handbrake":
            self._ensure_handbrake_thread()

        while not self.exit_all:
            try:
                sm = asm.read_shared_memory()
            except Exception:
                # Una lectura incompleta durante cargas/reinicios no debe
                # matar para siempre el hilo que detecta la largada.
                time.sleep(0.10)
                continue
            if sm is None:
                sm = last_shared_memory

            if sm is not None:
                self.speed_kmh = sm.Physics.speed_kmh
                self.distance = sm.Graphics.distance_traveled
                throttle = max(0.0, min(1.0, float(sm.Physics.gas)))
                previous_time = self.get_time()
                time_valid = self.set_time(sm.Graphics.current_time_str)
                self.track = str(sm.Static.track).strip("\0").strip()

                restarted_now = (
                    time_valid and previous_time > 0
                    and previous_time > self.time + 100)
                if restarted_now:
                    self._mark_restart()
                elif (self.start_mode == "automatic"
                      and not self.start_authorized
                      and not self.start_signal_running):
                    # Se exige una transición real: primero acelerador
                    # liberado y luego 100 %. Así no se dispara solo si el
                    # pedal quedó apretado durante un reinicio.
                    if throttle <= 0.20:
                        self.automatic_needs_release = False
                    elif (not self.automatic_needs_release
                          and throttle >= 0.99):
                        self._trigger_start_countdown()
                elif (self.start_authorized
                      and time.monotonic() >= self._restart_cooldown_until):
                    timer_advanced = (
                        time_valid and previous_time > 0
                        and self.time > previous_time)
                    distance_advanced = (
                        previous_distance is not None
                        and self.distance > previous_distance + 0.02)
                    car_is_moving = abs(self.speed_kmh) > 0.5
                    # El cronómetro sigue siendo la señal principal. Distancia
                    # y velocidad permiten arrancar si esa cadena llega tarde
                    # o permanece congelada durante los primeros instantes.
                    if timer_advanced or distance_advanced or car_is_moving:
                        self.started = True
                        self.started_event.set()

                last_shared_memory = sm
                previous_distance = self.distance
            else:
                # Evita un bucle al 100 % de CPU mientras la memoria todavía
                # no está disponible al iniciar o cerrar el juego.
                time.sleep(0.10)
                continue
            time.sleep(0.05)

        asm.close()

    def _mark_restart(self):
        """Rearma una etapa sin crear hilos ni llamadas recursivas."""
        self.restarted = True
        self.restart_event.set()
        self.started = False
        self.started_event.clear()
        self.start_signal_played = False
        self.start_generation += 1
        self._restart_cooldown_until = time.monotonic() + 0.50
        self.start_authorized = False
        self.automatic_needs_release = True
        if self.start_mode == "handbrake":
            self.handbrake_needs_release = True
            self.handbrake_rearm_event.set()

    def speak_thread(self):
        token_sounds = self.build_token_sounds()
        if not token_sounds:
            return

        while not self.exit_all:
            self.restarted = False
            self.load_notes_list()
            self.add_note_durations(self.notes_list, token_sounds)

            while not self.exit_all and not self.started_event.wait(0.10):
                if self.restart_event.is_set():
                    self.restart_event.clear()
                    self.start_from_distance = 0
                    break
            if self.exit_all:
                return
            if not self.started_event.is_set():
                continue

            # Al cambiar de voz se descartan únicamente las notas ya pasadas.
            if self.start_from_distance > 0:
                while (self.notes_list and self.notes_list[0]["distance"]
                       < self.start_from_distance):
                    self.notes_list.pop(0)

            previous_distances = []
            stream = util.open_stream(next(iter(token_sounds.values()))[0])
            try:
                while (self.notes_list and not self.exit_all
                       and not self.restart_event.is_set()):
                    while (previous_distances
                           and previous_distances[0] < self.distance):
                        previous_distances.pop(0)

                    if (len(previous_distances) < self.max_calls_ahead
                            and self.notes_list[0]["distance"]
                            < self.distance
                            + (self.notes_list[0]["duration"]
                               * (self.speed_kmh * (5/18)))
                            + (self.call_earliness
                               * ((self.speed_kmh * (5/18))
                                  ** self.call_speed_multiplier))):
                        note = self.notes_list.pop(0)
                        previous_distances.append(note["distance"])
                        tokens = self.combine_tokens(note["notes"], token_sounds)
                        link_to_next = note["link_to_next"]
                        while link_to_next and self.notes_list:
                            next_note = self.notes_list.pop(0)
                            tokens.extend(self.combine_tokens(
                                next_note["notes"], token_sounds))
                            link_to_next = next_note["link_to_next"]
                        self.play_tokens(stream, tokens, token_sounds)
                    else:
                        time.sleep(0.05)
            finally:
                stream.close()

            if self.restart_event.is_set():
                self.restart_event.clear()
                self.start_from_distance = 0
                continue

            # Aunque ya no queden notas, el hilo permanece disponible para
            # una futura repetición de la etapa.
            while not self.exit_all and not self.restart_event.wait(0.10):
                pass
            if self.restart_event.is_set():
                self.restart_event.clear()
                self.start_from_distance = 0

    def _handbrake_thread(self):
        """Inicia la señal al accionar el freno, sin demora artificial."""
        try:
            from handbrake import Handbrake
        except Exception as exc:
            self.handbrake_error = str(exc)
            self.handbrake_thread_started = False
            return

        handbrake = None
        loaded_config = None
        was_pressed = False
        while not self.exit_all:
            current_config = dict(self.handbrake_config)
            if handbrake is None or current_config != loaded_config:
                try:
                    handbrake = Handbrake(current_config)
                    loaded_config = current_config
                    was_pressed = False
                except Exception as exc:
                    self.handbrake_error = str(exc)
                    self.handbrake_thread_started = False
                    return

            if self.start_authorized:
                # No consultar pygame durante la etapa. El reinicio despierta
                # este hilo mediante un evento, sin sondeo constante.
                self.handbrake_rearm_event.wait(0.50)
                self.handbrake_rearm_event.clear()
                continue
            try:
                pressed = handbrake.get_pressed()
            except Exception as exc:
                self.handbrake_error = str(exc)
                self.handbrake_thread_started = False
                return
            if self.handbrake_needs_release:
                if not pressed:
                    self.handbrake_needs_release = False
            elif pressed and not was_pressed:
                self._trigger_start_countdown()
            was_pressed = pressed
            time.sleep(0.10)

    def _ensure_handbrake_thread(self):
        if self.handbrake_thread_started or self.exit_all:
            return
        self.handbrake_thread_started = True
        threading.Thread(
            target=self._handbrake_thread, daemon=True).start()

    def apply_start_settings(self, start_mode, handbrake_config,
                             countdown_enabled, start_beep_volume):
        """Actualiza largada sin destruir la etapa ni los hilos del copiloto."""
        self.start_mode = start_mode
        self.handbrake_config = handbrake_config or {}
        self.countdown_enabled = True
        self.start_beep_volume = max(
            0.0, min(1.0, float(start_beep_volume)))

        if start_mode == "handbrake":
            self._ensure_handbrake_thread()
            if not self.started:
                self.start_authorized = False
                self.handbrake_needs_release = True
                self.handbrake_rearm_event.set()
        else:
            if not self.started:
                self.start_authorized = False
                self.automatic_needs_release = True
            self.handbrake_needs_release = False
            self.handbrake_rearm_event.set()

    def _trigger_start_countdown(self):
        """Reproduce 5…1…GO una sola vez y autoriza esta generación."""
        if (self.start_authorized or self.start_signal_running
                or self.exit_all):
            return
        generation = self.start_generation
        self.start_signal_running = True
        self.start_signal_played = True

        def run():
            try:
                self._play_start_signal(True)
                if (not self.exit_all
                        and generation == self.start_generation):
                    self.start_authorized = True
            finally:
                self.start_signal_running = False

        threading.Thread(target=run, daemon=True).start()

    def _play_tone(self, frequency, duration=0.18):
        if self.start_beep_volume <= 0 or self.exit_all:
            return
        sample_rate = 44100
        count = int(sample_rate * duration)
        x = np.arange(count, dtype=np.float32) / sample_rate
        # Ataque y caída cortos para evitar clics en los parlantes.
        envelope = np.ones(count, dtype=np.float32)
        fade = min(int(sample_rate * 0.015), count // 2)
        if fade:
            envelope[:fade] = np.linspace(0, 1, fade, dtype=np.float32)
            envelope[-fade:] = np.linspace(1, 0, fade, dtype=np.float32)
        tone = (np.sin(2 * math.pi * frequency * x) * envelope
                * self.start_beep_volume).astype(np.float32)
        try:
            sd.play(tone, sample_rate, blocking=True)
        except Exception:
            pass

    def _play_start_signal(self, countdown):
        if countdown:
            try:
                token_sounds = self.build_token_sounds()
            except (FileNotFoundError, OSError):
                token_sounds = {}

            countdown_tokens = self._resolve_countdown_tokens(token_sounds)
            sequence = (5, 4, 3, 2, 1, "go")
            for index, step in enumerate(sequence):
                if self.exit_all:
                    break
                started_at = time.monotonic()
                token = countdown_tokens.get(step)
                played_voice = (
                    token is not None
                    and self._play_voice_token(token, token_sounds))
                if not played_voice:
                    self._play_tone(
                        1100 if step == "go" else 760,
                        0.32 if step == "go" else 0.18)

                # El comienzo de 5, 4, 3, 2, 1 y GO queda separado por un
                # segundo, compensando la duración real de cada grabación.
                if index < len(sequence) - 1 and not self.exit_all:
                    elapsed = time.monotonic() - started_at
                    time.sleep(max(0.0, 1.0 - elapsed))
        else:
            self._play_tone(880, 0.35)

    @staticmethod
    def _normalize_token_name(value):
        value = unicodedata.normalize("NFKD", str(value))
        value = "".join(
            char for char in value
            if not unicodedata.combining(char))
        return "".join(char for char in value.casefold() if char.isalnum())

    def _resolve_countdown_tokens(self, token_sounds):
        """Busca números y salida usando archivos y dictionary.yml."""
        normalized_aliases = {
            step: tuple(
                self._normalize_token_name(alias)
                for alias in values
            )
            for step, values in self._COUNTDOWN_ALIASES.items()
        }
        alias_sets = {
            step: set(values)
            for step, values in normalized_aliases.items()
        }
        normalized_tokens = {
            self._normalize_token_name(token): token
            for token in token_sounds
        }
        resolved = {}

        # El diccionario permite que una voz conserve nombres internos como
        # Five/GoGo pero muestre Cinco/Vamos dentro del editor.
        dictionary_path = os.path.join(
            "voices", self.voice, "dictionary.yml")
        try:
            with open(dictionary_path, encoding="utf-8") as dictionary_file:
                dictionary = yaml.safe_load(dictionary_file) or {}
        except (FileNotFoundError, OSError, yaml.YAMLError):
            dictionary = {}

        for step, step_aliases in normalized_aliases.items():
            for label, target in dictionary.items():
                if (self._normalize_token_name(label) in alias_sets[step]
                        and target in token_sounds):
                    resolved[step] = target
                    break
            if step in resolved:
                continue
            for alias in step_aliases:
                token = normalized_tokens.get(alias)
                if token is not None:
                    resolved[step] = token
                    break
        return resolved

    def _play_voice_token(self, token, token_sounds):
        """Reproduce una palabra de la voz sin retener la biblioteca entera."""
        sounds = token_sounds.get(token)
        if not sounds:
            return False
        stream = None
        try:
            sound = random.choice(sounds)
            stream = util.open_stream(sound)
            util.play_audio(stream, sound)
            return True
        except Exception:
            return False
        finally:
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass

    def build_token_sounds(self):
        """Indexa la voz sin cargar todos los WAV en memoria.

        Cada token conserva solamente las rutas de sus variantes. El audio se
        lee recién al reproducirse y util.py mantiene una caché pequeña
        compartida por el copiloto y el editor.
        """
        token_sounds = {}
        voice_dir = os.path.abspath(os.path.join("voices", self.voice))
        for entry in os.listdir(voice_dir):
            # This regex allows for After.wav and After_1.wav, etc. and matches the main token
            matches = re.match(r"(.+?)(?:_\d+)?\.wav", entry)
            if matches:
                token = matches.group(1)
                if not token in token_sounds:
                    token_sounds[token] = []
                token_sounds[token].append(os.path.join(voice_dir, entry))
        return token_sounds

    def combine_tokens(self, tokens, token_sounds):
        new_tokens = []
        while len(tokens) > 0:
            for i in reversed(range(len(tokens))):
                key = "-".join(tokens[:i + 1])
                # print(key)
                if key in token_sounds or i == 0:
                    # i == 0 is required for when a token does not exist
                    # e.g. PauseX.Ys
                    new_tokens.append(key)
                    tokens = tokens[i + 1:]
                    break
        return new_tokens

    def match_pause(self, token):
        if matches := re.match('Pause([\\d.]+)s(?:_Reset)?', token):
            return float(matches.group(1))
        return None

    def play_tokens(self, stream, tokens, token_sounds):
        for token in tokens:
            # print(token)
            if token in token_sounds:
                sound = random.choice(token_sounds[token])
                util.play_audio(stream, sound)
            elif pause_time := self.match_pause(token):
                time.sleep(pause_time)

    def add_note_durations(self, notes_list, token_sounds):
        notes_list = notes_list.copy()
        while len(notes_list) > 0:
            note = notes_list.pop(0)
            note["duration"] = 0
            tokens = self.combine_tokens(note["notes"], token_sounds)
            link_to_next = note["link_to_next"]
            while link_to_next and len(notes_list) > 0:
                next_note = notes_list.pop(0)
                next_note["duration"] = 0
                next_tokens = self.combine_tokens(next_note["notes"], token_sounds)
                tokens.extend(next_tokens)
                link_to_next = next_note["link_to_next"]

            for token in tokens:
                if token in token_sounds:
                    with wave.open(token_sounds[token][0], "rb") as f:
                        frames = f.getnframes()
                        rate = f.getframerate()
                        duration = frames / float(rate)
                        note["duration"] += duration
                elif pause_time := self.match_pause(token):
                    note["duration"] += pause_time

    def get_distance(self):
        return self.distance

    def set_time(self, value):
        try:
            value = str(value)
            # Format: 00:00.441\x00\x00\x00\x00\x00\x00
            parsed = (int(value[0:2]) * 60 * 1000
                      + int(value[3:5]) * 1000
                      + int(value[6:9]))
        except (ValueError, TypeError, IndexError):
            return False
        self.time = parsed
        return True

    def get_time(self):
        return self.time

    def get_track(self):
        return self.track

    def exit(self):
        self.exit_all = True
        self.started_event.set()
        self.restart_event.set()
        self.handbrake_rearm_event.set()
