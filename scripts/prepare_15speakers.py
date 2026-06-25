"""Merge 15 already-ingested PLD/PAM sessions, normalize, and approve all."""

from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))

from bosesph.review import approve_all_clips
from bosesph.transcripts import normalize_dataset

INGESTED = PROJECT / "outputs" / "ingested"
MERGED = PROJECT / "outputs" / "merged_15spk"

SESSIONS = [
    "0400", "0401", "0402", "0403", "0405",
    "0407", "0408", "0409", "0410", "0411",
    "0412", "0413", "0414", "0415", "0416",
]


def merge_datasets() -> None:
    if MERGED.exists():
        shutil.rmtree(MERGED)
    audio_out = MERGED / "audio_clean"
    audio_out.mkdir(parents=True)

    all_rows: list[dict[str, str]] = []
    fieldnames: list[str] | None = None
    global_idx = 0

    for session_id in SESSIONS:
        session_dir = INGESTED / session_id
        meta = session_dir / "metadata.csv"
        with meta.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            if fieldnames is None:
                fieldnames = list(reader.fieldnames or [])
            for row in reader:
                global_idx += 1
                new_id = f"pam_{global_idx:06d}"
                new_filename = f"{new_id}.wav"

                src_audio = session_dir / row["file_path"]
                if src_audio.is_file():
                    shutil.copy2(src_audio, audio_out / new_filename)

                row["audio_id"] = new_id
                row["file_path"] = f"audio_clean/{new_filename}"
                all_rows.append(row)

    assert fieldnames is not None
    with (MERGED / "metadata.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Merged {len(all_rows)} clips from {len(SESSIONS)} sessions")


def main() -> None:
    print("=== Merge 15 sessions ===")
    merge_datasets()

    print("\n=== Normalize transcripts ===")
    report = normalize_dataset(MERGED)
    print(f"Normalized {report.changed} / {report.row_count} transcripts")

    print("\n=== Approve all clips ===")
    result = approve_all_clips(MERGED)
    print(f"Approved {result.approved}, skipped {result.skipped_missing_audio}")

    print(f"\n=== Done! Dataset at: {MERGED} ===")


if __name__ == "__main__":
    main()
