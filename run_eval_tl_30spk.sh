#!/bin/bash
set -e

echo "Transcribing baseline whisper-small..."
.venv/bin/bosesph transcribe outputs/dataset_15spk --model openai/whisper-small --language tl --split test --output outputs/benchmark/baseline_small_tl_predictions.csv --limit 300

echo "Evaluating baseline whisper-small..."
.venv/bin/bosesph evaluate --predictions outputs/benchmark/baseline_small_tl_predictions.csv --output outputs/benchmark/baseline_small_tl --model-name "Baseline Whisper Small" --language kapampangan

echo "Transcribing Colab finetuned model 30spk (tl)..."
.venv/bin/bosesph transcribe outputs/dataset_15spk --model outputs/model/colab_finetuned_model_tl_30speakers/model --language tl --split test --output outputs/benchmark/colab_small_tl_30spk_predictions.csv --limit 300

echo "Evaluating Colab finetuned model 30spk (tl)..."
.venv/bin/bosesph evaluate --predictions outputs/benchmark/colab_small_tl_30spk_predictions.csv --output outputs/benchmark/colab_small_tl_30spk --model-name "Colab Finetuned Model 30spk (tl)" --language kapampangan

echo "Comparing..."
.venv/bin/bosesph compare --baseline outputs/benchmark/baseline_small_tl/results.json --finetuned outputs/benchmark/colab_small_tl_30spk/results.json --output outputs/benchmark/comparison_small_colab_tl_30spk.md

echo "Done!"
