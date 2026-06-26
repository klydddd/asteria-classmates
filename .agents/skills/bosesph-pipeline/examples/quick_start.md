# BosesPH Quick-Start Example

This example demonstrates the full pipeline from a PLD session import to
a benchmarked model comparison.

## Prerequisites

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[asr,train,api,mcp,dev]"
```

## Full Pipeline Run

```bash
# 1. Import a PLD recording session
bosesph import-pld PLD/PAM/0400 --output outputs/dataset --overwrite

# 2. Normalize transcript formatting
bosesph normalize-transcripts outputs/dataset

# 3. Review clips (interactive — approve all for demo)
bosesph review outputs/dataset

# 4. Build the dataset with speaker-aware splits
bosesph build-dataset outputs/dataset --output outputs/dataset --overwrite

# 5. Verify dataset statistics
cat outputs/dataset/dataset_stats.json | python -m json.tool

# 6. Baseline transcription on the test split
bosesph transcribe outputs/dataset \
  --split test \
  --model openai/whisper-small \
  --output outputs/benchmark/baseline_predictions.csv

# 7. Evaluate baseline WER/CER
bosesph evaluate \
  --predictions outputs/benchmark/baseline_predictions.csv \
  --output outputs/benchmark/baseline \
  --model-name "whisper-small (baseline)" \
  --language kapampangan

# 8. Fine-tune a small model (quick demo with 50 steps)
bosesph finetune outputs/dataset \
  --output outputs/model/kapampangan-v1 \
  --base-model openai/whisper-tiny \
  --language tl \
  --max-steps 50

# 9. Transcribe test split with the fine-tuned model
bosesph transcribe outputs/dataset \
  --split test \
  --model outputs/model/kapampangan-v1/model \
  --output outputs/benchmark/finetuned_predictions.csv

# 10. Evaluate fine-tuned model
bosesph evaluate \
  --predictions outputs/benchmark/finetuned_predictions.csv \
  --output outputs/benchmark/finetuned \
  --model-name "kapampangan-v1 (fine-tuned)" \
  --language kapampangan

# 11. Compare baseline vs fine-tuned
bosesph compare \
  --baseline outputs/benchmark/baseline/results.json \
  --finetuned outputs/benchmark/finetuned/results.json \
  --output outputs/benchmark/comparison.md
```

## Expected Output

After running the full pipeline:

```
outputs/
  dataset/
    audio/                    # ~300+ standardized WAV files
    metadata.csv              # All clips with assigned splits
    train.csv                 # ~70% of approved clips
    validation.csv            # ~15% of approved clips
    test.csv                  # ~15% of approved clips
    dataset_stats.json        # Clip counts, durations, speakers
    dataset_card.md           # Auto-generated documentation
  benchmark/
    baseline_predictions.csv  # Baseline transcriptions
    baseline/
      results.json            # WER/CER scores
      report.md               # Detailed benchmark report
    finetuned_predictions.csv
    finetuned/
      results.json
      report.md
    comparison.md             # Side-by-side comparison
  model/
    kapampangan-v1/
      model/                  # Weights + processor
      model_card.md
      training_config.json
```

## Using with MCP

```bash
# Start the MCP server
bosesph-mcp

# Or test interactively with the MCP Inspector
mcp dev src/bosesph/mcp/server.py
```

## Using the API

```bash
# Start the FastAPI server
bosesph-api

# OpenAPI docs at http://localhost:8000/docs
```
