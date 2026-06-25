"""Dependency-free inspection and standardization for integer PCM WAV audio."""

from __future__ import annotations

import math
import struct
import sys
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path

TARGET_SAMPLE_RATE = 16000
QUIET_RMS_THRESHOLD = 0.001
SUPPORTED_SAMPLE_WIDTHS = {1, 2, 3, 4}


class AudioError(ValueError):
    """Base class for clip-level audio processing failures."""


class CorruptAudioError(AudioError):
    """Raised when a file cannot be decoded as a WAV."""


class EmptyAudioError(AudioError):
    """Raised when a WAV contains no audio frames."""


class UnsupportedAudioError(AudioError):
    """Raised when a WAV uses unsupported compression or PCM properties."""


@dataclass(frozen=True)
class AudioInspection:
    """Measured source audio properties used by ingestion decisions."""

    duration_seconds: float
    sample_rate: int
    channels: int
    sample_width: int
    frame_count: int
    rms: float
    fully_silent: bool
    suspicious_quiet: bool


def _decode_sample(data: bytes, offset: int, sample_width: int) -> float:
    if sample_width == 1:
        return (data[offset] - 128) / 128
    if sample_width == 2:
        return struct.unpack_from("<h", data, offset)[0] / 32768
    if sample_width == 3:
        value = int.from_bytes(data[offset : offset + 3], "little", signed=False)
        if value & 0x800000:
            value -= 1 << 24
        return value / 8388608
    if sample_width == 4:
        return struct.unpack_from("<i", data, offset)[0] / 2147483648
    raise UnsupportedAudioError(f"unsupported PCM sample width: {sample_width}")


def _read_wav(path: Path) -> tuple[AudioInspection, list[float]]:
    try:
        with wave.open(str(path), "rb") as audio:
            if audio.getcomptype() != "NONE":
                raise UnsupportedAudioError(
                    f"unsupported WAV compression: {audio.getcomptype()}"
                )
            channels = audio.getnchannels()
            sample_width = audio.getsampwidth()
            sample_rate = audio.getframerate()
            frame_count = audio.getnframes()
            if channels <= 0 or sample_rate <= 0:
                raise UnsupportedAudioError("invalid WAV channels or sample rate")
            if sample_width not in SUPPORTED_SAMPLE_WIDTHS:
                raise UnsupportedAudioError(
                    f"unsupported PCM sample width: {sample_width}"
                )
            if frame_count <= 0:
                raise EmptyAudioError("WAV contains no audio frames")
            frame_bytes = audio.readframes(frame_count)
    except (EOFError, OSError, wave.Error) as error:
        raise CorruptAudioError(f"cannot decode WAV: {error}") from error

    expected_bytes = frame_count * channels * sample_width
    if len(frame_bytes) != expected_bytes:
        raise CorruptAudioError(
            f"truncated WAV data: expected {expected_bytes} bytes, "
            f"read {len(frame_bytes)}"
        )

    samples = [
        _decode_sample(frame_bytes, offset, sample_width)
        for offset in range(0, len(frame_bytes), sample_width)
    ]
    square_sum = sum(sample * sample for sample in samples)
    rms = math.sqrt(square_sum / len(samples))
    fully_silent = all(sample == 0 for sample in samples)
    inspection = AudioInspection(
        duration_seconds=frame_count / sample_rate,
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
        frame_count=frame_count,
        rms=rms,
        fully_silent=fully_silent,
        suspicious_quiet=rms <= QUIET_RMS_THRESHOLD,
    )
    return inspection, samples


def inspect_wav(path: str | Path) -> AudioInspection:
    """Inspect an integer PCM WAV without modifying it."""
    inspection, _ = _read_wav(Path(path))
    return inspection


def _to_mono(samples: list[float], channels: int) -> list[float]:
    if channels == 1:
        return samples
    return [
        sum(samples[offset : offset + channels]) / channels
        for offset in range(0, len(samples), channels)
    ]


def _resample(
    samples: list[float],
    source_rate: int,
    target_rate: int,
) -> list[float]:
    if source_rate == target_rate:
        return samples
    output_count = max(1, round(len(samples) * target_rate / source_rate))
    last_index = len(samples) - 1
    output: list[float] = []
    for output_index in range(output_count):
        source_position = output_index * source_rate / target_rate
        left_index = min(int(source_position), last_index)
        right_index = min(left_index + 1, last_index)
        fraction = source_position - left_index
        output.append(
            samples[left_index] * (1 - fraction) + samples[right_index] * fraction
        )
    return output


def _encode_16_bit(samples: list[float]) -> bytes:
    integers = array(
        "h",
        (round(max(-1.0, min(1.0, sample)) * 32767) for sample in samples),
    )
    if sys.byteorder != "little":
        integers.byteswap()
    return integers.tobytes()


def standardize_wav(source: str | Path, output: str | Path) -> AudioInspection:
    """Write a mono, 16 kHz, signed 16-bit WAV and return source properties."""
    source_path = Path(source)
    output_path = Path(output)
    inspection, samples = _read_wav(source_path)
    mono = _to_mono(samples, inspection.channels)
    standardized = _resample(mono, inspection.sample_rate, TARGET_SAMPLE_RATE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with wave.open(str(output_path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(TARGET_SAMPLE_RATE)
            audio.writeframes(_encode_16_bit(standardized))
    except (OSError, wave.Error) as error:
        raise AudioError(f"cannot write standardized WAV: {error}") from error
    return inspection
