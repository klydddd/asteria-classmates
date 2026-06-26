# Phase 8 — Dashboard & Demo UI Design

**Date:** 2026-06-26
**Scope:** Build the two functional pages required by Phase 8: Dashboard (`/`) and Demo (`/demo`).

---

## 1. Context

BosesPH Toolkit is a CLI-first pipeline for Philippine-language speech datasets. The web app (`apps/web`) is a Next.js 16 / React 19 frontend that surfaces pipeline outputs to hackathon judges. Phase 8 is the MVP UI — two pages that let judges see technical progress and interact with a live transcription demo in under two minutes.

The FastAPI backend is already complete. The relevant endpoints are:

| Endpoint | Purpose |
|---|---|
| `GET /project-status` | Dashboard metrics (dataset stats, WER, model version) |
| `GET /demo/options` | Available languages and models |
| `POST /demo/transcribe` | Submit audio for transcription (returns a Job) |
| `GET /jobs/{id}` | Poll job progress and retrieve result |

---

## 2. Decisions

| Question | Decision |
|---|---|
| Navigation structure | Two separate routes: `/` → Dashboard, `/demo` → Demo |
| Styling | shadcn/ui + Tailwind CSS; existing CSS custom properties (parchment palette, red accent) preserved in `globals.css` alongside Tailwind base |
| Data fetching | Typed `lib/api.ts` client, Client Components, `setInterval` polling — no SWR or React Query |
| Demo waiting UX | 3-step horizontal stepper (Upload → Transcribing → Done) |

---

## 3. Layout & Navigation

A top nav is added to `app/layout.tsx`. It contains:
- BosesPH wordmark (left)
- "Dashboard" and "Demo" links (right), with active-link underline

The existing `<html>` / `<body>` styles (serif font, gradient background, palette variables) are unchanged. The nav sits above `{children}`.

---

## 4. Dashboard Page (`/`)

### Behaviour
- Client Component; fetches `getProjectStatus()` on mount.
- Re-fetches every 10 seconds via `setInterval`. Clears interval on unmount.
- Shows skeleton cards while loading.
- Shows an inline error banner with a "Retry" button if the API is unreachable.
- Displays a "Last updated HH:MM:SS" timestamp that refreshes with each successful poll.

### Status Cards Grid

Responsive layout: 1 col (mobile) → 2 col (tablet) → 4 col (desktop).

| Card Label | API field | Empty value |
|---|---|---|
| Dataset Clips | `dataset_stats.total_clips` | — |
| Approved Clips | `dataset_stats.approved_clips` | — |
| Speakers | `dataset_stats.num_speakers` | — |
| Total Minutes | `dataset_stats.total_duration_minutes` | — |
| Baseline WER | `baseline_metrics.wer` | — |
| Fine-tuned WER | `finetuned_metrics.wer` | — |
| Model Version | `model_version` | — |

Cards with no data (field is `null`) show "—" rather than hiding. This is intentional — judges need to see which pipeline stages haven't run yet.

---

## 5. Demo Page (`/demo`)

### States

The page has two top-level visual states: **form** and **results**.

#### Form State

A centered card containing:
1. **Audio upload** — drag-and-drop zone or file picker; accepts `.wav`, `.mp3`, `.flac`, `.ogg`.
2. **Language selector** — populated from `GET /demo/options`.
3. **Model selector** — populated from `GET /demo/options`; fine-tuned option disabled if not available.
4. **Reference transcript** — optional textarea; if provided, WER/CER appear in results.
5. **Transcribe button** — disabled until an audio file is selected.

On submit: POSTs to `/demo/transcribe`, stores the returned Job ID, transitions to progress state.

#### Progress State

A 3-step horizontal stepper replaces the form inputs:

```
[✓] Upload  →  [⟳] Transcribing  →  [ ] Done
```

- Step 1 (Upload) is immediately marked complete.
- Step 2 (Transcribing) pulses; polls `GET /jobs/{id}` every 2 seconds.
- Step 3 (Done) advances when `job.status === "succeeded"`.
- On job failure: stepper shows a red error indicator with `job.error` message and a "Try again" button that resets to form state.

#### Results Panel

Appears below the stepper on completion:

- Header: audio filename + model used
- HTML5 `<audio>` element with browser-native controls (no waveform library)
- Predicted transcript in a readable text block
- WER / CER shown as two stat chips (only if a reference transcript was provided)
- "Try another file" button — resets full page to form state

---

## 6. Data Layer

### `lib/api.ts`

Four typed async functions; all throw on non-2xx responses.

```ts
getProjectStatus(): Promise<ProjectStatus>
getDemoOptions(): Promise<DemoOptions>
submitDemo(form: FormData): Promise<Job>
getJob(id: string): Promise<Job>
```

Base URL: `process.env.NEXT_PUBLIC_API_BASE_URL` (already in `.env.example`).

### Type shapes (mirroring the API)

```ts
interface ProjectStatus {
  dataset_available: boolean;
  dataset_stats: Record<string, number> | null;
  baseline_metrics: { wer: number; cer: number } | null;
  finetuned_metrics: { wer: number; cer: number } | null;
  model_available: boolean;
  model_dir: string | null;
  model_version: string | null;
}

interface DemoLanguageOption { id: string; label: string; description: string }
interface DemoModelOption {
  id: string; label: string; model_path: string;
  available: boolean; unavailable_reason: string | null;
}
interface DemoOptions {
  languages: DemoLanguageOption[];
  models: DemoModelOption[];
  default_language_id: string;
  default_model_id: string;
}

// Job status values from the API: "queued" | "running" | "succeeded" | "failed"
interface Job {
  id: string;
  type: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: string | null;
  result: DemoTranscriptionResult | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

// Payload in job.result when type === "demo-transcribe"
interface DemoTranscriptionResult {
  prediction: string;
  model_id: string;
  model_label: string;
  language_id: string;
  wer: number | null;
  cer: number | null;
}
```

---

## 7. File Structure

```
apps/web/
  app/
    layout.tsx              ← Add <Nav /> above {children}; keep existing html/body
    page.tsx                ← Dashboard (replace empty stub)
    demo/
      page.tsx              ← Demo page
    globals.css             ← Add Tailwind base; keep palette variables
  components/
    nav.tsx                 ← Top nav (wordmark + two links)
    status-card.tsx         ← Single metric card (label, value, icon slot)
    dashboard-grid.tsx      ← 7-card grid with 10s polling + error/skeleton states
    demo-form.tsx           ← Upload zone + selects + optional reference + submit
    demo-stepper.tsx        ← 3-step horizontal progress tracker
    demo-result.tsx         ← Audio player + transcript block + metric chips
  lib/
    api.ts                  ← Typed fetch wrappers
```

---

## 8. Styling Notes

- Tailwind's `@tailwind base/components/utilities` directives are added to `globals.css` above the existing `:root` block.
- The existing palette variables (`--background`, `--foreground`, `--surface`, `--accent`, `--border`) are used in Tailwind config as `colors.background`, etc., so component classes can reference them.
- shadcn/ui components (Card, Button, Select, Textarea, Skeleton, Badge) are added via `npx shadcn@latest add` — they pick up the palette automatically through the CSS variable mapping.
- Serif font (Georgia) is kept for body text. shadcn UI elements default to the system sans stack; override with `font-serif` where needed for consistency.

---

## 9. Out of Scope

- The "Future Implementations" pages (Collect, Annotate, Dataset, Train, Evaluate, Docs) are deferred per Tasks.md.
- Waveform visualization library (wavesurfer.js etc.) — native `<audio>` controls are sufficient for the demo.
- Authentication, user sessions, or multi-workspace support.
