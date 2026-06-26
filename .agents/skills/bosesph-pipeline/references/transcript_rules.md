# Transcript Rules Reference

## Supported Tags

Only these four lowercase tags are permitted:

```
[noise]      — non-speech sound overlapping speech
[laughter]   — audible laughter
[unclear]    — speech present but not reliably transcribable
[silence]    — meaningful silence within the clip
```

**Never invent new bracketed tags.** Propose and document a schema change first.

## Transcription Principles

1. **Transcribe what is spoken** — do not correct grammar or "improve" speech
2. **Preserve repetitions** — restarts, hesitations, discourse markers stay
3. **Keep code-switching** — if a speaker says English or Filipino words,
   transcribe them as-is in the original language
4. **Record code-switching metadata** — add ISO 639-3 codes to
   `code_switch_languages` (e.g. `eng;fil`)
5. **Use sentence casing** — capitalize only the first word and proper nouns
6. **Punctuation is conservative** — do not use `!!!` or `...` unless
   explicitly documented as a project convention
7. **Save as UTF-8 NFC** — this normalizes Unicode storage, not spelling
8. **Do not translate** — never convert words to make them "more familiar"
   to Filipino or English readers

## Rejection Criteria

Reject a clip if it contains:

- Private addresses, phone numbers, or account details
- Medical details or identifying information without consent
- Content whose license does not permit storage or model training

Do **not** copy sensitive information into `reviewer_notes`.

## Example Transcript

Good:
```
Masanting ya ing aldo, magandang umaga [noise] good morning.
```

Bad (translated code-switch):
```
Masanting ya ing aldo, magandang umaga [noise] magandang umaga.
```

Bad (invented tag):
```
Masanting ya ing aldo [cough] magandang umaga.
```
