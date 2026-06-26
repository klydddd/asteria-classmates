from __future__ import annotations

import csv
import io
import json
import time
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from bosesph.api import demo as demo_api
from bosesph.api.app import create_app
from bosesph.asr import TranscriptionResult
from tests.audio_fixtures import write_pcm_wav


def write_pld_session(directory: Path) -> None:
    directory.mkdir(parents=True)
    (directory / "session.log").write_text(
        'SessionID = "session-01"\n'
        'SessionEnvironment = "room"\n'
        'SpeakerID = "0400"\n'
        'SpeakerGender = "male"\n'
        'clip.wav "prompt.txt" "Masanting ya ing aldo."\n',
        encoding="utf-8",
    )
    write_pcm_wav(directory / "clip.wav", duration=6)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture
def client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, Path]:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("BOSESPH_WORKSPACE", str(workspace))
    with TestClient(create_app()) as test_client:
        yield test_client, workspace


def poll_job(test_client: TestClient, job_id: str) -> dict[str, object]:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = test_client.get(f"/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] in {"succeeded", "failed"}:
            return job
        time.sleep(0.01)
    raise AssertionError(f"job did not finish: {job_id}")


def test_cors_preflight_allows_local_dashboard(
    client: tuple[TestClient, Path],
) -> None:
    test_client, _ = client

    response = test_client.options(
        "/project-status",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ("http://localhost:3000")


def test_cors_preflight_rejects_external_origin(
    client: tuple[TestClient, Path],
) -> None:
    test_client, _ = client

    response = test_client.options(
        "/project-status",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_upload_audio_saves_wav(
    client: tuple[TestClient, Path], tmp_path: Path
) -> None:
    test_client, workspace = client
    wav_path = tmp_path / "clip.wav"
    write_pcm_wav(wav_path, duration=0.1)

    response = test_client.post(
        "/upload-audio",
        params={"destination": "uploads"},
        files={"files": ("clip.wav", wav_path.read_bytes(), "audio/wav")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "saved_files": ["uploads/clip.wav"],
        "count": 1,
    }
    assert (workspace / "uploads" / "clip.wav").is_file()


def test_upload_audio_rejects_traversal_filename(
    client: tuple[TestClient, Path],
) -> None:
    test_client, workspace = client

    response = test_client.post(
        "/upload-audio",
        params={"destination": "uploads"},
        files={"files": ("../escape.wav", b"not-a-wave", "audio/wav")},
    )

    assert response.status_code == 400
    assert not (workspace / "escape.wav").exists()


def test_upload_audio_rejects_symlink_escape(
    client: tuple[TestClient, Path],
    tmp_path: Path,
) -> None:
    test_client, workspace = client
    uploads = workspace / "uploads"
    uploads.mkdir(parents=True)
    outside = tmp_path / "outside.wav"
    (uploads / "escape.wav").symlink_to(outside)

    response = test_client.post(
        "/upload-audio",
        params={"destination": "uploads"},
        files={"files": ("escape.wav", b"not-a-wave", "audio/wav")},
    )

    assert response.status_code == 400
    assert not outside.exists()


def test_pipeline_sync_endpoints_and_review_decision(
    client: tuple[TestClient, Path],
) -> None:
    test_client, workspace = client
    write_pld_session(workspace / "source")

    imported = test_client.post(
        "/import-pld",
        json={"source": "source", "output": "reviewed"},
    )
    validated = test_client.post(
        "/validate-dataset",
        json={"dataset": "reviewed"},
    )
    normalized = test_client.post(
        "/normalize-transcripts",
        json={"dataset": "reviewed"},
    )
    audio_id = read_rows(workspace / "reviewed" / "metadata.csv")[0]["audio_id"]
    reviewed = test_client.post(
        "/review/decision",
        json={
            "dataset": "reviewed",
            "audio_id": audio_id,
            "decision": "approve",
        },
    )

    assert imported.status_code == 200
    assert imported.json()["counts"]["pending"] == 1
    assert validated.status_code == 200
    assert validated.json()["row_count"] == 1
    assert normalized.status_code == 200
    assert normalized.json()["row_count"] == 1
    assert reviewed.status_code == 200
    assert reviewed.json()["new_status"] == "approved"
    assert reviewed.json()["remaining_reviewable"] == 0


def test_build_job_status_and_download(
    client: tuple[TestClient, Path],
) -> None:
    test_client, workspace = client
    write_pld_session(workspace / "source")
    assert (
        test_client.post(
            "/import-pld",
            json={"source": "source", "output": "reviewed"},
        ).status_code
        == 200
    )
    audio_id = read_rows(workspace / "reviewed" / "metadata.csv")[0]["audio_id"]
    assert (
        test_client.post(
            "/review/decision",
            json={
                "dataset": "reviewed",
                "audio_id": audio_id,
                "decision": "approve",
            },
        ).status_code
        == 200
    )

    submitted = test_client.post(
        "/build-dataset",
        json={"dataset": "reviewed", "output": "dataset"},
    )
    assert submitted.status_code == 202
    job = poll_job(test_client, submitted.json()["id"])
    assert job["status"] == "succeeded"
    assert job["result"]["total_clips"] == 1

    jobs = test_client.get("/jobs")
    status = test_client.get("/project-status")
    download = test_client.get("/download-output", params={"path": "dataset"})

    assert jobs.status_code == 200
    assert jobs.json()[0]["id"] == submitted.json()["id"]
    assert status.status_code == 200
    assert status.json()["dataset_available"] is True
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
        assert "metadata.csv" in archive.namelist()
        assert "dataset_stats.json" in archive.namelist()


def test_project_status_returns_dashboard_metrics(
    client: tuple[TestClient, Path],
) -> None:
    test_client, workspace = client
    dataset = workspace / "dataset"
    baseline = workspace / "benchmark" / "baseline"
    finetuned = workspace / "benchmark" / "finetuned"
    incomplete_model = workspace / "model" / "a-incomplete"
    model = workspace / "model" / "bosesph-kapampangan-v1"
    later_model = workspace / "model" / "z-later"
    dataset.mkdir(parents=True)
    baseline.mkdir(parents=True)
    finetuned.mkdir(parents=True)
    incomplete_model.mkdir(parents=True)
    model.mkdir(parents=True)
    later_model.mkdir(parents=True)

    (dataset / "dataset_stats.json").write_text(
        json.dumps(
            {
                "total_clips": 68,
                "total_duration_seconds": 612.0,
                "total_duration_display": "10m 12s",
                "total_speakers": 4,
                "source_counts": {"approved": 68},
            }
        ),
        encoding="utf-8",
    )
    (baseline / "results.json").write_text(
        json.dumps({"wer": 0.91, "cer": 0.52}),
        encoding="utf-8",
    )
    (finetuned / "results.json").write_text(
        json.dumps({"wer": 0.75, "cer": 0.34}),
        encoding="utf-8",
    )
    (model / "model_card.md").write_text("# Model", encoding="utf-8")
    (later_model / "model_card.md").write_text("# Later model", encoding="utf-8")

    response = test_client.get("/project-status")

    assert response.status_code == 200
    assert response.json() == {
        "dataset_available": True,
        "dataset_stats": {
            "total_clips": 68,
            "total_duration_seconds": 612.0,
            "total_duration_display": "10m 12s",
            "total_speakers": 4,
            "source_counts": {"approved": 68},
        },
        "baseline_metrics": {"wer": 0.91, "cer": 0.52},
        "finetuned_metrics": {"wer": 0.75, "cer": 0.34},
        "model_available": True,
        "model_dir": "model/bosesph-kapampangan-v1",
        "model_version": "bosesph-kapampangan-v1",
    }


def test_project_status_uses_none_for_missing_outputs(
    client: tuple[TestClient, Path],
) -> None:
    test_client, _ = client

    response = test_client.get("/project-status")

    assert response.status_code == 200
    assert response.json() == {
        "dataset_available": False,
        "dataset_stats": None,
        "baseline_metrics": None,
        "finetuned_metrics": None,
        "model_available": False,
        "model_dir": None,
        "model_version": None,
    }


def test_project_status_ignores_malformed_artifacts_independently(
    client: tuple[TestClient, Path],
) -> None:
    test_client, workspace = client
    dataset = workspace / "dataset"
    baseline = workspace / "benchmark" / "baseline"
    finetuned = workspace / "benchmark" / "finetuned"
    model = workspace / "model" / "bosesph-kapampangan-v1"
    dataset.mkdir(parents=True)
    baseline.mkdir(parents=True)
    finetuned.mkdir(parents=True)
    model.mkdir(parents=True)

    (dataset / "dataset_stats.json").write_text("{invalid", encoding="utf-8")
    (baseline / "results.json").write_text(
        json.dumps({"wer": 0.91, "cer": 0.52}),
        encoding="utf-8",
    )
    (finetuned / "results.json").write_text("{invalid", encoding="utf-8")
    (model / "model_card.md").write_text("# Model", encoding="utf-8")

    response = test_client.get("/project-status")

    assert response.status_code == 200
    assert response.json() == {
        "dataset_available": False,
        "dataset_stats": None,
        "baseline_metrics": {"wer": 0.91, "cer": 0.52},
        "finetuned_metrics": None,
        "model_available": True,
        "model_dir": "model/bosesph-kapampangan-v1",
        "model_version": "bosesph-kapampangan-v1",
    }


@pytest.mark.parametrize(
    "metrics",
    [
        [],
        "not-an-object",
        1,
        {"wer": "0.91", "cer": 0.52},
        {"wer": True, "cer": 0.52},
        {"wer": 0.91, "cer": False},
        {"wer": float("inf"), "cer": 0.52},
        {"wer": 0.91, "cer": float("nan")},
        {"wer": 10**400, "cer": 0.52},
    ],
)
def test_project_status_rejects_invalid_metric_artifacts(
    client: tuple[TestClient, Path],
    metrics: object,
) -> None:
    test_client, workspace = client
    baseline = workspace / "benchmark" / "baseline"
    finetuned = workspace / "benchmark" / "finetuned"
    baseline.mkdir(parents=True)
    finetuned.mkdir(parents=True)
    (baseline / "results.json").write_text(
        json.dumps(metrics),
        encoding="utf-8",
    )
    (finetuned / "results.json").write_text(
        json.dumps({"wer": 0.75, "cer": 0.34}),
        encoding="utf-8",
    )

    response = test_client.get("/project-status")

    assert response.status_code == 200
    assert response.json()["baseline_metrics"] is None
    assert response.json()["finetuned_metrics"] == {"wer": 0.75, "cer": 0.34}


def test_demo_options_return_controlled_choices(
    client: tuple[TestClient, Path],
) -> None:
    test_client, workspace = client
    model_dir = workspace / "model" / "bosesph-kapampangan-v1"
    saved_model = model_dir / "model"
    saved_model.mkdir(parents=True)
    (saved_model / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "model_card.md").write_text("# Model", encoding="utf-8")
    (model_dir / "training_config.json").write_text(
        json.dumps({"language": "ceb"}),
        encoding="utf-8",
    )

    response = test_client.get("/demo/options")

    assert response.status_code == 200
    assert response.json() == {
        "languages": [
            {
                "id": "kapampangan",
                "label": "Kapampangan",
                "description": "Kapampangan speech with model-specific decoding.",
            },
            {
                "id": "auto",
                "label": "Auto-detect",
                "description": ("Let the selected model determine decoding language."),
            },
        ],
        "models": [
            {
                "id": "baseline",
                "label": "Whisper Small (baseline)",
                "model_path": "openai/whisper-small",
                "available": True,
                "unavailable_reason": None,
                "decoding_language": None,
            },
            {
                "id": "finetuned",
                "label": "BosesPH fine-tuned model",
                "model_path": "model/bosesph-kapampangan-v1/model",
                "available": True,
                "unavailable_reason": None,
                "decoding_language": "ceb",
            },
        ],
        "default_language_id": "kapampangan",
        "default_model_id": "baseline",
    }


def test_demo_options_disable_missing_finetuned_model(
    client: tuple[TestClient, Path],
) -> None:
    test_client, _ = client

    response = test_client.get("/demo/options")

    assert response.status_code == 200
    assert response.json()["models"][1] == {
        "id": "finetuned",
        "label": "BosesPH fine-tuned model",
        "model_path": "",
        "available": False,
        "unavailable_reason": "No local fine-tuned model found.",
        "decoding_language": None,
    }


def test_demo_options_use_first_sorted_complete_model(
    client: tuple[TestClient, Path],
) -> None:
    test_client, workspace = client
    model_root = workspace / "model"
    incomplete = model_root / "a-incomplete"
    selected = model_root / "b-selected"
    later = model_root / "z-later"

    (incomplete / "model").mkdir(parents=True)
    (incomplete / "model" / "config.json").write_text("{}", encoding="utf-8")
    for candidate in (selected, later):
        (candidate / "model").mkdir(parents=True)
        (candidate / "model_card.md").write_text("# Model", encoding="utf-8")
        (candidate / "model" / "config.json").write_text("{}", encoding="utf-8")

    response = test_client.get("/demo/options")

    assert response.status_code == 200
    assert response.json()["models"][1]["model_path"] == "model/b-selected/model"


def test_demo_options_ignore_candidate_symlink_outside_workspace(
    client: tuple[TestClient, Path],
    tmp_path: Path,
) -> None:
    test_client, workspace = client
    outside = tmp_path / "outside-candidate"
    (outside / "model").mkdir(parents=True)
    (outside / "model_card.md").write_text("# Outside", encoding="utf-8")
    (outside / "model" / "config.json").write_text("{}", encoding="utf-8")
    model_root = workspace / "model"
    model_root.mkdir(parents=True)
    (model_root / "external").symlink_to(outside, target_is_directory=True)

    response = test_client.get("/demo/options")

    assert response.status_code == 200
    assert response.json()["models"][1]["available"] is False


def test_demo_options_ignore_nested_model_symlink_outside_workspace(
    client: tuple[TestClient, Path],
    tmp_path: Path,
) -> None:
    test_client, workspace = client
    outside_model = tmp_path / "outside-model"
    outside_model.mkdir()
    (outside_model / "config.json").write_text("{}", encoding="utf-8")
    candidate = workspace / "model" / "local"
    candidate.mkdir(parents=True)
    (candidate / "model_card.md").write_text("# Local", encoding="utf-8")
    (candidate / "model").symlink_to(outside_model, target_is_directory=True)

    response = test_client.get("/demo/options")

    assert response.status_code == 200
    assert response.json()["models"][1]["available"] is False


def test_demo_options_ignore_external_model_config_symlink(
    client: tuple[TestClient, Path],
    tmp_path: Path,
) -> None:
    test_client, workspace = client
    outside_config = tmp_path / "config.json"
    outside_config.write_text("{}", encoding="utf-8")
    candidate = workspace / "model" / "local"
    model_dir = candidate / "model"
    model_dir.mkdir(parents=True)
    (candidate / "model_card.md").write_text("# Local", encoding="utf-8")
    (model_dir / "config.json").symlink_to(outside_config)

    response = test_client.get("/demo/options")

    assert response.status_code == 200
    assert response.json()["models"][1]["available"] is False


def test_demo_options_ignore_internal_model_symlink(
    client: tuple[TestClient, Path],
) -> None:
    test_client, workspace = client
    shared_config = workspace / "shared-config.json"
    shared_config.parent.mkdir(parents=True)
    shared_config.write_text("{}", encoding="utf-8")
    candidate = workspace / "model" / "local"
    model_dir = candidate / "model"
    model_dir.mkdir(parents=True)
    (candidate / "model_card.md").write_text("# Local", encoding="utf-8")
    (model_dir / "config.json").symlink_to(shared_config)

    response = test_client.get("/demo/options")

    assert response.status_code == 200
    assert response.json()["models"][1]["available"] is False


@pytest.mark.parametrize(
    "training_config",
    [None, "{invalid", "[]", json.dumps({"language": 7})],
)
def test_demo_options_default_malformed_training_language_to_tl(
    client: tuple[TestClient, Path],
    training_config: str | None,
) -> None:
    test_client, workspace = client
    model_dir = workspace / "model" / "local"
    (model_dir / "model").mkdir(parents=True)
    (model_dir / "model_card.md").write_text("# Model", encoding="utf-8")
    (model_dir / "model" / "config.json").write_text("{}", encoding="utf-8")
    if training_config is not None:
        (model_dir / "training_config.json").write_text(
            training_config,
            encoding="utf-8",
        )

    response = test_client.get("/demo/options")

    assert response.status_code == 200
    assert response.json()["models"][1]["decoding_language"] == "tl"


def test_demo_options_default_invalid_utf8_training_language_to_tl(
    client: tuple[TestClient, Path],
) -> None:
    test_client, workspace = client
    model_dir = workspace / "model" / "local"
    (model_dir / "model").mkdir(parents=True)
    (model_dir / "model_card.md").write_text("# Model", encoding="utf-8")
    (model_dir / "model" / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "training_config.json").write_bytes(
        b'{"language":"' + bytes([0xFF]) + b'"}'
    )

    response = test_client.get("/demo/options")

    assert response.status_code == 200
    assert response.json()["models"][1]["decoding_language"] == "tl"


def test_demo_options_strip_configured_training_language(
    client: tuple[TestClient, Path],
) -> None:
    test_client, workspace = client
    model_dir = workspace / "model" / "local"
    (model_dir / "model").mkdir(parents=True)
    (model_dir / "model_card.md").write_text("# Model", encoding="utf-8")
    (model_dir / "model" / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "training_config.json").write_text(
        json.dumps({"language": " ceb "}),
        encoding="utf-8",
    )

    response = test_client.get("/demo/options")

    assert response.status_code == 200
    assert response.json()["models"][1]["decoding_language"] == "ceb"


def test_select_demo_model_applies_model_specific_decoding(tmp_path: Path) -> None:
    model_dir = tmp_path / "model" / "local"
    (model_dir / "model").mkdir(parents=True)
    (model_dir / "model_card.md").write_text("# Model", encoding="utf-8")
    (model_dir / "model" / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "training_config.json").write_text(
        json.dumps({"language": "ceb"}),
        encoding="utf-8",
    )
    options = demo_api.discover_demo_options(tmp_path)

    baseline, baseline_language = demo_api.select_demo_model(
        options,
        "baseline",
        "kapampangan",
    )
    finetuned, finetuned_language = demo_api.select_demo_model(
        options,
        "finetuned",
        "kapampangan",
    )
    _, auto_language = demo_api.select_demo_model(options, "finetuned", "auto")

    assert baseline.id == "baseline"
    assert baseline_language is None
    assert finetuned.id == "finetuned"
    assert finetuned_language == "ceb"
    assert auto_language is None


@pytest.mark.parametrize(
    ("model_id", "language_id", "message"),
    [
        ("unknown", "kapampangan", "Unknown demo model: unknown"),
        ("finetuned", "kapampangan", "No local fine-tuned model found."),
        ("baseline", "unknown", "Unknown demo language: unknown"),
    ],
)
def test_select_demo_model_rejects_invalid_choices(
    tmp_path: Path,
    model_id: str,
    language_id: str,
    message: str,
) -> None:
    options = demo_api.discover_demo_options(tmp_path)

    with pytest.raises(ValueError, match=message):
        demo_api.select_demo_model(options, model_id, language_id)


def test_demo_transcribe_scores_reference_and_deletes_upload(
    client: tuple[TestClient, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, workspace = client
    wav_path = tmp_path / "clip.wav"
    write_pcm_wav(wav_path, duration=0.1)
    loaded_models: list[str] = []
    seen_paths: list[Path] = []

    def fake_load_model(model: str) -> object:
        loaded_models.append(model)
        return object()

    def fake_transcribe(
        pipe: object,
        audio_path: Path,
        *,
        language: str | None,
    ) -> str:
        seen_paths.append(audio_path)
        assert audio_path.is_file()
        assert language is None
        return "Masanting ya ing aldo"

    monkeypatch.setattr("bosesph.asr.load_model", fake_load_model)
    monkeypatch.setattr("bosesph.asr.transcribe_file", fake_transcribe)

    response = test_client.post(
        "/demo/transcribe",
        data={
            "model_id": "baseline",
            "language_id": "kapampangan",
            "reference": "Masanting ya ing aldo.",
        },
        files={"audio": ("../private.wav", wav_path.read_bytes(), "audio/wav")},
    )
    job = poll_job(test_client, response.json()["id"])

    assert response.status_code == 202
    assert job["status"] == "succeeded"
    assert job["progress"] == "transcribing"
    assert job["result"] == {
        "prediction": "Masanting ya ing aldo",
        "model_id": "baseline",
        "model_label": "Whisper Small (baseline)",
        "language_id": "kapampangan",
        "wer": 0.0,
        "cer": 0.0,
    }
    assert loaded_models == ["openai/whisper-small"]
    assert seen_paths
    assert seen_paths[0].name == "audio.wav"
    assert not seen_paths[0].parent.exists()
    assert not (workspace / ".demo_uploads").exists()


@pytest.mark.parametrize("reference", [None, "", "   "])
def test_demo_transcribe_without_reference_returns_null_metrics(
    client: tuple[TestClient, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reference: str | None,
) -> None:
    test_client, workspace = client
    wav_path = tmp_path / "clip.wav"
    write_pcm_wav(wav_path, duration=0.1)
    monkeypatch.setattr("bosesph.asr.load_model", lambda model: object())
    monkeypatch.setattr(
        "bosesph.asr.transcribe_file",
        lambda pipe, audio_path, *, language: "Mayap a abak",
    )
    data = {"model_id": "baseline", "language_id": "auto"}
    if reference is not None:
        data["reference"] = reference

    response = test_client.post(
        "/demo/transcribe",
        data=data,
        files={"audio": ("clip.wav", wav_path.read_bytes(), "audio/wav")},
    )
    job = poll_job(test_client, response.json()["id"])

    assert response.status_code == 202
    assert job["status"] == "succeeded"
    assert job["result"]["wer"] is None
    assert job["result"]["cer"] is None
    assert not (workspace / ".demo_uploads").exists()


def test_demo_transcribe_deletes_upload_after_failure(
    client: tuple[TestClient, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, workspace = client
    wav_path = tmp_path / "clip.wav"
    write_pcm_wav(wav_path, duration=0.1)

    monkeypatch.setattr("bosesph.asr.load_model", lambda model: object())

    def fail_transcription(*args: object, **kwargs: object) -> str:
        raise RuntimeError("inference failed")

    monkeypatch.setattr("bosesph.asr.transcribe_file", fail_transcription)

    response = test_client.post(
        "/demo/transcribe",
        data={"model_id": "baseline", "language_id": "auto"},
        files={"audio": ("clip.wav", wav_path.read_bytes(), "audio/wav")},
    )
    job = poll_job(test_client, response.json()["id"])

    assert response.status_code == 202
    assert job["status"] == "failed"
    assert job["error"] == "inference failed"
    assert not (workspace / ".demo_uploads").exists()


@pytest.mark.parametrize(
    ("data", "filename", "content", "expected"),
    [
        (
            {"model_id": "unknown", "language_id": "auto"},
            "clip.wav",
            b"RIFF",
            "Unknown demo model",
        ),
        (
            {"model_id": "baseline", "language_id": "unknown"},
            "clip.wav",
            b"RIFF",
            "Unknown demo language",
        ),
        (
            {"model_id": "finetuned", "language_id": "auto"},
            "clip.wav",
            b"RIFF",
            "No local fine-tuned model found",
        ),
        (
            {"model_id": "baseline", "language_id": "auto"},
            "clip.mp3",
            b"audio",
            "Only PCM WAV uploads are supported",
        ),
        (
            {"model_id": "baseline", "language_id": "auto"},
            "clip.wav",
            b"",
            "Uploaded audio is empty",
        ),
    ],
)
def test_demo_transcribe_rejects_invalid_input_before_job_submission(
    client: tuple[TestClient, Path],
    data: dict[str, str],
    filename: str,
    content: bytes,
    expected: str,
) -> None:
    test_client, workspace = client

    response = test_client.post(
        "/demo/transcribe",
        data=data,
        files={"audio": (filename, content, "audio/wav")},
    )

    assert response.status_code == 422
    assert expected in response.json()["detail"]
    assert test_client.get("/jobs").json() == []
    assert not (workspace / ".demo_uploads").exists()


def test_demo_transcribe_rejects_multiple_audio_files(
    client: tuple[TestClient, Path],
) -> None:
    test_client, workspace = client

    response = test_client.post(
        "/demo/transcribe",
        data={"model_id": "baseline", "language_id": "auto"},
        files=[
            ("audio", ("first.wav", b"RIFF-first", "audio/wav")),
            ("audio", ("second.wav", b"RIFF-second", "audio/wav")),
        ],
    )

    assert response.status_code == 422
    assert "Exactly one audio upload is required" in response.json()["detail"]
    assert test_client.get("/jobs").json() == []
    assert not (workspace / ".demo_uploads").exists()


def test_demo_transcribe_rejects_symlinked_upload_root(
    client: tuple[TestClient, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, workspace = client
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace.mkdir()
    (workspace / ".demo_uploads").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr("bosesph.asr.load_model", lambda model: object())
    monkeypatch.setattr(
        "bosesph.asr.transcribe_file",
        lambda pipe, audio_path, *, language: "Masanting",
    )

    response = test_client.post(
        "/demo/transcribe",
        data={"model_id": "baseline", "language_id": "auto"},
        files={"audio": ("clip.wav", b"RIFF", "audio/wav")},
    )

    assert response.status_code == 422
    assert "Demo upload root escapes workspace" in response.json()["detail"]
    assert test_client.get("/jobs").json() == []
    assert list(outside.iterdir()) == []


def test_demo_transcribe_resolves_finetuned_model_and_decoding_language(
    client: tuple[TestClient, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, workspace = client
    model_dir = workspace / "model" / "local"
    saved_model = model_dir / "model"
    saved_model.mkdir(parents=True)
    (saved_model / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "model_card.md").write_text("# Model", encoding="utf-8")
    (model_dir / "training_config.json").write_text(
        json.dumps({"language": "ceb"}),
        encoding="utf-8",
    )
    wav_path = tmp_path / "clip.wav"
    write_pcm_wav(wav_path, duration=0.1)
    loaded_models: list[str] = []
    decoding_languages: list[str | None] = []

    def fake_load_model(model: str) -> object:
        loaded_models.append(model)
        return object()

    def fake_transcribe(
        pipe: object,
        audio_path: Path,
        *,
        language: str | None,
    ) -> str:
        decoding_languages.append(language)
        return "Masanting"

    monkeypatch.setattr("bosesph.asr.load_model", fake_load_model)
    monkeypatch.setattr("bosesph.asr.transcribe_file", fake_transcribe)

    response = test_client.post(
        "/demo/transcribe",
        data={"model_id": "finetuned", "language_id": "kapampangan"},
        files={"audio": ("clip.wav", wav_path.read_bytes(), "audio/wav")},
    )
    job = poll_job(test_client, response.json()["id"])

    assert response.status_code == 202
    assert job["status"] == "succeeded"
    assert loaded_models == [str(saved_model.resolve())]
    assert decoding_languages == ["ceb"]
    assert not (workspace / ".demo_uploads").exists()


def test_demo_transcribe_cleanup_failure_preserves_result(
    client: tuple[TestClient, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    test_client, _ = client
    wav_path = tmp_path / "clip.wav"
    write_pcm_wav(wav_path, duration=0.1)
    monkeypatch.setattr("bosesph.asr.load_model", lambda model: object())
    monkeypatch.setattr(
        "bosesph.asr.transcribe_file",
        lambda pipe, audio_path, *, language: "Masanting",
    )

    def fail_cleanup(path: Path) -> None:
        raise OSError("cleanup denied")

    monkeypatch.setattr("bosesph.api.demo.shutil.rmtree", fail_cleanup)

    response = test_client.post(
        "/demo/transcribe",
        data={"model_id": "baseline", "language_id": "auto"},
        files={"audio": ("clip.wav", wav_path.read_bytes(), "audio/wav")},
    )
    job = poll_job(test_client, response.json()["id"])

    assert response.status_code == 202
    assert job["status"] == "succeeded"
    assert job["result"]["prediction"] == "Masanting"
    assert "Failed to remove demo upload directory" in caplog.text


def test_transcribe_job_uses_lazy_asr_services(
    client: tuple[TestClient, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, workspace = client
    (workspace / "dataset").mkdir(parents=True)
    (workspace / "dataset" / "test.csv").write_text(
        "audio_id,file_path,transcript,duration_seconds\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("bosesph.asr.load_model", lambda model: object())

    def transcribe_split(
        split_csv: Path,
        dataset_dir: Path,
        pipe: object,
        *,
        language: str | None,
        output_path: Path,
        progress_fn: object,
    ) -> list[TranscriptionResult]:
        progress_fn(1, 1)  # type: ignore[operator]
        return [
            TranscriptionResult(
                audio_id="pam_000001",
                reference="Masanting.",
                prediction="Masanting.",
                file_path="audio/pam_000001.wav",
            )
        ]

    monkeypatch.setattr("bosesph.asr.transcribe_split", transcribe_split)

    submitted = test_client.post(
        "/transcribe",
        json={
            "dataset": "dataset",
            "model": "test-model",
            "split": "test",
            "output": "benchmark/predictions.csv",
        },
    )
    job = poll_job(test_client, submitted.json()["id"])

    assert submitted.status_code == 202
    assert job["status"] == "succeeded"
    assert job["progress"] == "1/1"
    assert job["result"]["clip_count"] == 1


def test_train_job_uses_lazy_finetune_service(
    client: tuple[TestClient, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, _ = client

    class TrainingResult(BaseModel):
        model_path: str

    def finetune_model(
        dataset_dir: Path,
        output_dir: Path,
        **kwargs: object,
    ) -> TrainingResult:
        kwargs["progress_fn"]("starting")  # type: ignore[operator]
        return TrainingResult(model_path=str(output_dir / "model"))

    monkeypatch.setattr("bosesph.finetune.finetune_model", finetune_model)

    submitted = test_client.post(
        "/train",
        json={"dataset": "dataset", "output": "model/test"},
    )
    job = poll_job(test_client, submitted.json()["id"])

    assert submitted.status_code == 202
    assert job["status"] == "succeeded"
    assert job["progress"] == "starting"
    assert job["result"]["model_path"].endswith("model/test/model")


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("get", "/download-output", {"params": {"path": "../secret"}}),
        (
            "post",
            "/import-pld",
            {"json": {"source": "../source", "output": "dataset"}},
        ),
    ],
)
def test_traversal_paths_return_400(
    client: tuple[TestClient, Path],
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    test_client, _ = client

    response = getattr(test_client, method)(path, **kwargs)

    assert response.status_code == 400


def test_missing_dataset_returns_422(client: tuple[TestClient, Path]) -> None:
    test_client, _ = client

    response = test_client.post(
        "/normalize-transcripts",
        json={"dataset": "missing"},
    )

    assert response.status_code == 422
    assert "metadata.csv" in response.json()["detail"]


def test_openapi_documents_concrete_response_models() -> None:
    schema = create_app().openapi()

    assert (
        schema["paths"]["/import-pld"]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/IngestionReport"
    )
    assert (
        schema["paths"]["/build-dataset"]["post"]["responses"]["202"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/Job"
    )
