# Phase 2 PLD Audio Ingestion Design

## Goal

Implement the Phase 2 audio ingestion pipeline for Philippine Languages
Database (PLD) session folders, beginning with `PLD/PAM/0400`.

The user-facing command is:

```bash
bosesph import-pld PLD/PAM/0400 --output outputs/dataset
```

The command imports all usable recordings, preserves source files, standardizes
audio copies, writes BosesPH metadata, and records rejected inputs without
stopping the entire batch.

## Scope

This phase supports one PLD session directory containing:

- one session `.log` file;
- zero or more `.wav` recordings referenced by that log;
- PLD session and speaker fields in `Key = Value` form; and
- transcript rows containing a WAV filename, prompt-list filename, and quoted
  transcript.

Generic audio folders, CSV transcript imports, web uploads, transcript
normalization, reviewer interfaces, dataset splits, and ASR processing are
outside this phase.

## Command Interface

```text
bosesph import-pld SOURCE --output OUTPUT [--overwrite]
```

- `SOURCE` must be an existing PLD session directory.
- `OUTPUT` is the generated dataset directory.
- The command refuses to use a nonempty output directory unless `--overwrite`
  is supplied.
- `--overwrite` replaces only generated Phase 2 files inside `OUTPUT`; it never
  modifies `SOURCE`.

The command returns:

- exit code `0` when the batch completes, including batches containing
  individually rejected clips;
- exit code `2` for command-level failures such as a missing source directory,
  an invalid output location, a missing or ambiguous session log, or a
  structurally malformed session log.

## Architecture

Phase 2 uses focused modules rather than placing processing logic in the CLI:

- `src/bosesph/pld.py` parses PLD session logs into typed session and transcript
  records.
- `src/bosesph/audio.py` inspects WAV input and writes standardized output.
- `src/bosesph/ingestion.py` coordinates matching, status assignment, naming,
  output generation, and reporting.
- `src/bosesph/cli.py` parses arguments, invokes the ingestion service, prints a
  concise summary, and maps command-level errors to exit code `2`.

This separation keeps PLD parsing independent from audio processing and makes
both reusable by later API or UI layers.

## PLD Parsing

The parser reads the log as UTF-8 with an optional byte-order mark. It extracts:

- `SessionID` as `source_id`;
- `SessionEnvironment` as `environment`;
- `SpeakerID`, transformed to `spk_<lowercase-source-id>`;
- `SpeakerGender` as `speaker_gender`; and
- each transcript row's WAV filename, prompt-list filename, and transcript.

Exact age, speaker name, profession, parent dialects, and comments are not
copied into generated metadata.

Transcript rows are matched to WAV files by filename within the source
directory. Duplicate transcript filenames, malformed transcript rows, or more
than one session log make the session structurally ambiguous and fail the
command. A transcript reference with no WAV and a WAV with no transcript are
clip-level rejections recorded in the ingestion report.

## Audio Inspection and Standardization

The pipeline uses Python's standard `wave`, `array`, `struct`, and `math`
modules, with explicit PCM validation. Supported Phase 2 input is uncompressed
integer PCM WAV with 8-, 16-, 24-, or 32-bit samples.

Each input is checked for:

- readable WAV structure;
- nonzero frames and positive duration;
- supported PCM sample width;
- sample rate;
- channel count; and
- suspicious silence.

Suspicious silence is defined deterministically as either:

- an entire clip whose PCM samples have zero amplitude; or
- a clip whose normalized root-mean-square amplitude is at or below `0.001`
  (`-60 dBFS`).

Accepted and review-required recordings are written as:

```text
WAV, mono, 16000 Hz, signed 16-bit PCM
```

Conversion decodes samples to normalized floating-point values, averages
channels to mono, resamples with deterministic linear interpolation, clamps
values to `[-1.0, 1.0]`, and writes signed little-endian 16-bit samples. Source
recordings remain unchanged. This dependency-free converter is appropriate for
dataset standardization; higher-quality model preprocessing can be introduced
later behind the same audio interface if evaluation demonstrates a need.

## Deterministic Naming

Transcript entries are sorted by their original WAV filename. Each entry gets
the next six-digit identifier:

```text
pam_000001.wav
pam_000002.wav
```

The `pam` prefix is the ISO 639-3 language code for Kapampangan. Re-running the
same source session with the same implementation produces the same identifiers.
Rejected entries retain their assigned identifier in the report so the mapping
remains auditable, but no cleaned WAV is written for them.

## Status Rules

The existing metadata status vocabulary is used:

- `pending`: readable, non-silent audio between 5 and 15 seconds, with a
  matching nonempty transcript.
- `needs_review`: readable, non-silent audio with a matching transcript, but
  its duration is outside 5–15 seconds or its audio is suspiciously quiet.
- `rejected`: corrupt, empty, unsupported, unmatched, transcript-missing, or
  fully silent audio.

Sample-rate or channel differences alone do not require review when conversion
succeeds. The standardized output records `sample_rate=16000`.

## Generated Output

Successful execution creates:

```text
outputs/dataset/
  audio_clean/
    pam_000001.wav
    pam_000002.wav
  metadata.csv
  ingestion_report.json
```

`metadata.csv` contains accepted and review-required clips only and conforms to
the existing `MetadataRecord` schema. It uses:

- standardized relative paths such as `audio_clean/pam_000001.wav`;
- `language=pam`;
- `split=unassigned`;
- the assigned quality status;
- original transcript text;
- measured standardized duration and sample rate;
- anonymized speaker ID;
- session ID and environment where present; and
- concise, non-sensitive reviewer notes explaining review flags.

`ingestion_report.json` contains:

- source and output paths;
- total discovered WAV files and transcript rows;
- counts for `pending`, `needs_review`, and `rejected`;
- one result per assigned identifier;
- original filename;
- generated filename when exported;
- status;
- measured source audio properties when readable; and
- machine-readable reason codes and messages.

Reason codes include at least:

- `nonstandard_duration`;
- `suspicious_silence`;
- `corrupt_audio`;
- `empty_audio`;
- `unsupported_audio`;
- `missing_audio`;
- `missing_transcript`; and
- `conversion_failed`.

## Output Safety

Generation occurs in a temporary sibling directory. After all output files are
written successfully, publication uses same-filesystem renames. For overwrite,
the existing output is first renamed to a backup, the staged output is renamed
into place, and the backup is removed. If publication fails, the existing
output is restored from the backup.

Without `--overwrite`, an existing nonempty output directory is rejected.
With `--overwrite`, the implementation removes and replaces the output
directory only after source validation succeeds. Source files are never
renamed, deleted, or edited.

If a command-level failure occurs before publication, temporary generated files
are cleaned up and the existing output remains intact.

## Error Handling

Individual audio failures are isolated. The importer records the failure,
continues with remaining clips, and publishes the final report.

The command aborts without publishing partial output when:

- the source directory cannot be read;
- the session has no log or multiple logs;
- the log cannot be decoded or parsed structurally;
- output safety checks fail; or
- metadata or report serialization fails.

CLI errors are written to standard error. A successful batch prints output
location and status counts.

## Testing

Tests use temporary directories and generated PCM WAV fixtures. They cover:

- parsing BOM-prefixed PLD session metadata and transcript rows;
- rejection of ambiguous or malformed session logs;
- deterministic transcript-to-audio matching and naming;
- import of standard 16 kHz mono WAV;
- resampling and channel conversion;
- duration-based `pending` and `needs_review` assignment;
- silence, empty, corrupt, missing-audio, and missing-transcript rejection;
- valid `metadata.csv` output;
- complete `ingestion_report.json` counts and reason codes;
- overwrite refusal and replacement behavior;
- preservation of source bytes; and
- CLI output and exit codes.

Final integration verification runs the command against `PLD/PAM/0400` and
validates the generated `metadata.csv`. Generated dataset output remains
ignored by Git.

## Task Tracking

After implementation and verification:

- mark Phase 1.3 complete because `PLD/PAM/0400` supplies matched sample audio
  and transcripts;
- mark Phase 2.1 through Phase 2.4 complete in `Tasks.md`;
- check all four Phase 2 items in `Simple_Tasks.md`; and
- update `README.md` with the implemented command and current project status.
