#!/bin/bash
set -e

echo "Transcribing baseline whisper-small..."
.venv/bin/bosesph transcribe outputs/dataset_15spk --model openai/whisper-small --language tl --split test --output outputs/benchmark/baseline_small_tl_predictions.csv --limit 300

echo "Evaluating baseline whisper-small..."
.venv/bin/bosesph evaluate --predictions outputs/benchmark/baseline_small_tl_predictions.csv --output outputs/benchmark/baseline_small_tl --model-name "Baseline Whisper Small" --language kapampangan

echo "Transcribing Colab finetuned model (tl)..."
.venv/bin/bosesph transcribe outputs/dataset_15spk --model outputs/model/colab_finetuned_model_tl/model --language tl --split test --output outputs/benchmark/colab_small_tl_predictions.csv --limit 300

echo "Evaluating Colab finetuned model (tl)..."
.venv/bin/bosesph evaluate --predictions outputs/benchmark/colab_small_tl_predictions.csv --output outputs/benchmark/colab_small_tl --model-name "Colab Finetuned Model (tl)" --language kapampangan

echo "Comparing..."
.venv/bin/bosesph compare --baseline outputs/benchmark/baseline_small_tl/results.json --finetuned outputs/benchmark/colab_small_tl/results.json --output outputs/benchmark/comparison_small_colab_tl.md

echo "Done!"
