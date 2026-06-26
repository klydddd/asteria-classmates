# Static Pipeline Showcase Design

## Purpose

Build a standalone static website that showcases the BosesPH Toolkit pipeline
without changing the existing Next.js dashboard or demo routes.

The page should help judges, collaborators, and developers understand that
BosesPH is a reusable developer pipeline for Philippine-language speech
datasets, benchmarks, and fine-tuned ASR models, not only a transcription app.

## Placement

Create the static site at:

```text
apps/web/public/showcase/index.html
```

This keeps the page independent from the Next.js App Router while still making
it available through the existing web app at:

```text
/showcase/
```

The file must also be usable directly from disk in a browser.

## Visual Direction

The static page should mirror the existing web app style:

- warm parchment background
- off-white surface cards
- deep green-black foreground text
- muted warm borders
- brick red accent color
- serif display headings
- compact dashboard-style cards and sections

Use embedded CSS in the HTML file to avoid extra build dependencies and to keep
the page portable. Keep cards compact, avoid nested cards, and use a restrained
layout that feels consistent with the current dashboard rather than a generic
marketing landing page.

## Content Structure

The page should include these sections:

1. Hero
   - Product name: BosesPH Toolkit
   - Short pipeline statement: raw audio and transcripts become clean datasets,
     benchmarks, evaluation reports, and optional fine-tuned ASR models.
   - Key stats or capability chips that summarize CLI-first, Kapampangan pilot,
     WER/CER benchmarks, and reproducible outputs.

2. Pipeline overview
   - Compact cards showing the ordered sequence:
     Import, Normalize, Review, Build, Transcribe, Evaluate, Fine-tune.
   - Include the rule that reviewed and approved clips are the source for
     dataset building.
   - Link to a separate vertical Mermaid diagram page at
     `apps/web/public/showcase/pipeline/index.html`.

2a. Pipeline diagram page
   - Render a vertical Mermaid flowchart with the full data flow from raw audio
     and metadata validation through import, normalization, review, dataset
     build, baseline evaluation, optional fine-tuning, model comparison, and
     final artifacts.
   - Include concise supporting sections for stage details, command sequence,
     and generated outputs.

3. Capabilities
   - Import PLD sessions.
   - Validate audio and metadata.
   - Normalize transcripts.
   - Review clips interactively.
   - Build speaker-aware train/validation/test splits.
   - Run baseline ASR transcription.
   - Evaluate WER and CER.
   - Fine-tune Whisper with LoRA.
   - Compare baseline and fine-tuned metrics.
   - Generate dataset cards, model cards, reports, and export artifacts.

4. Command reference
   - Include concrete commands for install, validation, schema export, import,
     normalization, review, build, transcribe, evaluate, fine-tune, compare,
     backend API, web app, lint, and tests.

5. Output artifacts
   - Show the generated `outputs/` structure for dataset, benchmark, and model
     artifacts.

6. Interfaces
   - CLI as the primary interface.
   - FastAPI backend for jobs and HTTP access.
   - MCP tools for agent workflows.
   - Next.js dashboard and live demo.
   - Colab notebooks and scripts for evaluation and fine-tuning workflows.

7. Data standards and safety
   - Required metadata columns.
   - Accepted transcript tags.
   - ISO 639-3 language codes.
   - Deterministic anonymized speaker/audio IDs.
   - No private audio, PII, secrets, raw private recordings, model weights, or
     generated outputs in git.

8. Run section
   - Give a concise local workflow for someone who wants to try the toolkit.

## Interaction

The main showcase page is static and uses anchor links only. The separate
pipeline diagram page uses a Mermaid CDN module for rendering; do not add local
packages or custom application JavaScript beyond Mermaid initialization.

## Testing And Verification

Verify the work with:

```bash
pnpm --dir apps/web lint
pnpm --dir apps/web test
pnpm --dir apps/web build
```

Because the page is plain HTML under `public/`, also verify that the file exists
and contains the main showcase sections.

## Non-Goals

- Do not replace the existing dashboard homepage.
- Do not add a new App Router page.
- Do not duplicate backend logic.
- Do not introduce images, new packages, or a new styling system.
