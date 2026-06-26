"""Tests for the BosesPH MCP server and tool wrappers."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# tools.py helpers
# ---------------------------------------------------------------------------


class TestResolve:
    """Path resolution and traversal rejection."""

    def test_valid_relative(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import _resolve

        target = tmp_path / "a" / "b"
        target.mkdir(parents=True)
        assert _resolve(tmp_path, "a/b") == target

    def test_rejects_absolute(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import _resolve

        with pytest.raises(ValueError, match="relative POSIX"):
            _resolve(tmp_path, "/etc/passwd")

    def test_rejects_traversal(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import _resolve

        with pytest.raises(ValueError, match="traversal"):
            _resolve(tmp_path, "a/../../../etc")

    def test_rejects_empty(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import _resolve

        with pytest.raises(ValueError, match="non-empty"):
            _resolve(tmp_path, "")

    def test_rejects_backslash(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import _resolve

        with pytest.raises(ValueError, match="relative POSIX"):
            _resolve(tmp_path, "a\\b")


# ---------------------------------------------------------------------------
# tools.py - get_project_status
# ---------------------------------------------------------------------------


class TestGetProjectStatus:
    def test_empty_workspace(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import get_project_status

        status = get_project_status(tmp_path)
        assert status["dataset_available"] is False
        assert status["dataset_stats"] is None
        assert status["baseline_metrics"] is None
        assert status["finetuned_metrics"] is None
        assert status["model_available"] is False

    def test_with_dataset_stats(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import get_project_status

        stats_dir = tmp_path / "dataset_30spk"
        stats_dir.mkdir()
        stats = {"total_clips": 100, "total_duration_seconds": 600.0}
        (stats_dir / "dataset_stats.json").write_text(
            json.dumps(stats), encoding="utf-8"
        )
        status = get_project_status(tmp_path)
        assert status["dataset_available"] is True
        assert status["dataset_stats"]["total_clips"] == 100

    def test_with_baseline_metrics(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import get_project_status

        metrics_dir = tmp_path / "benchmark" / "baseline_small_tl"
        metrics_dir.mkdir(parents=True)
        (metrics_dir / "results.json").write_text(
            json.dumps({"wer": 0.45, "cer": 0.22}), encoding="utf-8"
        )
        status = get_project_status(tmp_path)
        assert status["baseline_metrics"] == {"wer": 0.45, "cer": 0.22}

    def test_with_model(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import get_project_status

        model_dir = tmp_path / "model" / "my-model-v1"
        model_dir.mkdir(parents=True)
        (model_dir / "model_card.md").write_text("# Model", encoding="utf-8")
        status = get_project_status(tmp_path)
        assert status["model_available"] is True
        assert status["model_version"] == "my-model-v1"


# ---------------------------------------------------------------------------
# tools.py - get_dataset_stats & list_dataset_clips
# ---------------------------------------------------------------------------


class TestGetDatasetStats:
    def test_missing(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import get_dataset_stats

        with pytest.raises(FileNotFoundError, match="dataset_stats"):
            get_dataset_stats(tmp_path)

    def test_present(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import get_dataset_stats

        stats_dir = tmp_path / "dataset"
        stats_dir.mkdir()
        expected = {"total_clips": 50}
        (stats_dir / "dataset_stats.json").write_text(
            json.dumps(expected), encoding="utf-8"
        )
        result = get_dataset_stats(tmp_path)
        assert result["total_clips"] == 50


class TestListDatasetClips:
    def test_missing_split(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import list_dataset_clips

        with pytest.raises(FileNotFoundError, match="test.csv"):
            list_dataset_clips(tmp_path, "test")

    def test_lists_clips(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import list_dataset_clips

        dataset_dir = tmp_path / "dataset"
        dataset_dir.mkdir()
        split_csv = dataset_dir / "test.csv"
        with split_csv.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["audio_id", "transcript"])
            writer.writeheader()
            for i in range(5):
                writer.writerow(
                    {"audio_id": f"clip_{i:03d}", "transcript": f"text {i}"}
                )
        result = list_dataset_clips(tmp_path, "test", limit=3)
        assert result["split"] == "test"
        assert result["clip_count"] == 3
        assert len(result["clips"]) == 3
        assert result["clips"][0]["audio_id"] == "clip_000"


# ---------------------------------------------------------------------------
# tools.py - validate_metadata (mocked service)
# ---------------------------------------------------------------------------


class TestValidateMetadata:
    def test_missing_metadata_csv(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import validate_metadata

        dataset_dir = tmp_path / "dataset"
        dataset_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="metadata.csv"):
            validate_metadata(tmp_path, "dataset")

    def test_calls_service(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import validate_metadata

        dataset_dir = tmp_path / "dataset"
        dataset_dir.mkdir()
        (dataset_dir / "metadata.csv").write_text("audio_id\n", encoding="utf-8")

        mock_report = mock.MagicMock()
        mock_report.model_dump.return_value = {"valid": True, "issues": []}

        with mock.patch(
            "bosesph.metadata.validate_metadata_csv", return_value=mock_report
        ):
            result = validate_metadata(tmp_path, "dataset")
        assert result == {"valid": True, "issues": []}


# ---------------------------------------------------------------------------
# tools.py - import_pld_session (mocked service)
# ---------------------------------------------------------------------------


class TestImportPldSession:
    def test_calls_service(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import import_pld_session

        source_dir = tmp_path / "PLD"
        source_dir.mkdir()

        mock_report = mock.MagicMock()
        mock_report.model_dump.return_value = {"accepted": 10, "rejected": 2}

        with mock.patch(
            "bosesph.ingestion.import_pld_session", return_value=mock_report
        ):
            result = import_pld_session(tmp_path, "PLD", "dataset")
        assert result == {"accepted": 10, "rejected": 2}


# ---------------------------------------------------------------------------
# tools.py - normalize_transcripts (mocked service)
# ---------------------------------------------------------------------------


class TestNormalizeTranscripts:
    def test_calls_service(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import normalize_transcripts

        dataset_dir = tmp_path / "dataset"
        dataset_dir.mkdir()

        mock_report = mock.MagicMock()
        mock_report.model_dump.return_value = {"normalized": 5, "warnings": 0}

        with mock.patch(
            "bosesph.transcripts.normalize_dataset", return_value=mock_report
        ):
            result = normalize_transcripts(tmp_path, "dataset")
        assert result == {"normalized": 5, "warnings": 0}


# ---------------------------------------------------------------------------
# tools.py - build_dataset (mocked service)
# ---------------------------------------------------------------------------


class TestBuildDataset:
    def test_calls_service(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import build_dataset

        source_dir = tmp_path / "source"
        source_dir.mkdir()

        mock_result = mock.MagicMock()
        mock_result.model_dump.return_value = {
            "total_clips": 80,
            "splits": {"train": 56, "validation": 12, "test": 12},
        }

        with mock.patch(
            "bosesph.dataset.build_dataset", return_value=mock_result
        ):
            result = build_dataset(tmp_path, "source", "output", seed=99)
        assert result["total_clips"] == 80


# ---------------------------------------------------------------------------
# tools.py - evaluate_predictions (mocked service)
# ---------------------------------------------------------------------------


class TestEvaluatePredictions:
    def test_calls_service(self, tmp_path: Path) -> None:
        from bosesph.mcp.tools import evaluate_predictions

        preds_csv = tmp_path / "predictions.csv"
        with preds_csv.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=["audio_id", "reference", "prediction"]
            )
            writer.writeheader()
            writer.writerow(
                {"audio_id": "a", "reference": "hello", "prediction": "hi"}
            )

        mock_metrics = mock.MagicMock()
        mock_metrics.model_dump.return_value = {"wer": 0.5, "cer": 0.3}

        with mock.patch(
            "bosesph.asr.evaluate_predictions", return_value=mock_metrics
        ):
            result = evaluate_predictions(tmp_path, "predictions.csv")
        assert result == {"wer": 0.5, "cer": 0.3}


# ---------------------------------------------------------------------------
# server.py - tool registration
# ---------------------------------------------------------------------------


class TestMcpServerRegistration:
    """Verify the FastMCP server registers the expected tools, resources,
    and prompts."""

    def test_all_tools_registered(self) -> None:
        from bosesph.mcp.server import mcp

        tool_names = {t.name for t in mcp._tool_manager.list_tools()}
        expected = {
            "get_project_status",
            "validate_metadata",
            "import_pld_session",
            "normalize_transcripts",
            "build_dataset",
            "transcribe_audio",
            "transcribe_dataset",
            "evaluate_predictions",
            "get_dataset_stats",
            "list_dataset_clips",
        }
        assert expected.issubset(tool_names), (
            f"Missing tools: {expected - tool_names}"
        )

    def test_tool_count(self) -> None:
        from bosesph.mcp.server import mcp

        tool_list = mcp._tool_manager.list_tools()
        assert len(tool_list) == 11

    def test_resources_registered(self) -> None:
        from bosesph.mcp.server import mcp

        resources = mcp._resource_manager.list_resources()
        uris = {str(r.uri) for r in resources}
        assert "bosesph://dataset/stats" in uris
        assert "bosesph://benchmark/report" in uris

    def test_prompts_registered(self) -> None:
        from bosesph.mcp.server import mcp

        prompts = mcp._prompt_manager.list_prompts()
        prompt_names = {p.name for p in prompts}
        assert "full_pipeline" in prompt_names
        assert "evaluate_model" in prompt_names


# ---------------------------------------------------------------------------
# server.py - resource content
# ---------------------------------------------------------------------------


class TestMcpResources:
    def test_dataset_stats_resource_missing(self, tmp_path: Path) -> None:
        from bosesph.mcp.server import dataset_stats_resource

        with mock.patch(
            "bosesph.mcp.server._workspace", return_value=tmp_path
        ):
            content = dataset_stats_resource()
        data = json.loads(content)
        assert "error" in data

    def test_dataset_stats_resource_present(self, tmp_path: Path) -> None:
        from bosesph.mcp.server import dataset_stats_resource

        stats_dir = tmp_path / "dataset"
        stats_dir.mkdir()
        expected = {"total_clips": 42}
        (stats_dir / "dataset_stats.json").write_text(
            json.dumps(expected), encoding="utf-8"
        )
        with mock.patch(
            "bosesph.mcp.server._workspace", return_value=tmp_path
        ):
            content = dataset_stats_resource()
        data = json.loads(content)
        assert data["total_clips"] == 42

    def test_benchmark_report_missing(self, tmp_path: Path) -> None:
        from bosesph.mcp.server import benchmark_report_resource

        with mock.patch(
            "bosesph.mcp.server._workspace", return_value=tmp_path
        ):
            content = benchmark_report_resource()
        assert "No benchmark report" in content

    def test_benchmark_report_present(self, tmp_path: Path) -> None:
        from bosesph.mcp.server import benchmark_report_resource

        report_dir = tmp_path / "benchmark" / "baseline"
        report_dir.mkdir(parents=True)
        (report_dir / "report.md").write_text(
            "# Benchmark\nWER: 0.45", encoding="utf-8"
        )
        with mock.patch(
            "bosesph.mcp.server._workspace", return_value=tmp_path
        ):
            content = benchmark_report_resource()
        assert "Benchmark" in content
        assert "0.45" in content


# ---------------------------------------------------------------------------
# server.py - prompts
# ---------------------------------------------------------------------------


class TestMcpPrompts:
    def test_full_pipeline_prompt(self) -> None:
        from bosesph.mcp.server import full_pipeline

        text = full_pipeline()
        assert "get_project_status" in text
        assert "import_pld_session" in text
        assert "build_dataset" in text

    def test_evaluate_model_prompt(self) -> None:
        from bosesph.mcp.server import evaluate_model

        text = evaluate_model(model_path="my-model", split="validation")
        assert "my-model" in text
        assert "validation" in text
