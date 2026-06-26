"""BosesPH MCP Server — exposes the speech pipeline as MCP tools.

Start with ``bosesph-mcp`` (stdio transport) or run directly::

    python -m bosesph.mcp.server

Configuration via environment variables:

* ``BOSESPH_WORKSPACE`` — root directory for pipeline inputs/outputs
  (default: ``outputs/``).
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from bosesph.mcp import tools

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "BosesPH Toolkit",
    instructions=(
        "BosesPH Toolkit is a CLI-first pipeline for building "
        "Philippine-language speech datasets, ASR benchmarks, and "
        "fine-tuned models. Use these tools to manage the pipeline."
    ),
)


def _workspace() -> Path:
    """Resolve the workspace root from the environment."""
    return Path(os.environ.get("BOSESPH_WORKSPACE", "outputs"))


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_project_status() -> dict:
    """Get the current BosesPH project status.

    Returns dataset availability, statistics, baseline and fine-tuned
    WER/CER metrics, and model information from the workspace.
    """
    return tools.get_project_status(_workspace())


@mcp.tool()
def validate_metadata(dataset: str) -> dict:
    """Validate a dataset's metadata.csv file.

    Args:
        dataset: Relative path to the dataset directory containing
            metadata.csv (e.g. "dataset").
    """
    return tools.validate_metadata(_workspace(), dataset)


@mcp.tool()
def import_pld_session(
    source: str,
    output: str,
    overwrite: bool = False,
) -> dict:
    """Import a PLD (Philippine Language Documentation) recording session.

    Parses session metadata and transcript rows, matches WAV files,
    validates audio quality, and produces a standardized dataset directory
    with metadata.csv and audio_clean/ files.

    Args:
        source: Relative path to the PLD session directory
            (e.g. "PLD/PAM/0400").
        output: Relative path for the ingestion output
            (e.g. "dataset").
        overwrite: Whether to overwrite an existing output directory.
    """
    return tools.import_pld_session(_workspace(), source, output, overwrite=overwrite)


@mcp.tool()
def normalize_transcripts(dataset: str) -> dict:
    """Normalize transcript formatting in a dataset.

    Args:
        dataset: Relative path to the dataset directory containing metadata.csv.
    """
    return tools.normalize_transcripts(_workspace(), dataset)


@mcp.tool()
def apply_review_decision(
    dataset: str, audio_id: str, decision: str, note: str | None = None
) -> dict:
    """Apply a review decision to a single clip.

    Args:
        dataset: Relative path to the dataset directory.
        audio_id: The ID of the clip to review (e.g., 'pam_000001').
        decision: 'approved', 'rejected', or 'needs_fix'.
        note: Optional reviewer note.
    """
    return tools.apply_review_decision(_workspace(), dataset, audio_id, decision, note)


@mcp.tool()
def build_dataset(
    dataset: str,
    output: str,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    overwrite: bool = False,
) -> dict:
    """Build a clean dataset with train/validation/test splits.

    Filters approved clips, copies audio, assigns speaker-aware splits,
    and generates statistics and a dataset card.

    Args:
        dataset: Relative path to source dataset with reviewed clips.
        output: Relative path for the built dataset output.
        train_ratio: Proportion of clips for training (default 0.70).
        val_ratio: Proportion of clips for validation (default 0.15).
        test_ratio: Proportion of clips for testing (default 0.15).
        seed: Random seed for reproducible splits.
        overwrite: Whether to overwrite an existing output directory.
    """
    return tools.build_dataset(
        _workspace(),
        dataset,
        output,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        seed=seed,
        overwrite=overwrite,
    )


@mcp.tool()
def transcribe_audio(
    audio_path: str,
    model: str = "openai/whisper-small",
    language: str | None = None,
) -> dict:
    """Transcribe a single audio file using a Whisper ASR model.

    Args:
        audio_path: Relative path to the audio file (WAV format).
        model: HuggingFace model ID or local path (default:
            "openai/whisper-small").
        language: Optional language hint for Whisper decoding.
    """
    return tools.transcribe_audio(
        _workspace(), audio_path, model=model, language=language
    )


@mcp.tool()
def transcribe_dataset(
    dataset: str,
    output: str,
    model: str = "openai/whisper-small",
    language: str | None = None,
    split: str = "test",
    limit: int | None = None,
) -> dict:
    """Transcribe an entire dataset split and write predictions CSV.

    Args:
        dataset: Relative path to the built dataset directory.
        output: Relative path for the predictions output CSV.
        model: HuggingFace model ID (default: "openai/whisper-small").
        language: Optional language hint for Whisper decoding.
        split: Which split to transcribe (default: "test").
        limit: Maximum number of clips to process (default: all).
    """
    return tools.transcribe_dataset(
        _workspace(),
        dataset,
        output,
        model=model,
        language=language,
        split=split,
        limit=limit,
    )


@mcp.tool()
def evaluate_predictions(
    predictions: str,
    references: str | None = None,
    model_name: str = "baseline",
    language: str = "kapampangan",
    output: str | None = None,
) -> dict:
    """Compute WER and CER from a predictions CSV file.

    Args:
        predictions: Relative path to the predictions CSV file.
        references: Optional relative path to a separate references CSV.
        model_name: Label for the model in the report (default: "baseline").
        language: Language label for the report (default: "kapampangan").
        output: Optional relative path for the results directory
            (writes results.json and report.md).
    """
    return tools.evaluate_predictions(
        _workspace(),
        predictions,
        references=references,
        model_name=model_name,
        language=language,
        output=output,
    )


@mcp.tool()
def get_dataset_stats() -> dict:
    """Get detailed dataset statistics.

    Returns total clips, duration, speakers, average clip length,
    language distribution, per-split breakdowns, and status counts.
    Requires build-dataset to have been run first.
    """
    return tools.get_dataset_stats(_workspace())


@mcp.tool()
def list_dataset_clips(
    split: str = "test",
    limit: int = 50,
) -> dict:
    """List clips in a dataset split.

    Args:
        split: Split name — "train", "validation", or "test"
            (default: "test").
        limit: Maximum number of clips to return (default: 50).
    """
    return tools.list_dataset_clips(_workspace(), split, limit=limit)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("bosesph://dataset/stats")
def dataset_stats_resource() -> str:
    """Dataset statistics as JSON.

    Returns the full dataset_stats.json content produced by the
    build-dataset step.
    """
    import json

    try:
        data = tools.get_dataset_stats(_workspace())
    except FileNotFoundError:
        return json.dumps({"error": "No dataset built yet."})
    return json.dumps(data, indent=2)


@mcp.resource("bosesph://benchmark/report")
def benchmark_report_resource() -> str:
    """Latest benchmark report in Markdown format.

    Returns the report.md file from the most recent baseline evaluation.
    """
    ws = _workspace().resolve()
    report_path = ws / "benchmark" / "baseline" / "report.md"
    if not report_path.is_file():
        # Fall back to report.md directly under benchmark/
        report_path = ws / "benchmark" / "report.md"
    if not report_path.is_file():
        return "No benchmark report found. Run evaluate first."
    return report_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt()
def full_pipeline() -> str:
    """Step-by-step instructions for running the complete BosesPH pipeline.

    Use this prompt to guide an LLM through the full workflow from raw
    audio to a benchmarked, fine-tuned model.
    """
    return """You are helping a developer run the BosesPH speech pipeline.
Follow these steps in order:

1. **Check project status** — Call `get_project_status` to see what's
   already been done.

2. **Import audio** — If no dataset exists, call `import_pld_session`
   with the PLD session directory (e.g. source="PLD/PAM/0400",
   output="dataset").

3. **Normalize transcripts** — Call `normalize_transcripts` with
   dataset="dataset" to clean up formatting.

4. **Build dataset** — Call `build_dataset` with dataset="dataset",
   output="dataset" to create train/validation/test splits from
   approved clips.

5. **Review statistics** — Call `get_dataset_stats` to verify the
   dataset was built correctly.

6. **Transcribe test split** — Call `transcribe_dataset` with
   dataset="dataset", output="benchmark/baseline_predictions.csv",
   split="test".

7. **Evaluate results** — Call `evaluate_predictions` with
   predictions="benchmark/baseline_predictions.csv",
   output="benchmark/baseline" to compute WER/CER.

8. **Report** — Summarize the results and suggest next steps
   (fine-tuning, more data, different model).
"""


@mcp.prompt()
def evaluate_model(
    model_path: str = "openai/whisper-small",
    split: str = "test",
) -> str:
    """Instructions for benchmarking a specific ASR model.

    Args:
        model_path: HuggingFace model ID or local model directory.
        split: Dataset split to evaluate on.
    """
    return f"""You are benchmarking the ASR model: {model_path}

Steps:
1. Call `get_project_status` to confirm a dataset is built.
2. Call `transcribe_dataset` with model="{model_path}", split="{split}",
   dataset="dataset", output="benchmark/predictions.csv".
3. Call `evaluate_predictions` with
   predictions="benchmark/predictions.csv",
   output="benchmark/evaluation".
4. Summarize the WER and CER results.
5. If a baseline result exists, compare the two and explain whether
   this model improves on the baseline.
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the BosesPH MCP server using stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
