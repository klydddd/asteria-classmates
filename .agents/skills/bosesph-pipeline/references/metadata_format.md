# Metadata Format Reference

## Required Columns

| Column | Type | Rules |
|---|---|---|
| `audio_id` | string | `{lang}_{six_digits}` — e.g. `pam_000001`. Prefix must match `language`. |
| `file_path` | string | Relative POSIX path ending in `.wav`, `.mp3`, `.m4a`, or `.flac`. No `..` traversal. |
| `transcript` | string | Non-empty UTF-8 NFC. Only `[noise]`, `[laughter]`, `[unclear]`, `[silence]` tags allowed. |
| `language` | string | Lowercase ISO 639-3 code: `pam`, `tgl`, `ceb`, `ilo`, `hil`, `eng`, etc. |
| `speaker_id` | string | Anonymized, starts with `spk_` (e.g. `spk_001`). Never a real name. |
| `duration_seconds` | float | Positive. Warns outside 5–15s range. |
| `sample_rate` | int | Positive hertz. Warns if not 16000. |
| `split` | string | One of: `unassigned`, `train`, `validation`, `test`. |
| `quality_status` | string | One of: `pending`, `approved`, `needs_review`, `rejected`. |

## Optional Columns

| Column | Meaning |
|---|---|
| `source_id` | Links clip to its documented source |
| `region` | Geographic variety (no precise location) |
| `speaker_age_group` | Coarse, consented age category |
| `speaker_gender` | Consented, project-defined category |
| `recording_device` | General device description |
| `environment` | Recording conditions (e.g. `quiet indoor`) |
| `code_switch_languages` | Semicolon-separated ISO 639-3 codes (e.g. `eng;fil`) |
| `reviewer_notes` | Non-sensitive review context |

Unknown columns are **rejected** to prevent accidental PII inclusion.

## Validation

```bash
bosesph validate-metadata outputs/dataset/metadata.csv
bosesph validate-metadata metadata.csv --format json
```

Exit codes: `0` = valid, `1` = metadata errors, `2` = unreadable input.

## Example Row

```csv
audio_id,file_path,transcript,language,speaker_id,duration_seconds,sample_rate,split,quality_status
pam_000001,audio/pam_000001.wav,"Masanting ya ing aldo.",pam,spk_001,8.5,16000,unassigned,pending
```
