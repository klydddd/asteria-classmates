# Dataset Metadata Format

BosesPH metadata is a UTF-8 CSV file with one row per audio clip. The validator
checks metadata only; it does not open audio files or verify that referenced
paths exist.

## Required columns

| Column | Type and contract |
|---|---|
| `audio_id` | Lowercase ISO 639-3 language code, underscore, and six digits, such as `pam_000001`. The prefix must equal `language`. |
| `file_path` | Relative POSIX path ending in `.wav`, `.mp3`, `.m4a`, or `.flac`. Absolute paths, backslashes, `.` segments, and `..` traversal are rejected. |
| `transcript` | Nonempty UTF-8 text in Unicode NFC. Only the documented special tags are allowed. |
| `language` | Lowercase ISO 639-3 code, such as `pam`, `fil`, or `eng`. |
| `speaker_id` | An anonymized lowercase identifier beginning with `spk_`, such as `spk_001`. Never use a name or contact detail. |
| `duration_seconds` | Positive number. Values outside 5–15 seconds produce a warning. |
| `sample_rate` | Positive integer in hertz. Values other than 16000 produce a warning. |
| `split` | `unassigned`, `train`, `validation`, or `test`. |
| `quality_status` | `pending`, `approved`, `needs_review`, or `rejected`. |

## Optional columns

All optional columns may be omitted. Empty optional CSV cells are treated as
missing values.

| Column | Meaning |
|---|---|
| `source_id` | Stable identifier linking the clip to its documented source. |
| `region` | Broad geographic variety, without precise private location data. |
| `speaker_age_group` | Coarse, consented age category rather than exact birth date. |
| `speaker_gender` | Consented, project-defined category. |
| `recording_device` | General microphone or device description. |
| `environment` | General recording conditions, such as `quiet indoor`. |
| `code_switch_languages` | Semicolon-separated lowercase ISO 639-3 codes, for example `eng;fil`. |
| `reviewer_notes` | Non-sensitive review context. |

Unknown columns are rejected so accidental personal or undocumented metadata
does not silently enter the dataset. `audio_id` and `file_path` must each be
unique across the file.

## Transcript annotations

The only supported annotations are:

```text
[noise]
[laughter]
[unclear]
[silence]
```

Tags are lowercase and use square brackets exactly as shown. See
[Transcription Guidelines](transcription_guidelines.md) for usage rules.

## Complete example

```csv
audio_id,file_path,transcript,language,speaker_id,duration_seconds,sample_rate,split,quality_status,source_id,region,speaker_age_group,speaker_gender,recording_device,environment,code_switch_languages,reviewer_notes
pam_000001,audio/pam_000001.wav,"Masanting ya ing aldo, magandang umaga, good morning.",pam,spk_001,8.5,16000,unassigned,pending,field_session_01,Pampanga,adult,unspecified,handheld recorder,quiet indoor,eng;fil,Consent and license verified.
```

Quote fields according to standard CSV rules when they contain commas, quotes,
or line breaks. Save the file as UTF-8.

## Validation

Install the package and validate a file:

```bash
bosesph validate-metadata sample_data/metadata_template.csv
bosesph validate-metadata metadata.csv --format json
```

The validator aggregates issues from all rows. Reports contain:

- `row_count`
- `valid_row_count`
- `error_count`
- `warning_count`
- `issues`, each with `severity`, `code`, `row`, `field`, and `message`

CSV row numbers include the header, so the first data row is row 2. Warnings do
not make a row invalid. Exit code `0` means there are no metadata errors, `1`
means metadata errors were found, and `2` means the input was unreadable or
malformed, or the CLI was used incorrectly.

The machine-readable contract is checked in at
[`metadata.schema.json`](metadata.schema.json). Regenerate it after model
changes:

```bash
bosesph export-metadata-schema --output docs/metadata.schema.json
```
