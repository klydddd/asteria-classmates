"""Create a local mock PLD dataset with valid, short, and silent audio clips to test the pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "src"))

from tests.audio_fixtures import write_pcm_wav


def main() -> None:
    mock_dir = PROJECT / "mock_pld" / "PAM" / "0400"
    mock_dir.mkdir(parents=True, exist_ok=True)

    print(f"Creating mock PLD session in: {mock_dir.relative_to(PROJECT)}")

    # 1. Write the PLD session log
    session_log = mock_dir / "session.log"
    log_content = (
        'SessionID = "mock-session-01"\n'
        'SessionEnvironment = "room"\n'
        'SpeakerID = "0400"\n'
        'SpeakerAge = "25"\n'
        'SpeakerGender = "female"\n'
        # 1. Normal valid clip (duration: 6s, good amplitude)
        'clip_valid.wav "prompt1.txt" "Masanting ya ing aldo."\n'
        # 2. Valid clip with Taglish and noise tag (duration: 8s)
        'clip_taglish.wav "prompt2.txt" "Ikayu ngeni... [noise] okay let\'s go."\n'
        # 3. Silent clip (will be rejected/marked needs_review - amplitude 0.001)
        'clip_silent.wav "prompt3.txt" "Masanting ya ing aldo."\n'
        # 4. Too short clip (will be rejected - duration: 2s)
        'clip_short.wav "prompt4.txt" "Masanting."\n'
        # 5. Too long clip (will be rejected - duration: 20s)
        'clip_long.wav "prompt5.txt" "Masanting ya ing aldo at masanting ya ing abak at masanting ya ing silim."\n'
    )
    session_log.write_text(log_content, encoding="utf-8")

    # 2. Write the wav files using tests/audio_fixtures.py
    # Valid clip
    write_pcm_wav(mock_dir / "clip_valid.wav", duration=6.0, amplitude=0.25)
    # Taglish clip
    write_pcm_wav(mock_dir / "clip_taglish.wav", duration=8.0, amplitude=0.25)
    # Silent clip
    write_pcm_wav(mock_dir / "clip_silent.wav", duration=7.0, amplitude=0.0001)
    # Short clip
    write_pcm_wav(mock_dir / "clip_short.wav", duration=2.0, amplitude=0.25)
    # Long clip
    write_pcm_wav(mock_dir / "clip_long.wav", duration=20.0, amplitude=0.25)

    print("Created audio fixtures:")
    print(" - clip_valid.wav (6s, active) -> Expected: pending")
    print(" - clip_taglish.wav (8s, active) -> Expected: pending")
    print(" - clip_silent.wav (7s, silent) -> Expected: rejected")
    print(" - clip_short.wav (2s, too short) -> Expected: rejected")
    print(" - clip_long.wav (20s, too long) -> Expected: rejected")
    print("\nMock dataset ready! Run these commands to test the pipeline:")
    print("  1. python scripts/create_mock_dataset.py (this script)")
    print("  2. .venv\\Scripts\\bosesph import-pld mock_pld/PAM/0400 --output outputs/test_dataset --overwrite")
    print("  3. Check results in outputs/test_dataset/metadata.csv and ingestion_report.json")


if __name__ == "__main__":
    main()
