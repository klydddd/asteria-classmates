from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


def _encode_sample(value: float, sample_width: int) -> bytes:
    value = max(-1.0, min(1.0, value))
    if sample_width == 1:
        return bytes((round((value + 1.0) * 127.5),))
    if sample_width == 2:
        return struct.pack("<h", round(value * 32767))
    if sample_width == 3:
        integer = round(value * 8388607)
        if integer < 0:
            integer += 1 << 24
        return integer.to_bytes(3, "little", signed=False)
    if sample_width == 4:
        return struct.pack("<i", round(value * 2147483647))
    raise ValueError(f"unsupported fixture sample width: {sample_width}")


def write_pcm_wav(
    path: Path,
    *,
    duration: float,
    sample_rate: int = 16000,
    channels: int = 1,
    sample_width: int = 2,
    amplitude: float = 0.25,
) -> None:
    frame_count = round(duration * sample_rate)
    frames = bytearray()
    for frame_index in range(frame_count):
        sample = amplitude * math.sin(2 * math.pi * 440 * frame_index / sample_rate)
        encoded = _encode_sample(sample, sample_width)
        frames.extend(encoded * channels)

    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(sample_width)
        audio.setframerate(sample_rate)
        audio.writeframes(bytes(frames))
