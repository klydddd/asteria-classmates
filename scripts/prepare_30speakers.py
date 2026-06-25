"""Ingest 30 PLD/PAM sessions, merge into one dataset, normalize, and approve all."""

from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))

from bosesph.ingestion import import_pld_session
from bosesph.review import approve_all_clips
from bosesph.transcripts import normalize_dataset

PLD_PAM = PROJECT / "PLD" / "PAM"
OUTPUTS = PROJECT / "outputs"
INGESTED = OUTPUTS / "ingested"
MERGED = OUTPUTS / "merged_30spk"

SESSIONS = sorted(d.name for d in PLD_PAM.iterdir() if d.is_dir())[:30]


def ingest_all() -> list[Path]:
    """Ingest each session into its own directory, return list of output paths."""
    INGESTED.mkdir(parents=True, exist_ok=True)
    session_dirs: list[Path] = []
    for i, session_id in enumerate(SESSIONS, 1):
        source = PLD_PAM / session_id
        output = INGESTED / session_id
        print(f"[{i:02d}/30] Ingesting session {session_id}...", end=" ", flush=True)
        if (output / "metadata.csv").is_file():
            print("(cached)")
            session_dirs.append(output)
            continue
        report = import_pld_session(source, output, overwrite=True)
        print(
            f"pending={report.counts.pending} "
            f"needs_review={report.counts.needs_review} "
            f"rejected={report.counts.rejected}"
        )
        session_dirs.append(output)
    return session_dirs


def merge_datasets(session_dirs: list[Path]) -> None:
    """Merge all ingested sessions into MERGED with renumbered audio IDs."""
    if MERGED.exists():
        shutil.rmtree(MERGED)
    audio_out = MERGED / "audio_clean"
    audio_out.mkdir(parents=True)

    all_rows: list[dict[str, str]] = []
    fieldnames: list[str] | None = None
    global_idx = 0

    for session_dir in session_dirs:
        meta = session_dir / "metadata.csv"
        with meta.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            if fieldnames is None:
                fieldnames = list(reader.fieldnames or [])
            for row in reader:
                global_idx += 1
                old_filename = Path(row["file_path"]).name
                new_id = f"pam_{global_idx:06d}"
                new_filename = f"{new_id}.wav"

                src_audio = session_dir / row["file_path"]
                if src_audio.is_file():
                    shutil.copy2(src_audio, audio_out / new_filename)

                row["audio_id"] = new_id
                row["file_path"] = f"audio_clean/{new_filename}"
                all_rows.append(row)

    assert fieldnames is not None
    out_meta = MERGED / "metadata.csv"
    with out_meta.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nMerged {len(all_rows)} clips from {len(session_dirs)} sessions into {MERGED}")


def main() -> None:
    print("=== Step 1: Ingest 30 sessions ===")
    session_dirs = ingest_all()

    print("\n=== Step 2: Merge datasets ===")
    merge_datasets(session_dirs)

    print("\n=== Step 3: Normalize transcripts ===")
    report = normalize_dataset(MERGED)
    print(f"Normalized {report.changed} / {report.row_count} transcripts")

    print("\n=== Step 4: Approve all clips ===")
    result = approve_all_clips(MERGED)
    print(
        f"Approved {result.approved}, "
        f"skipped (missing audio) {result.skipped_missing_audio}, "
        f"remaining {result.remaining}"
    )

    print("\n=== Done! Ready for build-dataset + finetune ===")
    print(f"Dataset at: {MERGED}")


if __name__ == "__main__":
    main()
