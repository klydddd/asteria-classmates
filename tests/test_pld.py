from __future__ import annotations

from pathlib import Path

import pytest

from bosesph.pld import PldParseError, parse_pld_session


def write_log(directory: Path, content: str, name: str = "session.log") -> Path:
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return path


def valid_log(*transcript_rows: str) -> str:
    header = (
        '\ufeffSessionID = "120223.051412"\n'
        'SessionEnvironment = "closed empty room"\n'
        'SpeakerID = "0400"\n'
        'SpeakerGender = "male"\n'
    )
    return header + "".join(f"{row}\n" for row in transcript_rows)


def test_parse_pld_session_reads_bom_metadata_and_transcripts(
    tmp_path: Path,
) -> None:
    write_log(
        tmp_path,
        valid_log(
            'clip.0002.wav "KAP_Iso.txt" "Masanting ya ing aldo."',
        ),
    )

    session = parse_pld_session(tmp_path)

    assert session.session_id == "120223.051412"
    assert session.environment == "closed empty room"
    assert session.speaker_id == "spk_0400"
    assert session.speaker_gender == "male"
    assert session.transcripts[0].filename == "clip.0002.wav"
    assert session.transcripts[0].prompt_list == "KAP_Iso.txt"
    assert session.transcripts[0].transcript == "Masanting ya ing aldo."


def test_parse_pld_session_preserves_quotes_inside_transcript(
    tmp_path: Path,
) -> None:
    write_log(
        tmp_path,
        valid_log(
            'clip.wav "KAP_Essay.txt" '
            '""Lalung mayap, Ginung Matsing", ing pakibat."',
        ),
    )

    session = parse_pld_session(tmp_path)

    assert session.transcripts[0].transcript == (
        '"Lalung mayap, Ginung Matsing", ing pakibat.'
    )


def test_parse_pld_session_skips_not_recorded_prompt_rows(
    tmp_path: Path,
) -> None:
    write_log(
        tmp_path,
        valid_log(
            'clip.wav "KAP_Essay.txt" "Recorded text."',
            'NOT_RECORDED "KAP_Essay.txt" "Prompt without audio."',
        ),
    )

    session = parse_pld_session(tmp_path)

    assert [row.filename for row in session.transcripts] == ["clip.wav"]


@pytest.mark.parametrize("log_count", [0, 2])
def test_parse_pld_session_requires_exactly_one_log(
    tmp_path: Path,
    log_count: int,
) -> None:
    for index in range(log_count):
        write_log(tmp_path, valid_log(), name=f"session-{index}.log")

    with pytest.raises(PldParseError, match="exactly one"):
        parse_pld_session(tmp_path)


@pytest.mark.parametrize(
    "content",
    [
        valid_log('clip.wav "prompt.txt"'),
        valid_log('clip.wav "prompt.txt" "one"', 'clip.wav "prompt.txt" "two"'),
        (
            'SessionEnvironment = "room"\n'
            'SpeakerID = "0400"\n'
            'clip.wav "prompt.txt" "text"\n'
        ),
        (
            'SessionID = "session"\n'
            'SessionEnvironment = "room"\n'
            'clip.wav "prompt.txt" "text"\n'
        ),
    ],
)
def test_parse_pld_session_rejects_structural_ambiguity(
    tmp_path: Path,
    content: str,
) -> None:
    write_log(tmp_path, content)

    with pytest.raises(PldParseError):
        parse_pld_session(tmp_path)
