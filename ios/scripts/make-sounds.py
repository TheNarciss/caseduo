#!/usr/bin/env python3
"""The app's sounds, synthesised so they can be regenerated and never carry a licence.

Short, soft, in tune with each other (a pentatonic around A4): a tick when an answer leaves,
a two-note chime when it is right, a muted low bump when it is wrong, a pop when a tile
lands, a rising arpeggio for a combo, a short fanfare when a lesson ends, and the streak and
success sounds the app already had.

    python3 ios/scripts/make-sounds.py
"""

import math
import struct
import wave
from pathlib import Path

import numpy as np

RATE = 44100
OUT = Path(__file__).resolve().parents[1] / "CaseDuo" / "Resources" / "Sounds"


def tone(freq: float, seconds: float, *, attack=0.004, decay=0.12, volume=0.5, harmonics=(1.0, 0.35, 0.12)) -> np.ndarray:
    """A plucked, slightly bell-like note with a fast attack and an exponential tail."""
    t = np.linspace(0, seconds, int(RATE * seconds), endpoint=False)
    wave_ = sum(a * np.sin(2 * math.pi * freq * (i + 1) * t) for i, a in enumerate(harmonics))
    env = np.minimum(1, t / attack) * np.exp(-t / decay)
    return (wave_ * env * volume).astype(np.float32)


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(RATE * seconds), dtype=np.float32)


def mix(*layers: tuple[float, np.ndarray]) -> np.ndarray:
    """Layers placed at offsets (seconds), summed."""
    length = max(int(RATE * at) + len(buf) for at, buf in layers)
    out = np.zeros(length, dtype=np.float32)
    for at, buf in layers:
        start = int(RATE * at)
        out[start : start + len(buf)] += buf
    peak = np.max(np.abs(out)) or 1
    return out / peak * 0.8


def write(name: str, samples: np.ndarray) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32767)) for s in samples))


A4, Cs5, E5, A5, Cs6, E6 = 440.0, 554.37, 659.25, 880.0, 1108.73, 1318.51

write("send", mix((0, tone(A5, 0.06, decay=0.02, volume=0.3))))
write("pop", mix((0, tone(E5, 0.05, decay=0.025, volume=0.35, harmonics=(1.0, 0.2)))))
write("correct", mix((0, tone(E5, 0.18, decay=0.08)), (0.09, tone(A5, 0.32, decay=0.14))))
write("wrong", mix((0, tone(220.0, 0.22, decay=0.09, volume=0.5, harmonics=(1.0, 0.5, 0.0))),
                   (0.0, tone(207.65, 0.22, decay=0.09, volume=0.35, harmonics=(1.0, 0.4)))))
write("combo", mix((0, tone(A4, 0.2, decay=0.07)), (0.07, tone(Cs5, 0.2, decay=0.07)),
                   (0.14, tone(E5, 0.2, decay=0.07)), (0.21, tone(A5, 0.4, decay=0.18))))
write("done", mix((0, tone(A4, 0.25, decay=0.1)), (0.12, tone(Cs5, 0.25, decay=0.1)),
                  (0.24, tone(E5, 0.25, decay=0.1)), (0.36, tone(A5, 0.5, decay=0.22)),
                  (0.36, tone(Cs6, 0.5, decay=0.2, volume=0.25))))
write("success", mix((0, tone(Cs5, 0.2, decay=0.08)), (0.1, tone(E5, 0.3, decay=0.14))))
write("streak", mix((0, tone(A4, 0.18, decay=0.07)), (0.08, tone(E5, 0.18, decay=0.07)),
                    (0.16, tone(A5, 0.18, decay=0.07)), (0.24, tone(E6, 0.45, decay=0.2)),
                    (0.24, tone(A5, 0.45, decay=0.2, volume=0.3))))
print("ok", sorted(p.name for p in OUT.iterdir()))
