# Kapampangan Transcription Guidelines

These rules prioritize a source-faithful record of what is spoken. They do not
silently rewrite a speaker's variety into a different orthography.

## Spelling and Unicode

- Transcribe the Kapampangan words actually spoken using a consistent spelling
  system selected for the dataset.
- Preserve meaningful diacritics present in the chosen transcription. Do not
  remove or invent them during normalization.
- Save text as UTF-8 in Unicode NFC. NFC normalization changes Unicode storage,
  not spelling or orthography.
- Do not translate, modernize, or convert words merely to make them look more
  familiar to Filipino or English readers.

## Spoken content

- Preserve repetitions, restarts, hesitations, and discourse markers when they
  are audible. Do not silently improve grammar.
- Transcribe spoken code-switching in the language used. Do not translate
  English, Filipino, or another language back into Kapampangan.
- Record every code-switched language in `code_switch_languages` using
  semicolon-separated lowercase ISO 639-3 codes, such as `eng;fil`.
- Do not add a code-switch code for proper names alone unless the project has
  explicitly documented that convention.

## Punctuation and casing

- Use sentence casing and ordinary terminal punctuation when the utterance has
  a clear boundary.
- Use commas and question marks consistently and conservatively.
- Do not use punctuation to encode pauses, emotion, or timing with false
  precision.
- Avoid repeated decorative punctuation such as `!!!` or `...` unless the
  project adopts and documents a specific linguistic convention.

## Special tags

Use only these lowercase tags:

- `[noise]` — non-speech sound materially overlaps or interrupts speech.
- `[laughter]` — audible laughter.
- `[unclear]` — speech is present but cannot be transcribed reliably.
- `[silence]` — a meaningful period of silence within the selected clip.

Place a tag at the point where the event occurs. Do not use tags for routine
breaths or insignificant background sound. Never invent new bracketed tags in
metadata; propose and document a schema change first.

## Review and rejection

Reviewers should compare the complete transcript against the recording and
confirm spelling, language labels, tags, and code-switch metadata.

Reject or securely remove a clip if it contains sensitive personal information,
including private addresses, phone numbers, account details, medical details,
or identifying information that the speaker did not explicitly consent to
publish. Do not copy that information into `reviewer_notes`.

Also reject clips when the license or speaker consent does not permit the
intended storage, redistribution, or model-training use.
