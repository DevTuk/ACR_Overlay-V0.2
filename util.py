import io
import os
import sys
import time
import wave
from functools import lru_cache

import sounddevice


# Sólo se retienen los últimos sonidos usados. La caché es global al proceso,
# por lo que el editor y el overlay comparten estos datos en vez de duplicar
# una voz completa en memoria.
@lru_cache(maxsize=8)
def _cached_wav(path):
    with open(path, "rb") as audio_file:
        return audio_file.read()


def _wave_source(audio):
    if isinstance(audio, bytes):
        return io.BytesIO(audio)
    if isinstance(audio, (str, os.PathLike)):
        return io.BytesIO(_cached_wav(os.fspath(audio)))
    return audio


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def open_stream(audio):
    with wave.open(_wave_source(audio), "rb") as wf:
        stream = sounddevice.RawOutputStream(samplerate=wf.getframerate(), channels=wf.getnchannels(), dtype="int16")
        stream.start()
        return stream


def play_audio(stream, audio):
    with wave.open(_wave_source(audio), "rb") as wf:
        stream.write(wf.readframes(wf.getnframes()))


def play_beep():
    with open(str(resource_path("beep.wav")), "rb") as f:
        data = f.read()

        stream = open_stream(data)
        play_audio(stream, data)
        time.sleep(0.5)
        stream.close()


def initialise_audio():
    stream = sounddevice.RawOutputStream(samplerate=44100, channels=1, dtype="int16")
    stream.start()
    stream.close()
