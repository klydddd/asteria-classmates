# BosesPH Toolkit - Simplified Task List

## Phase 0: Team Alignment and Setup
- [ ] Define the final pitch
- [ ] Choose the pilot language (e.g., Kapampangan)
- [ ] Create repository and basic folder structure

## Phase 1: Dataset Design
- [x] Define required metadata fields
- [x] Define transcript rules
- [x] Prepare sample data (30-100 clips)

## Phase 2: Audio Ingestion Pipeline
- [x] Build audio upload/import function
- [x] Validate uploaded audio (format, duration, sample rate, etc.)
- [x] Convert audio to standard format (WAV, mono, 16kHz)
- [x] Rename files consistently

## Phase 3: Transcription and Validation
- [x] Create transcript input format
- [x] Build transcript normalizer
- [x] Add reviewer validation flow

## Phase 4: Dataset Builder
- [x] Generate final dataset folder structure
- [x] Split dataset into train (70%), validation (15%), test (15%)
- [x] Generate dataset statistics

## Phase 5: Baseline ASR and Benchmark
- [x] Run baseline ASR model
- [x] Calculate WER and CER metrics
- [x] Create benchmark report

## Phase 6: Fine-Tuning ASR Model
- [ ] Prepare training data
- [ ] Choose base ASR model (Whisper tiny/small)
- [ ] Run fine-tuning script
- [ ] Evaluate fine-tuned model (compare with baseline)
- [ ] Export model package

## Phase 7: API Layer
- [ ] Build backend API endpoints
- [ ] Add background jobs for heavy tasks

## Phase 8: Demo UI / Visualization
- [ ] Create dashboard pages
- [ ] Build the demo flow (upload -> transcribe -> evaluate)
- [ ] Show pipeline status cards

## Phase 9: Open-Source Output Package
- [ ] Generate `dataset_card.md`
- [ ] Generate `model_card.md`
- [ ] Create contribution guide

## Phase 10: Final Hackathon Presentation
- [ ] Prepare live demo script
- [ ] Prepare judging-criteria talking points
