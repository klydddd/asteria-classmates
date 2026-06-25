from __future__ import annotations

import wave
from pathlib import Path

import pytest

from bosesph.audio import (
    CorruptAudioError,
    EmptyAudioError,
    inspect_wav,
    standardize_wav,
)
from tests.audio_fixtures import write_pcm_wav


@pytest.mark.parametrize("sample_width", [1, 2, 3, 4])
def test_inspect_wav_supports_integer_pcm_widths(
    tmp_path: Path,
    sample_width: int,
) -> None:
    source = tmp_path / f"source-{sample_width}.wav"
    write_pcm_wav(source, duration=0.1, sample_width=sample_width)

    inspection = inspect_wav(source)

    assert inspection.sample_width == sample_width
    assert inspection.duration_seconds == pytest.approx(0.1)
    assert inspection.rms > 0.001
    assert inspection.fully_silent is False
    assert inspection.suspicious_quiet is False


def test_standardize_wav_resamples_stereo_to_16khz_mono(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.wav"
    output = tmp_path / "output.wav"
    write_pcm_wav(source, duration=0.2, sample_rate=44100, channels=2)

    inspection = standardize_wav(source, output)

    assert inspection.sample_rate == 44100
    assert inspection.channels == 2
    with wave.open(str(output), "rb") as audio:
        assert audio.getframerate() == 16000
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        assert audio.getnframes() == pytest.approx(3200, abs=1)


def test_inspect_wav_marks_silent_and_quiet_audio(tmp_path: Path) -> None:
    silent = tmp_path / "silent.wav"
    quiet = tmp_path / "quiet.wav"
    write_pcm_wav(silent, duration=0.1, amplitude=0)
    write_pcm_wav(quiet, duration=0.1, amplitude=0.001)

    silent_result = inspect_wav(silent)
    quiet_result = inspect_wav(quiet)

    assert silent_result.fully_silent is True
    assert silent_result.suspicious_quiet is True
    assert quiet_result.fully_silent is False
    assert quiet_result.suspicious_quiet is True


def test_inspect_wav_rejects_empty_and_corrupt_files(tmp_path: Path) -> None:
    empty = tmp_path / "empty.wav"
    corrupt = tmp_path / "corrupt.wav"
    write_pcm_wav(empty, duration=0)
    corrupt.write_bytes(b"not a wav")

    with pytest.raises(EmptyAudioError):
        inspect_wav(empty)
    with pytest.raises(CorruptAudioError):
        inspect_wav(corrupt)
