# Tasks.md — BosesPH Toolkit Build Plan

## Project Goal

Build **BosesPH Toolkit**, an open-source pipeline that turns raw Philippine-language speech recordings into:

1. a cleaned and standardized speech dataset,
2. train/validation/test benchmark splits,
3. evaluation results using WER/CER,
4. an optional fine-tuned ASR model for a target Philippine language or dialect variety,
5. a simple demo/API that developers can reuse.

**Recommended MVP pilot language:** Kapampangan, because it is locally relevant and easier to validate if the team can access native speakers. The pipeline must still be designed so that another developer can replace Kapampangan with Ilocano, Waray, Hiligaynon, Cebuano, or another Philippine language.

---

## Winning Strategy

The judges should understand that this is **not just a transcription app**. It is a reusable developer toolkit.

| Criteria | What we must show |
|---|---|
| Innovation & Creativity | Reusable speech-resource pipeline for underrepresented Philippine languages, not only a one-time app. |
| Technical Execution | Working ingestion, cleaning, dataset split, benchmark, ASR inference/fine-tuning, and export. |
| Design & UX | Clear dashboard/demo showing the full workflow from raw audio to model output. |
| Theme Relevance & Impact | Helps future developers and communities build inclusive voice technology for Philippine languages. |

---

## MVP Scope

### Must Have

- Upload or import raw audio files.
- Add or import transcripts and metadata.
- Validate audio and transcript quality.
- Convert audio into a consistent format.
- Produce a clean dataset folder.
- Produce train/validation/test splits.
- Run baseline ASR transcription.
- Calculate WER and CER.
- Export dataset, benchmark files, and documentation.
- Provide a demo screen or notebook showing the workflow.

### Should Have

- Fine-tune an ASR model on the cleaned dataset.
- Compare baseline model vs fine-tuned model.
- Generate a dataset card and model card automatically.
- Provide a simple API for upload/transcribe/evaluate.

### Nice to Have

- Community reviewer workflow.
- Speaker diversity dashboard.
- Language detection or code-switching tags.
- Leaderboard for model results.
- Hugging Face dataset/model publishing.

---

# Phase 0 — Team Alignment and Setup

## 0.1 Define the final pitch

**Task:** Write a one-sentence project definition.

Suggested pitch:

> BosesPH Toolkit is an open-source pipeline that converts raw Philippine-language speech recordings into clean datasets, benchmarks, and fine-tuned ASR models for underrepresented Filipino language communities.

**Done when:** Everyone on the team can explain the project in 30 seconds.

## 0.2 Choose the pilot language

**Recommended:** Kapampangan.

**Why:** Local relevance, accessible speakers, and strong theme fit.

**Done when:** The team has chosen one MVP language and 1–2 backup languages.

## 0.3 Create the repository

Recommended repository name:

```text
bosesph-toolkit
```

Initial folders:

```text
bosesph-toolkit/
  apps/
    web/
    api/
  ml/
    data/
    training/
    evaluation/
  docs/
  sample_data/
  scripts/
  outputs/
```

**Done when:** Repository is created with README.md, license, and initial folder structure.

---

# Phase 1 — Dataset Design

## 1.1 Define the required metadata fields

**Status: Complete (June 25, 2026).**

Create a standard metadata schema.

Recommended columns:

```csv
audio_id,file_path,transcript,language,region,speaker_id,speaker_age_group,speaker_gender,duration_seconds,sample_rate,split,quality_status,reviewer_notes
```

**Done when:** The team has a documented `metadata.csv` format.

## 1.2 Define transcript rules

**Status: Complete (June 25, 2026).**

Create rules for writing transcripts consistently.

Include:

- how to handle punctuation,
- how to handle repeated words,
- how to handle English/Filipino code-switching,
- how to handle unclear speech,
- how to spell common local words,
- how to mark noise, laughter, or silence.

Example tags:

```text
[noise]
[laughter]
[unclear]
[silence]
```

**Done when:** `docs/transcription_guidelines.md` exists.

## 1.3 Prepare sample data

**Status: Complete (June 25, 2026).** `PLD/PAM/0400` provides 397 Kapampangan
WAV clips with 397 matching transcript rows from one PLD recording session.
The Phase 2 importer uses this session as the integration dataset.

For the MVP, prepare at least:

- 30–100 short clips for demo quality, or
- 100–300 clips if time allows,
- 3–10 speakers if possible,
- clips around 5–15 seconds each,
- matching transcripts.

**Done when:** Sample audio and transcripts are ready for ingestion.

---

# Phase 2 — Audio Ingestion Pipeline

## 2.1 Build audio upload/import function

**Status: Complete (June 25, 2026).** The `bosesph import-pld` command imports
one PLD session directory, parses session metadata and transcript rows, matches
WAV files, and writes `metadata.csv` plus `ingestion_report.json`.

The current MVP implements the local-folder path for PLD PCM WAV sessions.
Generic CSV manifests, compressed formats, and web uploads remain later
extensions rather than Phase 2 requirements for the selected Option A scope.

Input options:

- upload audio through web UI,
- import from local folder,
- import from CSV manifest.

Accepted formats:

```text
.wav, .mp3, .m4a, .flac
```

**Done when:** The system can read multiple raw audio files and list them in a queue.

## 2.2 Validate uploaded audio

**Status: Complete (June 25, 2026).** Ingestion checks PCM WAV structure,
duration, sample rate, channels, sample width, empty audio, corruption, silence,
quiet audio, missing WAV files, and missing transcripts. Clip-level failures
are reported without aborting the batch.

Check:

- file format,
- file duration,
- sample rate,
- corrupt files,
- empty audio,
- extremely noisy or silent clips,
- missing transcript.

Possible validation statuses:

```text
pending
valid
needs_review
rejected
```

**Done when:** Each uploaded clip gets a validation status.

## 2.3 Convert audio to standard format

**Status: Complete (June 25, 2026).** Readable clips are copied or converted to
mono, 16 kHz, signed 16-bit PCM WAV while source files remain unchanged.

Recommended standard:

```text
WAV, mono, 16kHz
```

Output folder:

```text
outputs/dataset/audio_clean/
```

**Done when:** Raw audio files are converted to clean standardized audio files.

## 2.4 Rename files consistently

**Status: Complete (June 25, 2026).** Entries are sorted by source filename and
renamed deterministically using the Kapampangan ISO 639-3 prefix:
`pam_000001.wav`, `pam_000002.wav`, and so on.

Example filename format:

```text
kap_000001.wav
kap_000002.wav
kap_000003.wav
```

**Done when:** All accepted clips have clean and consistent file names.

---

# Phase 3 — Transcription and Validation

## 3.1 Create transcript input format

**Status: Complete (June 25, 2026).** For the selected PLD-first MVP scope,
Phase 3 consumes the validated `metadata.csv` produced by `bosesph import-pld`.
This preserves one metadata contract across ingestion, normalization, review,
and the future dataset builder. Generic transcript CSV manifests remain a later
extension.

Support transcript upload through CSV:

```csv
file_name,transcript,language,speaker_id
kap_raw_01.wav,Masanting ya ing aldo,Kapampangan,spk_001
```

**Done when:** The pipeline can match audio files with their transcripts.

## 3.2 Build transcript normalizer

**Status: Complete (June 25, 2026).** `bosesph normalize-transcripts DATASET`
normalizes Unicode, whitespace, punctuation spacing, repeated punctuation,
supported tag casing, sentence initials, and control characters without
respelling or translating spoken content. It atomically updates `metadata.csv`
and writes `normalization_report.json`; ambiguous symbols are retained and
routed to `needs_review`.

Normalize:

- extra spaces,
- inconsistent punctuation,
- casing,
- unsupported symbols,
- repeated punctuation,
- empty transcripts.

**Done when:** Transcript cleaning script outputs normalized text.

## 3.3 Add reviewer validation

**Status: Complete (June 25, 2026).** `bosesph review DATASET` provides a
resumable terminal review flow for `pending` and `needs_review` rows. Reviewers
see the audio path, transcript, language, speaker metadata, duration, notes, and
required checklist. Decisions are checkpointed immediately. The existing
`needs_review` status represents the task list's `needs_fix` decision.

For each clip, reviewers should check:

- Is the audio understandable?
- Does the transcript match the speech?
- Is the language label correct?
- Is the speaker metadata complete?

Review statuses:

```text
approved
needs_fix
rejected
```

**Done when:** Only approved clips enter the final dataset.

---

# Phase 4 — Dataset Builder

## 4.1 Generate final dataset folder

Output structure:

```text
outputs/dataset/
  audio/
    kap_000001.wav
    kap_000002.wav
  metadata.csv
  train.csv
  validation.csv
  test.csv
  dataset_card.md
```

**Done when:** The pipeline exports a clean dataset package.

## 4.2 Split dataset into train/validation/test

Recommended split:

```text
70% train
15% validation
15% test
```

Important rule:

> Avoid placing the same speaker in both train and test if possible. This makes evaluation more realistic.

**Done when:** Split files are generated correctly.

## 4.3 Generate dataset statistics

Show:

- total clips,
- total hours/minutes,
- number of speakers,
- average clip length,
- language distribution,
- split distribution,
- rejected/approved counts.

**Done when:** Dataset summary appears in JSON and in the dashboard.

---

# Phase 5 — Baseline ASR and Benchmark

## 5.1 Run baseline ASR model

Use a pretrained ASR model such as Whisper or another multilingual ASR model.

Input:

```text
outputs/dataset/test.csv
```

Output:

```text
outputs/benchmark/baseline_predictions.csv
```

**Done when:** The system generates predicted transcripts for the test set.

## 5.2 Calculate WER and CER

Metrics:

- WER = Word Error Rate
- CER = Character Error Rate

Output:

```json
{
  "model": "baseline",
  "language": "Kapampangan",
  "wer": 0.48,
  "cer": 0.22
}
```

**Done when:** The system outputs WER and CER for the baseline model.

## 5.3 Create benchmark report

Report should include:

- model name,
- dataset version,
- number of test clips,
- WER,
- CER,
- common error examples,
- notes about limitations.

**Done when:** `outputs/benchmark/report.md` is generated.

---

# Phase 6 — Fine-Tuning ASR Model

## 6.1 Prepare training data

Convert dataset into the format expected by the training library.

Required fields:

```text
audio
transcript
language
```

**Done when:** Train and validation data can be loaded by the training script.

## 6.2 Choose base ASR model

Recommended for MVP:

```text
Whisper tiny or Whisper small
```

Use a smaller model first to make training faster.

**Done when:** The team has selected one base model for fine-tuning.

## 6.3 Run fine-tuning

Training script should accept:

```bash
python ml/training/train_asr.py \
  --train_csv outputs/dataset/train.csv \
  --val_csv outputs/dataset/validation.csv \
  --base_model openai/whisper-small \
  --language kapampangan \
  --output_dir outputs/model/bosesph-kapampangan-v1
```

**Done when:** A fine-tuned model checkpoint is saved.

## 6.4 Evaluate fine-tuned model

Compare:

| Model | WER | CER |
|---|---:|---:|
| Baseline ASR | TBD | TBD |
| Fine-tuned ASR | TBD | TBD |

**Done when:** The report shows whether fine-tuning improved results.

## 6.5 Export model package

Output:

```text
outputs/model/bosesph-kapampangan-v1/
  config.json
  model files
  tokenizer/processor files
  model_card.md
```

**Done when:** The model can be loaded again for inference.

---

# Phase 7 — API Layer

## 7.1 Build backend API

Recommended endpoints:

```text
POST /upload-audio
POST /upload-transcripts
POST /validate-dataset
POST /build-dataset
POST /transcribe
POST /evaluate
POST /train
GET  /project-status
GET  /download-output
```

**Done when:** Frontend or notebooks can call the backend.

## 7.2 Add background jobs for heavy tasks

Heavy tasks:

- audio conversion,
- baseline inference,
- fine-tuning,
- evaluation,
- export packaging.

**Done when:** Long-running tasks do not freeze the API.

---

# Phase 8 — Demo UI / Visualization

## 8.1 Create dashboard pages

Suggested pages:

```text
Dashboard
Collect
Annotate
Dataset
Train
Evaluate
Demo
Docs
```

**Done when:** Users can visually follow the pipeline.

## 8.2 Build the demo flow

Minimum demo flow:

1. Upload sample audio.
2. Select language.
3. Click transcribe.
4. Show waveform preview.
5. Show predicted transcript.
6. Show model used.
7. Show WER/CER if reference transcript exists.

**Done when:** Judges can see the product working in under 2 minutes.

## 8.3 Show pipeline status cards

Cards to show:

```text
Dataset Clips
Approved Clips
Speakers
Total Minutes
Baseline WER
Fine-tuned WER
Model Version
```

**Done when:** Dashboard clearly communicates technical progress.

---

# Phase 9 — Open-Source Output Package

## 9.1 Generate dataset card

`dataset_card.md` should include:

- language,
- data source,
- number of clips,
- number of speakers,
- total duration,
- collection method,
- consent/license notes,
- limitations,
- intended use.

**Done when:** Dataset package is understandable by another developer.

## 9.2 Generate model card

`model_card.md` should include:

- base model,
- fine-tuning dataset,
- training settings,
- evaluation scores,
- limitations,
- ethical considerations,
- usage example.

**Done when:** Model package is understandable by another developer.

## 9.3 Create contribution guide

Explain how others can add a new language.

Example:

```text
1. Create a new language folder.
2. Add raw audio.
3. Add metadata.csv.
4. Run validation.
5. Build dataset.
6. Run evaluation.
7. Submit pull request.
```

**Done when:** Another team can reuse the pipeline.

---

# Phase 10 — Final Hackathon Presentation

## 10.1 Prepare a live demo script

Suggested demo order:

1. Show problem: Philippine languages lack open speech resources.
2. Show raw messy audio/transcripts.
3. Run cleaning/validation.
4. Show generated dataset package.
5. Run baseline transcription.
6. Show WER/CER.
7. Show fine-tuned model comparison.
8. Show final open-source package.
9. Explain how other developers can reuse it.

**Done when:** Demo can be completed smoothly within the time limit.

## 10.2 Prepare judging-criteria talking points

### Innovation & Creativity

- We built a reusable pipeline, not just a single app.
- It supports future Philippine languages.
- It turns community speech data into AI-ready resources.

### Technical Execution

- Working audio ingestion.
- Dataset validation.
- Train/validation/test split.
- Baseline ASR.
- WER/CER evaluation.
- Fine-tuning flow.

### Design & UX

- Clear dashboard.
- Simple upload-to-output flow.
- Easy-to-understand visual pipeline.

### Theme Relevance & Impact

- Supports underrepresented Philippine languages.
- Helps developers build inclusive voice tools.
- Produces open resources for research and community use.

**Done when:** Pitch directly matches all judging criteria.

---

# Suggested Sprint Schedule

## Day 1 — Planning and Data Design

- Finalize pitch.
- Choose pilot language.
- Create repo.
- Define metadata schema.
- Write transcription guidelines.

## Day 2 — Ingestion and Cleaning

- Build audio import.
- Add format validation.
- Convert audio to WAV mono 16kHz.
- Normalize filenames and transcripts.

## Day 3 — Dataset Builder

- Generate metadata.csv.
- Create train/validation/test split.
- Generate dataset statistics.
- Export dataset package.

## Day 4 — Baseline and Evaluation

- Run baseline ASR model.
- Generate predictions.
- Calculate WER/CER.
- Create benchmark report.

## Day 5 — Fine-Tuning

- Prepare training script.
- Fine-tune small ASR model.
- Save model checkpoint.
- Evaluate fine-tuned model.

## Day 6 — Demo and Dashboard

- Build simple UI.
- Add upload/transcribe demo.
- Add status cards.
- Add export/download buttons.

## Day 7 — Polish and Pitch

- Improve README.
- Generate dataset card/model card.
- Prepare demo script.
- Prepare final slide explanations.
- Test full workflow.

---

# Final Acceptance Checklist

## Product Checklist

- [ ] Raw audio can be uploaded or imported.
- [ ] Transcripts can be attached to audio files.
- [ ] Audio is validated.
- [ ] Audio is converted to standard format.
- [ ] Transcripts are normalized.
- [ ] Approved clips are exported into a clean dataset.
- [ ] Train/validation/test splits are generated.
- [ ] Baseline ASR predictions are produced.
- [ ] WER and CER are calculated.
- [ ] Fine-tuning script exists.
- [ ] Fine-tuned model output is saved.
- [ ] Baseline vs fine-tuned comparison is shown.
- [ ] Demo UI or notebook works.
- [ ] Dataset card is generated.
- [ ] Model card is generated.
- [ ] README explains how to reuse the pipeline.

## Presentation Checklist

- [ ] Problem is clear.
- [ ] Proposed solution is clear.
- [ ] Demo works without confusion.
- [ ] Technical metrics are shown.
- [ ] Reusability is emphasized.
- [ ] Impact on Philippine languages is emphasized.
- [ ] All judging criteria are addressed.

---

# Definition of Done

The project is ready when a developer can clone the repository, run the sample workflow, and receive the following output package:

```text
outputs/
  dataset/
    audio/
    metadata.csv
    train.csv
    validation.csv
    test.csv
    dataset_card.md
  benchmark/
    baseline_predictions.csv
    fine_tuned_predictions.csv
    results.json
    report.md
  model/
    bosesph-kapampangan-v1/
      model files
      model_card.md
  demo/
    sample_audio.wav
    sample_transcription.json
```

Final project message:

> BosesPH Toolkit helps developers transform raw Philippine-language speech recordings into clean datasets, benchmarks, and fine-tuned ASR models, making voice AI more inclusive for Filipino language communities.
