#!/bin/bash
set -e

echo "Transcribing baseline whisper-small..."
.venv/bin/bosesph transcribe outputs/dataset_15spk --model openai/whisper-small --language tagalog --split test --output outputs/benchmark/baseline_small_tagalog_predictions.csv

echo "Evaluating baseline whisper-small..."
.venv/bin/bosesph evaluate --predictions outputs/benchmark/baseline_small_tagalog_predictions.csv --output outputs/benchmark/baseline_small_tagalog --model-name "Baseline Whisper Small" --language kapampangan

echo "Transcribing Colab finetuned model..."
.venv/bin/bosesph transcribe outputs/dataset_15spk --model outputs/model/colab_finetuned_model/model --language tagalog --split test --output outputs/benchmark/colab_small_tagalog_predictions.csv

echo "Evaluating Colab finetuned model..."
.venv/bin/bosesph evaluate --predictions outputs/benchmark/colab_small_tagalog_predictions.csv --output outputs/benchmark/colab_small_tagalog --model-name "Colab Finetuned Model" --language kapampangan

echo "Comparing..."
.venv/bin/bosesph compare --baseline outputs/benchmark/baseline_small_tagalog/results.json --finetuned outputs/benchmark/colab_small_tagalog/results.json --output outputs/benchmark/comparison_small_colab.md

echo "Done!"
