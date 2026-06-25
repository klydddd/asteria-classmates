from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

import pytest

from bosesph.review import ReviewError, review_dataset


def metadata_row(**overrides: str) -> dict[str, str]:
    row = {
        "audio_id": "pam_000001",
        "file_path": "audio_clean/pam_000001.wav",
        "transcript": "Masanting ya ing aldo.",
        "language": "pam",
        "speaker_id": "spk_001",
        "duration_seconds": "8",
        "sample_rate": "16000",
        "split": "unassigned",
        "quality_status": "pending",
        "source_id": "",
        "region": "",
        "speaker_age_group": "",
        "speaker_gender": "",
        "recording_device": "",
        "environment": "",
        "code_switch_languages": "",
        "reviewer_notes": "",
    }
    row.update(overrides)
    return row


def write_dataset(
    dataset: Path,
    rows: list[dict[str, str]],
    *,
    create_audio: bool = True,
) -> None:
    audio_dir = dataset / "audio_clean"
    audio_dir.mkdir(parents=True)
    if create_audio:
        for row in rows:
            (dataset / row["file_path"]).write_bytes(b"synthetic")
    with (dataset / "metadata.csv").open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_rows(dataset: Path) -> list[dict[str, str]]:
    with (dataset / "metadata.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def scripted_input(responses: list[str]) -> tuple[object, list[str]]:
    iterator: Iterator[str] = iter(responses)
    prompts: list[str] = []

    def respond(prompt: str) -> str:
        prompts.append(prompt)
        return next(iterator)

    return respond, prompts


def test_review_approves_pending_clip_and_displays_checklist(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    write_dataset(
        dataset,
        [
            metadata_row(
                region="Pampanga",
                speaker_age_group="adult",
                speaker_gender="male",
            )
        ],
    )
    input_fn, _ = scripted_input(["a"])
    output: list[str] = []

    summary = review_dataset(dataset, input_fn=input_fn, output_fn=output.append)

    assert read_rows(dataset)[0]["quality_status"] == "approved"
    assert summary.approved == 1
    assert summary.remaining == 0
    screen = "\n".join(output)
    assert "Audio understandable?" in screen
    assert "Transcript matches speech?" in screen
    assert "Region: Pampanga" in screen
    assert "Age group: adult" in screen
    assert "Gender: male" in screen
    assert str(dataset / "audio_clean/pam_000001.wav") in screen


@pytest.mark.parametrize(
    ("action", "status", "summary_field"),
    [
        ("f", "needs_review", "needs_fix"),
        ("r", "rejected", "rejected"),
    ],
)
def test_review_requires_note_for_fix_and_rejection(
    tmp_path: Path,
    action: str,
    status: str,
    summary_field: str,
) -> None:
    dataset = tmp_path / "dataset"
    write_dataset(dataset, [metadata_row(reviewer_notes="Existing note.")])
    input_fn, prompts = scripted_input([action, " ", "Check transcript wording."])
    output: list[str] = []

    summary = review_dataset(dataset, input_fn=input_fn, output_fn=output.append)

    row = read_rows(dataset)[0]
    assert row["quality_status"] == status
    assert row["reviewer_notes"] == "Existing note.; Check transcript wording."
    assert getattr(summary, summary_field) == 1
    assert prompts.count("Reviewer note: ") == 2
    assert "A note is required." in output


def test_review_skip_and_quit_leave_rows_unchanged(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    rows = [
        metadata_row(),
        metadata_row(
            audio_id="pam_000002",
            file_path="audio_clean/pam_000002.wav",
        ),
    ]
    write_dataset(dataset, rows)
    input_fn, _ = scripted_input(["s", "q"])

    summary = review_dataset(dataset, input_fn=input_fn, output_fn=lambda _: None)

    assert [row["quality_status"] for row in read_rows(dataset)] == [
        "pending",
        "pending",
    ]
    assert summary.skipped == 1
    assert summary.quit is True
    assert summary.remaining == 2


def test_review_checkpoints_decisions_and_resumes_unreviewed_rows(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "dataset"
    rows = [
        metadata_row(),
        metadata_row(
            audio_id="pam_000002",
            file_path="audio_clean/pam_000002.wav",
        ),
    ]
    write_dataset(dataset, rows)
    first_input, _ = scripted_input(["a", "q"])

    review_dataset(dataset, input_fn=first_input, output_fn=lambda _: None)

    second_input, prompts = scripted_input(["a"])
    summary = review_dataset(
        dataset,
        input_fn=second_input,
        output_fn=lambda _: None,
    )

    assert [row["quality_status"] for row in read_rows(dataset)] == [
        "approved",
        "approved",
    ]
    assert summary.approved == 1
    assert all("pam_000001" not in prompt for prompt in prompts)


def test_review_does_not_approve_missing_audio(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    write_dataset(dataset, [metadata_row()], create_audio=False)
    input_fn, _ = scripted_input(["a", "s"])
    output: list[str] = []

    summary = review_dataset(dataset, input_fn=input_fn, output_fn=output.append)

    assert read_rows(dataset)[0]["quality_status"] == "pending"
    assert summary.approved == 0
    assert summary.skipped == 1
    assert "Cannot approve: audio file is missing." in output


def test_review_keyboard_interrupt_preserves_prior_checkpoint(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    rows = [
        metadata_row(),
        metadata_row(
            audio_id="pam_000002",
            file_path="audio_clean/pam_000002.wav",
        ),
    ]
    write_dataset(dataset, rows)
    responses = iter(["a"])

    def interrupt_after_first(prompt: str) -> str:
        try:
            return next(responses)
        except StopIteration as error:
            raise KeyboardInterrupt from error

    summary = review_dataset(
        dataset,
        input_fn=interrupt_after_first,
        output_fn=lambda _: None,
    )

    assert [row["quality_status"] for row in read_rows(dataset)] == [
        "approved",
        "pending",
    ]
    assert summary.quit is True
    assert summary.remaining == 1


def test_review_rejects_invalid_dataset(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    dataset.mkdir()

    with pytest.raises(ReviewError):
        review_dataset(dataset, input_fn=lambda _: "q", output_fn=lambda _: None)


def test_review_checkpoint_failure_keeps_metadata_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = tmp_path / "dataset"
    write_dataset(dataset, [metadata_row()])
    original = (dataset / "metadata.csv").read_bytes()
    input_fn, _ = scripted_input(["a"])

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("checkpoint failed")

    monkeypatch.setattr("bosesph.review.os.replace", fail_replace)

    with pytest.raises(ReviewError, match="checkpoint failed"):
        review_dataset(dataset, input_fn=input_fn, output_fn=lambda _: None)

    assert (dataset / "metadata.csv").read_bytes() == original
