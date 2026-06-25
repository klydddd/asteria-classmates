# Requirements.md — BosesPH Toolkit Technical Requirements

## 1. Product Summary

**BosesPH Toolkit** is an open-source, **CLI-first developer pipeline** for creating Philippine-language speech resources.

The system accepts raw audio, transcripts, and metadata, then outputs:

- cleaned speech dataset,
- metadata files,
- train/validation/test splits,
- benchmark files,
- WER/CER evaluation results,
- optional fine-tuned ASR model,
- reusable documentation,
- optional demo interface.

The main product should be usable from the **terminal/command line** so developers and researchers can run the full workflow reproducibly.

The first MVP should focus on one target language, preferably **Kapampangan**, while keeping the architecture reusable for other Philippine languages such as Ilocano, Waray, Hiligaynon, Cebuano, Pangasinan, Bikol, and others.

Core product idea:

```text
Raw audio + transcripts
        ↓
BosesPH CLI pipeline
        ↓
Clean dataset + benchmark + optional fine-tuned ASR model
```

Final success statement:

> BosesPH Toolkit gives developers a repeatable way to transform raw Philippine-language speech into clean datasets, benchmarks, and fine-tuned ASR models through simple terminal commands.

---

## 2. Product Interface Strategy

## 2.1 Primary Interface: CLI / Terminal

The main interface should be a command-line tool named `bosesph`.

Example command flow:

```bash
bosesph init kapampangan-asr
bosesph validate data/raw --transcripts data/transcripts.csv
bosesph clean data/raw --language kapampangan
bosesph split outputs/dataset --train 0.7 --val 0.15 --test 0.15
bosesph transcribe sample.wav --model openai/whisper-small
bosesph evaluate --predictions outputs/benchmark/predictions.csv --references outputs/dataset/test.csv
bosesph train --base-model openai/whisper-small --dataset outputs/dataset
bosesph package --output release
```

### Why CLI-first?

A CLI is recommended because the target users are developers, researchers, and language-data contributors who need reproducible workflows.

Benefits:

- easier to run on local machines,
- easier to run on Google Colab or cloud GPUs,
- easier to automate in scripts,
- easier to document in GitHub,
- easier to reproduce during judging,
- more aligned with open-source developer tooling.

The web dashboard is optional. The CLI is the core product.

---

## 2.2 Optional Interfaces

The CLI should work even without any web app.

Optional interfaces can be added only after the CLI pipeline works.

| Interface | Priority | Purpose |
|---|---:|---|
| CLI / Terminal | Required | Main developer workflow |
| Jupyter Notebook | Recommended | Technical demo and backup walkthrough |
| Gradio | Optional | Quick interactive model demo |
| Streamlit | Optional | Simple dashboard demo |
| Next.js Web App | Optional / Stretch Goal | Polished user-facing dashboard |
| FastAPI Backend | Optional / Stretch Goal | API layer for web or remote execution |

Recommended MVP:

```text
Python package + Typer CLI + Jupyter/Gradio demo + clean GitHub README
```

Avoid spending too much time on a full web app unless the CLI pipeline is already working.

---

## 3. Recommended Tech Stack

## 3.1 CLI and Core Pipeline Stack

| Requirement | Recommendation |
|---|---|
| Main Language | Python 3.10+ |
| CLI Framework | Typer |
| Terminal UI | Rich |
| Config Files | YAML / JSON |
| Data Handling | pandas, numpy |
| Audio Processing | ffmpeg, soundfile, librosa, torchaudio, pydub |
| ML Framework | PyTorch |
| ASR Models | Whisper, Wav2Vec2/XLS-R, or MMS-style multilingual ASR models |
| Model Library | Hugging Face Transformers |
| Dataset Handling | Hugging Face Datasets or pandas |
| Evaluation | jiwer for WER/CER |
| Packaging | pyproject.toml |
| Testing | pytest |

### CLI Responsibilities

The CLI should allow developers to:

- initialize a new speech dataset project,
- validate raw audio and transcript files,
- clean and standardize audio files,
- normalize transcripts,
- build train/validation/test splits,
- run baseline ASR transcription,
- calculate WER and CER,
- fine-tune an ASR model,
- export output packages,
- generate dataset cards and model cards.

---

## 3.2 Optional Backend API Stack

Only build this if there is enough time.

| Requirement | Recommendation |
|---|---|
| Language | Python 3.10+ |
| Framework | FastAPI |
| Server | Uvicorn |
| Validation | Pydantic |
| File Handling | pathlib, shutil, tempfile |
| Background Jobs | FastAPI BackgroundTasks for MVP; Celery/RQ later |
| Local Database | SQLite for MVP |
| Production Database | PostgreSQL or Supabase |
| Storage | Local filesystem for MVP; Supabase Storage or S3 later |

### Backend Responsibilities

The backend should only wrap the existing CLI/core pipeline logic.

It may:

- receive uploaded audio and transcript files,
- validate audio format and metadata,
- trigger the cleaning pipeline,
- trigger ASR inference,
- trigger WER/CER evaluation,
- trigger fine-tuning jobs,
- export dataset/model packages.

Important rule:

> Do not duplicate logic between CLI and API. The API should call the same Python services used by the CLI.

---

## 3.3 Optional Frontend Stack

Only build this as a stretch goal.

| Requirement | Recommendation |
|---|---|
| Language | TypeScript |
| Framework | Next.js with App Router |
| Styling | Tailwind CSS |
| UI Components | shadcn/ui or custom components |
| Charts | Recharts or Chart.js |
| Audio Visualization | wavesurfer.js |
| API Calls | Fetch API or Axios |
| Package Manager | pnpm or npm |

### Frontend Responsibilities

The frontend may:

- upload audio files,
- upload transcript CSV files,
- display waveform previews,
- show validation status,
- show dataset statistics,
- trigger CLI-backed actions through an API,
- display transcription output,
- display WER/CER results,
- provide download links for output packages.

---

## 3.4 Machine Learning Stack

| Requirement | Recommendation |
|---|---|
| ML Language | Python |
| Deep Learning | PyTorch |
| ASR Models | Whisper, Wav2Vec2/XLS-R, or MMS-style multilingual ASR models |
| Model Library | Hugging Face Transformers |
| Dataset Handling | Hugging Face Datasets or pandas |
| Training Utility | Hugging Face Trainer or custom PyTorch loop |
| Training Acceleration | Accelerate |
| Audio Loading | torchaudio, librosa, or soundfile |
| Evaluation | jiwer for WER/CER |
| Experiment Tracking | Weights & Biases, MLflow, or simple JSON logs |

### Recommended MVP Model

Use a small ASR model first to reduce training time.

Suggested MVP path:

```text
Baseline: pretrained Whisper tiny/small
Fine-tuned: Whisper tiny/small on cleaned Kapampangan dataset
Metrics: WER and CER
```

If fine-tuning takes too long, the team can still show:

- cleaned dataset,
- train/validation/test split,
- baseline ASR output,
- evaluation script,
- precomputed or notebook-based fine-tuning prototype.

---

## 4. Core Dependencies

## 4.1 CLI Dependencies

Recommended `pyproject.toml` or `requirements.txt` dependencies:

```text
typer
rich
pydantic
pydantic-settings
pyyaml
python-dotenv
loguru
pandas
numpy
tqdm
```

Purpose:

| Package | Purpose |
|---|---|
| typer | Build the CLI commands |
| rich | Pretty terminal output, tables, progress bars |
| pydantic | Validate configs and data schemas |
| pydantic-settings | Manage environment/config settings |
| pyyaml | Read YAML config files |
| python-dotenv | Load environment variables |
| loguru | Cleaner logging |
| pandas | Process metadata CSV files |
| numpy | Numeric/audio utilities |
| tqdm | Progress bars |

---

## 4.2 Audio Processing Dependencies

```text
ffmpeg
ffmpeg-python
librosa
soundfile
torchaudio
pydub
webrtcvad
```

Purpose:

| Tool/Package | Purpose |
|---|---|
| ffmpeg | Audio conversion |
| ffmpeg-python | Python wrapper for FFmpeg |
| librosa | Audio analysis/loading |
| soundfile | Read/write WAV files |
| torchaudio | Audio processing for PyTorch |
| pydub | Simple audio manipulation |
| webrtcvad | Optional voice activity detection |

---

## 4.3 ML and ASR Dependencies

```text
torch
transformers
datasets
accelerate
evaluate
jiwer
sentencepiece
protobuf
safetensors
```

Purpose:

| Package | Purpose |
|---|---|
| torch | Deep learning backend |
| transformers | Load/fine-tune ASR models |
| datasets | Manage train/validation/test datasets |
| accelerate | Easier CPU/GPU training setup |
| evaluate | Evaluation utilities |
| jiwer | WER/CER calculation |
| sentencepiece | Tokenizer support for some models |
| protobuf | Model/tokenizer compatibility |
| safetensors | Safe model weight format |

---

## 4.4 Optional Backend Dependencies

```text
fastapi
uvicorn
python-multipart
sqlmodel
```

Purpose:

| Package | Purpose |
|---|---|
| fastapi | Build API endpoints |
| uvicorn | Run API server |
| python-multipart | Handle file uploads |
| sqlmodel | Lightweight database models |

---

## 4.5 Optional Frontend Dependencies

Recommended Next.js packages:

```text
next
react
react-dom
typescript
tailwindcss
lucide-react
recharts
wavesurfer.js
axios
zod
```

Purpose:

| Package | Purpose |
|---|---|
| next | Web framework |
| react | UI library |
| typescript | Type safety |
| tailwindcss | Styling |
| lucide-react | Icons |
| recharts | Charts and metrics |
| wavesurfer.js | Audio waveform visualization |
| axios | API requests |
| zod | Frontend validation |

---

## 5. System Architecture

Recommended CLI-first architecture:

```text
Developer / Researcher
        ↓
Terminal / CLI command: bosesph
        ↓
Core Python Pipeline Services
  - Project initializer
  - Audio validator
  - Audio cleaner
  - Transcript normalizer
  - Dataset builder
  - ASR inference runner
  - WER/CER evaluator
  - Fine-tuning runner
  - Package exporter
        ↓
Output Package
  - Clean dataset
  - Benchmark report
  - Fine-tuned model
  - Documentation
```

Optional extended architecture:

```text
CLI Core Package
   ↓              ↓
FastAPI API       Jupyter/Gradio Demo
   ↓
Next.js Dashboard
```

Important architecture rule:

> The CLI and optional web/API layers must all use the same core Python services.

---

## 6. Required CLI Commands

## 6.1 `bosesph init`

Purpose:

Create a new project folder with the expected structure.

Example:

```bash
bosesph init kapampangan-asr
```

Expected output:

```text
kapampangan-asr/
  data/
    raw/
    cleaned/
    processed/
  outputs/
    dataset/
    benchmark/
    model/
    logs/
  configs/
    project.yaml
  docs/
```

---

## 6.2 `bosesph validate`

Purpose:

Check if audio, transcript, and metadata files are valid.

Example:

```bash
bosesph validate data/raw --transcripts data/transcripts.csv
```

Should check:

- missing audio files,
- missing transcripts,
- unsupported audio formats,
- broken audio files,
- empty transcripts,
- invalid language labels,
- duplicate audio IDs,
- too-short or too-long clips.

Example output:

```text
Validation Summary
✅ 120 audio files found
✅ 118 transcripts matched
⚠️ 2 files missing transcripts
⚠️ 5 clips longer than 30 seconds
```

---

## 6.3 `bosesph clean`

Purpose:

Convert and clean raw audio files.

Example:

```bash
bosesph clean data/raw --language kapampangan --output outputs/dataset
```

Should perform:

- convert audio to WAV,
- convert to mono,
- resample to 16kHz,
- rename files consistently,
- trim or flag long silence,
- normalize transcript text,
- generate `metadata.csv`.

---

## 6.4 `bosesph split`

Purpose:

Create train/validation/test splits.

Example:

```bash
bosesph split outputs/dataset --train 0.7 --val 0.15 --test 0.15
```

Expected output:

```text
outputs/dataset/train.csv
outputs/dataset/validation.csv
outputs/dataset/test.csv
```

---

## 6.5 `bosesph transcribe`

Purpose:

Run ASR inference on an audio file.

Example:

```bash
bosesph transcribe sample.wav --model openai/whisper-small --language kapampangan
```

Example output:

```text
Language: Kapampangan
Model: openai/whisper-small
Transcript: "Masanting ya ing aldo"
```

---

## 6.6 `bosesph evaluate`

Purpose:

Calculate WER and CER using reference transcripts and model predictions.

Example:

```bash
bosesph evaluate --references outputs/dataset/test.csv --predictions outputs/benchmark/predictions.csv
```

Expected output:

```text
Evaluation Results
WER: 48.2%
CER: 22.5%
Saved report: outputs/benchmark/report.md
```

---

## 6.7 `bosesph train`

Purpose:

Fine-tune an ASR model on the cleaned dataset.

Example:

```bash
bosesph train --base-model openai/whisper-small --dataset outputs/dataset --output outputs/model/bosesph-kapampangan-v1
```

Should support:

- loading train/validation split,
- loading base ASR model,
- extracting audio features,
- preparing transcript labels,
- training/fine-tuning,
- saving checkpoints,
- evaluating on test set,
- exporting final model.

---

## 6.8 `bosesph package`

Purpose:

Export the final output package.

Example:

```bash
bosesph package --dataset outputs/dataset --benchmark outputs/benchmark --model outputs/model/bosesph-kapampangan-v1 --output release
```

Expected output:

```text
release/
  dataset/
  benchmark/
  model/
  docs/
  README.md
  dataset_card.md
  model_card.md
```

---

## 7. Recommended Repository Structure

CLI-first repository structure:

```text
bosesph-toolkit/
  README.md
  LICENSE
  pyproject.toml
  requirements.txt
  .env.example
  .gitignore

  bosesph/
    __init__.py
    cli.py

    commands/
      init.py
      validate.py
      clean.py
      split.py
      transcribe.py
      evaluate.py
      train.py
      package.py

    services/
      project_initializer.py
      audio_validator.py
      audio_cleaner.py
      transcript_normalizer.py
      dataset_builder.py
      asr_inference.py
      evaluator.py
      trainer.py
      package_exporter.py

    schemas/
      config.py
      metadata.py
      results.py

    utils/
      audio.py
      text.py
      files.py
      logging.py

  configs/
    default.yaml
    whisper_tiny.yaml
    whisper_small.yaml

  ml/
    training/
      train_asr.py
    evaluation/
      evaluate_asr.py
      compute_metrics.py
    notebooks/
      demo_workflow.ipynb

  docs/
    transcription_guidelines.md
    dataset_format.md
    cli_guide.md
    training_guide.md
    evaluation_guide.md
    contribution_guide.md

  sample_data/
    raw_audio/
    transcripts.csv
    metadata_sample.csv

  outputs/
    dataset/
    benchmark/
    model/
    logs/

  tests/
    test_audio_validator.py
    test_transcript_normalizer.py
    test_dataset_builder.py
    test_evaluator.py
```

Optional web/API structure if time allows:

```text
apps/
  api/
    main.py
    routes/
  web/
    app/
    components/
```

---

## 8. Data Requirements

## 8.1 Audio Requirements

Accepted input formats:

```text
.wav
.mp3
.m4a
.flac
```

Standardized output format:

```text
WAV, mono, 16kHz
```

Recommended clip length:

```text
5 to 15 seconds per clip
```

Minimum MVP data target:

```text
30 to 100 clips
3 to 10 speakers
```

Better target if time allows:

```text
100 to 300 clips
10+ speakers
```

---

## 8.2 Metadata Requirements

Required fields:

```csv
audio_id,file_path,transcript,language,speaker_id,duration_seconds,split,quality_status
```

Optional fields:

```csv
region,speaker_age_group,speaker_gender,recording_device,environment,reviewer_notes
```

Example:

```csv
audio_id,file_path,transcript,language,region,speaker_id,duration_seconds,split,quality_status
kap_000001,audio/kap_000001.wav,Masanting ya ing aldo,Kapampangan,Pampanga,spk_001,8.4,train,approved
```

---

## 8.3 Transcript Requirements

Transcripts should be:

- manually checked,
- consistently spelled,
- language-tagged,
- free from unnecessary symbols,
- aligned with the audio,
- marked if unclear.

Recommended unclear speech tag:

```text
[unclear]
```

Recommended noise tag:

```text
[noise]
```

---

## 9. Pipeline Requirements

## 9.1 Audio Cleaning Pipeline

Input:

```text
raw audio files
```

Steps:

1. Check file validity.
2. Convert to WAV.
3. Convert to mono.
4. Resample to 16kHz.
5. Trim or flag long silence.
6. Calculate duration.
7. Save to clean audio folder.

Output:

```text
outputs/dataset/audio/
```

---

## 9.2 Transcript Pipeline

Input:

```text
transcripts.csv
```

Steps:

1. Match transcript to audio file.
2. Remove extra spaces.
3. Normalize punctuation.
4. Validate empty or suspicious transcripts.
5. Save normalized transcript.

Output:

```text
outputs/dataset/metadata.csv
```

---

## 9.3 Dataset Split Pipeline

Input:

```text
approved metadata.csv
```

Steps:

1. Filter approved clips.
2. Group by speaker if possible.
3. Split into train/validation/test.
4. Save CSV split files.

Output:

```text
train.csv
validation.csv
test.csv
```

---

## 9.4 Baseline ASR Pipeline

Input:

```text
test.csv
base ASR model
```

Steps:

1. Load test audio files.
2. Run baseline model transcription.
3. Save predicted transcripts.
4. Prepare predictions for evaluation.

Output:

```text
outputs/benchmark/baseline_predictions.csv
```

---

## 9.5 Evaluation Pipeline

Input:

```text
test.csv
model predictions
```

Steps:

1. Load reference transcript.
2. Load predicted transcript.
3. Normalize text for fair scoring.
4. Calculate WER.
5. Calculate CER.
6. Save report.

Output:

```text
results.json
report.md
```

---

## 9.6 Fine-Tuning Pipeline

Input:

```text
train.csv
validation.csv
base ASR model
```

Steps:

1. Load dataset.
2. Load processor/tokenizer.
3. Prepare audio features.
4. Prepare labels.
5. Train model.
6. Save checkpoints.
7. Evaluate on test set.
8. Export final model.

Output:

```text
outputs/model/bosesph-language-v1/
```

---

## 10. CLI UX Requirements

The CLI should be clean and understandable during a live demo.

Requirements:

- Use clear command names.
- Show helpful `--help` output for every command.
- Show progress bars for long-running tasks.
- Show warnings without crashing when possible.
- Save logs to `outputs/logs/`.
- Use readable error messages.
- Use tables for validation and evaluation summaries.
- Print the location of generated output files.

Example terminal output style:

```text
BosesPH Toolkit — Dataset Validation

┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Check                ┃ Status ┃
┣━━━━━━━━━━━━━━━━━━━━━━╋━━━━━━━━┫
┃ Audio files found    ┃ 120    ┃
┃ Transcripts matched  ┃ 118    ┃
┃ Missing transcripts  ┃ 2      ┃
┃ Invalid audio files  ┃ 0      ┃
┗━━━━━━━━━━━━━━━━━━━━━━┻━━━━━━━━┛

Saved validation report: outputs/logs/validation_report.json
```

---

## 11. Optional API Requirements

Only required if building a web dashboard or remote demo.

## 11.1 Optional Endpoints

```text
POST /audio/upload
POST /transcripts/upload
POST /dataset/validate
POST /dataset/build
GET  /dataset/stats
POST /asr/transcribe
POST /evaluation/run
POST /training/start
GET  /training/status/{job_id}
GET  /outputs/download/{package_id}
```

## 11.2 Example API Response

```json
{
  "language": "Kapampangan",
  "model": "bosesph-kapampangan-v1",
  "transcript": "Masanting ya ing aldo",
  "confidence": 0.87
}
```

---

## 12. Optional UI Requirements

A web UI is optional. It should not block the CLI MVP.

## 12.1 Optional Pages

```text
Dashboard
Collect Audio
Annotate / Validate
Dataset Builder
Train Model
Evaluate Model
Demo Transcription
Documentation
```

## 12.2 Dashboard Cards

Show:

```text
Total Clips
Approved Clips
Rejected Clips
Total Speakers
Total Minutes
Baseline WER
Fine-tuned WER
Model Version
```

## 12.3 Demo Page Requirements

The demo page should include:

- audio upload box,
- waveform preview,
- language dropdown,
- model dropdown,
- transcript output box,
- run transcription button,
- WER/CER display if reference text is provided.

---

## 13. Hardware Requirements

## 13.1 MVP Without Fine-Tuning

For dataset cleaning, baseline inference, and demo:

```text
Laptop or desktop
8GB RAM minimum
16GB RAM recommended
CPU is acceptable
```

## 13.2 With Fine-Tuning

For model fine-tuning:

```text
NVIDIA GPU recommended
8GB+ VRAM for small experiments
Google Colab, Kaggle, RunPod, or cloud GPU can be used
```

If GPU is limited, use:

```text
Whisper tiny
small dataset
few epochs
batch size 1 or 2
gradient accumulation
```

---

## 14. Environment Variables

Create `.env.example`:

```env
APP_ENV=development
DATA_DIR=./outputs/dataset
MODEL_DIR=./outputs/model
UPLOAD_DIR=./data/raw
LOG_DIR=./outputs/logs
DATABASE_URL=sqlite:///./bosesph.db
HUGGINGFACE_TOKEN=
WANDB_API_KEY=
```

If using optional API/web:

```env
API_BASE_URL=http://localhost:8000
```

---

## 15. Installation Requirements

## 15.1 CLI Setup

Recommended local setup:

```bash
git clone <repo-url>
cd bosesph-toolkit
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

For Windows PowerShell:

```powershell
git clone <repo-url>
cd bosesph-toolkit
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

Check installation:

```bash
bosesph --help
```

Expected output:

```text
Usage: bosesph [OPTIONS] COMMAND [ARGS]...

Commands:
  init
  validate
  clean
  split
  transcribe
  evaluate
  train
  package
```

---

## 15.2 Python Requirements Setup

Alternative setup:

```bash
pip install -r requirements.txt
python -m bosesph.cli --help
```

---

## 15.3 Optional Backend Setup

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

For Windows PowerShell:

```powershell
cd apps/api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## 15.4 Optional Frontend Setup

```bash
cd apps/web
pnpm install
pnpm dev
```

Alternative:

```bash
npm install
npm run dev
```

---

## 15.5 FFmpeg Requirement

FFmpeg must be installed on the system for audio conversion.

Check installation:

```bash
ffmpeg -version
```

---

## 16. Output Package Requirements

The final export should look like this:

```text
outputs/
  dataset/
    audio/
      kap_000001.wav
      kap_000002.wav
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
      config.json
      model files
      tokenizer files
      model_card.md

  demo/
    sample_audio.wav
    sample_transcription.json

  logs/
    validation_report.json
    cleaning_report.json
    training_log.json
```

Packaged release:

```text
release/
  dataset/
  benchmark/
  model/
  docs/
  README.md
  dataset_card.md
  model_card.md
```

---

## 17. Documentation Requirements

Required documentation files:

```text
README.md
docs/transcription_guidelines.md
docs/dataset_format.md
docs/cli_guide.md
docs/training_guide.md
docs/evaluation_guide.md
docs/contribution_guide.md
outputs/dataset/dataset_card.md
outputs/model/model_card.md
```

## 17.1 README Must Explain

- What the project is.
- Why Philippine speech resources matter.
- How to install the CLI.
- How to run the pipeline from terminal.
- How to add a new language.
- How to evaluate a model.
- How to fine-tune a model.
- How to use the output package.

---

## 17.2 CLI Guide Must Include

The CLI guide should include:

- command list,
- example workflow,
- expected inputs,
- expected outputs,
- troubleshooting section,
- sample terminal screenshots or copied outputs.

Example CLI guide flow:

```bash
bosesph init kapampangan-asr
cd kapampangan-asr
bosesph validate data/raw --transcripts data/transcripts.csv
bosesph clean data/raw --language kapampangan
bosesph split outputs/dataset
bosesph transcribe sample.wav --model openai/whisper-small
bosesph evaluate --references outputs/dataset/test.csv --predictions outputs/benchmark/predictions.csv
bosesph package --output release
```

---

## 18. Data Ethics and Consent Requirements

Because the project uses human voice recordings, the team must handle data responsibly.

Requirements:

- Get speaker consent before using recordings.
- Explain intended use clearly.
- Avoid collecting sensitive personal information.
- Allow speakers to request removal.
- Do not publish private or identifiable metadata.
- Use a clear license for the dataset.
- State limitations and possible bias.

Recommended public metadata should avoid exact personal details. Use broad fields only:

```text
speaker_id instead of real name
age_group instead of exact age
region instead of full address
```

---

## 19. Quality Requirements

## 19.1 Dataset Quality

- No missing audio files.
- No missing transcripts.
- No duplicate audio IDs.
- Audio duration is valid.
- Transcript is not empty.
- Language label is present.
- Split column is present.

## 19.2 Model Quality

- Baseline WER/CER is reported.
- Fine-tuned WER/CER is reported if training is completed.
- Test set is not used for training.
- Evaluation script is reproducible.

## 19.3 CLI UX Quality

- The full demo can be run through terminal commands.
- Every command has helpful `--help` text.
- Output messages are clear.
- Long tasks show progress bars.
- Errors explain what to fix.
- Results are saved to predictable folders.

## 19.4 Optional Web UX Quality

- The demo can be understood in under 2 minutes.
- Buttons and outputs are clearly labeled.
- Dashboard explains what stage the dataset is in.
- Error messages are understandable.

---

## 20. Minimum Viable Demo

A successful CLI MVP demo should show:

1. Initialize a project.
2. Validate sample audio and transcripts.
3. Clean the sample dataset.
4. Build train/validation/test splits.
5. Run baseline transcription.
6. Show WER/CER.
7. Optionally run fine-tuning.
8. Export output package.

Minimum acceptable terminal demo:

```bash
bosesph init demo-kapampangan
bosesph validate sample_data/raw_audio --transcripts sample_data/transcripts.csv
bosesph clean sample_data/raw_audio --language kapampangan
bosesph split outputs/dataset
bosesph transcribe sample_data/raw_audio/sample.wav --model openai/whisper-small
bosesph evaluate --references outputs/dataset/test.csv --predictions outputs/benchmark/baseline_predictions.csv
bosesph package --output release
```

Minimum acceptable outputs:

```text
metadata.csv
train.csv
validation.csv
test.csv
baseline_predictions.csv
results.json
README.md
```

Stronger outputs:

```text
fine-tuned model
model_card.md
dataset_card.md
interactive Gradio demo
before-vs-after WER/CER chart
```

---

## 21. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Not enough data | Use a small but clean MVP dataset and focus on reproducibility. |
| Fine-tuning takes too long | Use Whisper tiny, fewer epochs, or show training notebook/prototype. |
| Poor WER results | Emphasize benchmark creation and show improvement if any. |
| Transcript inconsistency | Create clear transcription rules and reviewer status. |
| CLI is hard for non-technical judges | Prepare a short terminal demo script and a visual flow diagram. |
| Demo failure | Prepare a backup notebook, precomputed outputs, and a recorded terminal demo. |
| Ethical concerns | Use consented sample data and anonymized speaker IDs. |

---

## 22. Hackathon Success Requirements

To be competitive, the team should demonstrate:

- a clear problem,
- a reusable CLI-first solution,
- working technical pipeline,
- clean terminal demo,
- measurable results,
- open-source outputs,
- direct impact on Philippine language inclusion.

Criteria mapping:

| Criteria | How BosesPH CLI satisfies it |
|---|---|
| Innovation & Creativity | Developer-first speech-resource factory for Philippine languages |
| Technical Execution | Working commands for cleaning, splitting, evaluating, and training |
| Design & UX | Clean terminal UX, progress bars, readable summaries, clear docs |
| Theme Relevance & Impact | Produces reusable speech datasets, benchmarks, and ASR models for underrepresented Philippine languages |

Final pitch:

> BosesPH Toolkit is a CLI-first open-source pipeline that helps developers turn raw Philippine-language voice recordings into clean datasets, benchmarks, and fine-tuned ASR models using reproducible terminal commands.
