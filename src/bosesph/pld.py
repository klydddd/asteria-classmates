"""Parser for Philippine Languages Database session logs."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path

KEY_VALUE_PATTERN = re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9]*)\s*=\s*(?P<value>.*)$")
TRANSCRIPT_ROW_PATTERN = re.compile(
    r'^(?P<filename>\S+\.wav)\s+"(?P<prompt>[^"]+)"\s+' r'(?P<transcript>".*")$',
    re.IGNORECASE,
)
NOT_RECORDED_PATTERN = re.compile(
    r'^NOT_RECORDED\s+"[^"]+"\s+".*"$',
    re.IGNORECASE,
)


class PldParseError(ValueError):
    """Raised when a PLD session directory or log is structurally invalid."""


@dataclass(frozen=True)
class PldTranscript:
    """One transcript row from a PLD session log."""

    filename: str
    prompt_list: str
    transcript: str


@dataclass(frozen=True)
class PldSession:
    """Parsed non-sensitive metadata and transcripts for one PLD session."""

    source: Path
    session_id: str
    environment: str | None
    speaker_id: str
    speaker_gender: str | None
    transcripts: tuple[PldTranscript, ...]


def _unquote(value: str) -> str:
    try:
        parts = shlex.split(value)
    except ValueError as error:
        raise PldParseError(f"malformed session field: {error}") from error
    if len(parts) != 1:
        raise PldParseError("session field must contain exactly one value")
    return parts[0]


def parse_pld_session(source: str | Path) -> PldSession:
    """Parse exactly one PLD log from a session directory."""
    source_path = Path(source)
    if not source_path.is_dir():
        raise PldParseError(f"source directory does not exist: {source_path}")

    logs = sorted(source_path.glob("*.log"))
    if len(logs) != 1:
        raise PldParseError(
            f"source directory must contain exactly one .log file; found {len(logs)}"
        )

    try:
        lines = logs[0].read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as error:
        raise PldParseError(f"cannot read PLD session log: {error}") from error

    fields: dict[str, str] = {}
    transcripts: list[PldTranscript] = []
    filenames: set[str] = set()

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        field_match = KEY_VALUE_PATTERN.fullmatch(line)
        if field_match:
            key = field_match.group("key")
            fields[key] = _unquote(field_match.group("value"))
            continue
        if NOT_RECORDED_PATTERN.fullmatch(line):
            continue
        if ".wav" not in line.lower():
            raise PldParseError(f"unrecognized log line {line_number}")
        transcript_match = TRANSCRIPT_ROW_PATTERN.fullmatch(line)
        if transcript_match is None:
            raise PldParseError(f"malformed transcript row {line_number}")
        filename = transcript_match.group("filename")
        prompt_list = transcript_match.group("prompt")
        transcript_envelope = transcript_match.group("transcript")
        transcript = transcript_envelope[1:-1]
        if filename in filenames:
            raise PldParseError(f"duplicate transcript filename: {filename}")
        filenames.add(filename)
        transcripts.append(
            PldTranscript(
                filename=filename,
                prompt_list=prompt_list,
                transcript=transcript,
            )
        )

    session_id = fields.get("SessionID")
    speaker_source_id = fields.get("SpeakerID")
    if not session_id:
        raise PldParseError("required SessionID field is missing")
    if not speaker_source_id:
        raise PldParseError("required SpeakerID field is missing")

    normalized_speaker = re.sub(
        r"[^a-z0-9]+",
        "_",
        speaker_source_id.lower(),
    ).strip("_")
    if not normalized_speaker:
        raise PldParseError("SpeakerID cannot be anonymized safely")

    return PldSession(
        source=source_path,
        session_id=session_id,
        environment=fields.get("SessionEnvironment") or None,
        speaker_id=f"spk_{normalized_speaker}",
        speaker_gender=fields.get("SpeakerGender") or None,
        transcripts=tuple(transcripts),
    )
