# Phase 8 Dashboard & Demo UI — Implementation Progress

> Last updated: 2026-06-26
> Plan file: `docs/superpowers/plans/2026-06-26-phase8-dashboard-demo.md`
> Design spec: `docs/superpowers/specs/2026-06-26-phase8-dashboard-demo-design.md`

---

## Summary

Building the Phase 8 web UI for BosesPH Toolkit: a Dashboard page (`/`) showing pipeline status cards and a Demo page (`/demo`) for live audio transcription. The FastAPI backend is already complete at `src/bosesph/api/`.

**Working directory:** `apps/web/` (Next.js 16, React 19, TypeScript)
**Run tests:** `pnpm test` (Vitest 4 + @testing-library/react)
**Run dev server:** `pnpm dev` → `http://localhost:3000`

---

## Completed Tasks

### Task 1 ✅ — Tailwind v4 + shadcn/ui Setup (committed)

**What was done:**
- Installed `tailwindcss` and `@tailwindcss/postcss`
- Created `apps/web/postcss.config.mjs`
- Updated `apps/web/app/globals.css`: added `@import "tailwindcss"`, `@theme { --color-surface: ... }`, and fixed shadcn's overwritten `:root` palette vars back to the project's parchment/red palette
- Ran `pnpm dlx shadcn@latest init -d` — created `components.json`, modified `layout.tsx`, and added shadcn boilerplate to `globals.css`
- Added shadcn components: `card`, `select`, `textarea`, `skeleton`, `badge`, `button` → `apps/web/components/ui/`
- Installed `@vitejs/plugin-react` as a dev dependency
- Updated `apps/web/vitest.config.ts`: added React plugin, path alias `@/*`, `resolve.dedupe`, `server.deps.inline: ["next"]`

**Important note — shadcn init modified layout.tsx:** It added the Geist font:
```tsx
import { Geist } from "next/font/google";
const geist = Geist({ subsets: ['latin'], variable: '--font-sans' });
// html gets className={cn("font-sans", geist.variable)}
```
This is intentional. Body text is still Georgia/serif (set in CSS), Geist is the sans-serif fallback for shadcn UI elements.

**Important note — globals.css palette fix:** shadcn's `@theme inline` block maps `--color-background: var(--background)` etc., overriding our manual `@theme` block. The `:root` variables now hold the actual palette values:
```css
--background: #f4f1e8;
--foreground: #17231b;
--accent: #b33a2b;
--accent-foreground: #fffdf7;
--border: #d7d0c0;
--card: #fffdf7;
```

---

### Task 2 ✅ — API Types and Client (committed)

**Files created:**
- `apps/web/lib/api.ts` — typed fetch wrappers + all TypeScript interfaces
- `apps/web/__tests__/api.test.ts` — 5 tests, all passing

**Exports from `lib/api.ts`:**
```ts
// Types
export interface ProjectStatus { dataset_available, dataset_stats, baseline_metrics, finetuned_metrics, model_available, model_dir, model_version }
export interface DemoLanguageOption { id, label, description }
export interface DemoModelOption { id, label, model_path, available, unavailable_reason }
export interface DemoOptions { languages, models, default_language_id, default_model_id }
export interface DemoTranscriptionResult { prediction, model_id, model_label, language_id, wer, cer }
export interface Job { id, type, status: "queued"|"running"|"succeeded"|"failed", progress, result, error, created_at, updated_at }

// Functions
export function getProjectStatus(): Promise<ProjectStatus>
export function getDemoOptions(): Promise<DemoOptions>
export function submitDemo(form: FormData): Promise<Job>
export function getJob(id: string): Promise<Job>
```

Base URL comes from `process.env.NEXT_PUBLIC_API_BASE_URL` (falls back to `http://localhost:8000`). All functions throw on non-2xx.

---

### Task 3 ✅ — Nav Component + Layout (tests pass, NOT YET COMMITTED)

**Files created/modified:**
- `apps/web/components/nav.tsx` — top nav with BosesPH wordmark, Dashboard + Demo links, active-link underline via `usePathname()`
- `apps/web/app/layout.tsx` — added `<Nav />` above `{children}` inside `<main className="max-w-6xl mx-auto px-6 py-8">`
- `apps/web/__tests__/nav.test.tsx` — 3 tests, all passing

**Important note — test strategy for next/link:** Mocking `next/link` via `vi.mock` caused double DOM renders (Next.js loads both ESM and CJS versions). The tests use `container.querySelectorAll("a")` instead of `screen.getByRole("link")` to avoid this. Only `next/navigation` is mocked:
```ts
vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/"),
}));
```

**TO DO BEFORE COMMITTING TASK 3:** Run `git add` and commit with message `feat(web): add Nav component and update layout`.

---

## Remaining Tasks

### Task 4 — StatusCard Component

**Files to create:**
- `apps/web/components/status-card.tsx`
- `apps/web/__tests__/status-card.test.tsx`

**Component interface:**
```tsx
<StatusCard label={string} value={string | null} loading={boolean} />
```

Renders a shadcn `<Card>` with label, large value, and `<Skeleton data-testid="status-card-skeleton" />` when loading. Shows `"—"` when value is null.

---

### Task 5 — DashboardGrid + Dashboard Page

**Files to create/modify:**
- `apps/web/components/dashboard-grid.tsx` — Client Component, polls `getProjectStatus()` every 10s via `setInterval`, shows 7 `<StatusCard>` components in a responsive grid
- `apps/web/app/page.tsx` — replace stub `<main />` with `<DashboardGrid />`
- `apps/web/__tests__/dashboard-grid.test.tsx`

**7 cards and their data sources:**

| Card Label | API field | Format |
|---|---|---|
| Dataset Clips | `dataset_stats.total_clips` | plain number |
| Approved Clips | `dataset_stats.approved_clips` | plain number |
| Speakers | `dataset_stats.num_speakers` | plain number |
| Total Minutes | `dataset_stats.total_duration_minutes` | `"X.X min"` |
| Baseline WER | `baseline_metrics.wer` | `"XX.X%"` (× 100) |
| Fine-tuned WER | `finetuned_metrics.wer` | `"XX.X%"` (× 100) |
| Model Version | `model_version` | string as-is |

Error state: banner + Retry button. "Last updated HH:MM:SS" timestamp updates each poll.

---

### Task 6 — DemoForm Component

**Files to create:**
- `apps/web/components/demo-form.tsx`
- `apps/web/__tests__/demo-form.test.tsx`

**Component interface:**
```tsx
<DemoForm options={DemoOptions} onSubmit={(form: FormData, filename: string) => void} />
```

Fields:
- Audio file input (`data-testid="audio-input"`, accepts `.wav,.mp3,.flac,.ogg`) — drag-drop zone
- Language `<Select>` populated from `options.languages`, defaults to `options.default_language_id`
- Model `<Select>` populated from `options.models`, unavailable models are disabled, defaults to `options.default_model_id`
- Reference `<Textarea>` (optional, enables WER/CER in results)
- Transcribe `<Button>` — disabled until a file is selected

On submit: builds `FormData` with fields `audio`, `language_id`, `model_id`, `reference` (if non-empty), calls `onSubmit(form, file.name)`.

---

### Task 7 — DemoStepper Component

**Files to create:**
- `apps/web/components/demo-stepper.tsx`
- `apps/web/__tests__/demo-stepper.test.tsx`

**Component interface:**
```tsx
<DemoStepper step={"uploading"|"transcribing"|"done"|"error"} error?: string onRetry: () => void />
```

3-step horizontal stepper: Upload → Transcribe → Done. Each step circle has `data-testid="step-{key}-{status}"` where status is `active`, `done`, or `error`. Error state shows red indicator, error message, and "Try again" button that calls `onRetry`.

---

### Task 8 — DemoResult Component

**Files to create:**
- `apps/web/components/demo-result.tsx`
- `apps/web/__tests__/demo-result.test.tsx`

**Component interface:**
```tsx
<DemoResult result={DemoTranscriptionResult} filename={string} onReset={() => void} />
```

Renders:
- Header: `filename` + `result.model_label`
- `<audio data-testid="audio-player" controls />` (browser-native, no waveform library)
- Transcript text block: `result.prediction`
- WER/CER `<Badge>` chips (`"WER: XX.X%"`, `"CER: XX.X%"`) — only if `result.wer` and `result.cer` are non-null
- "Try another file" `<Button>` that calls `onReset`

---

### Task 9 — Demo Page (wire-up)

**Files to create:**
- `apps/web/app/demo/page.tsx`
- `apps/web/__tests__/demo-page.test.tsx`

**State machine:**
```ts
type Phase =
  | { kind: "form" }
  | { kind: "polling"; jobId: string; filename: string }
  | { kind: "result"; result: DemoTranscriptionResult; filename: string }
  | { kind: "error"; message: string; filename: string };
```

Flow:
1. On mount: `getDemoOptions()` → populate `<DemoForm>`
2. On form submit: `submitDemo(form)` → transition to `"polling"`; `setInterval` polls `getJob(id)` every 2s
3. `job.status === "succeeded"` → transition to `"result"`
4. `job.status === "failed"` → transition to `"error"`
5. "Try again" or "Try another file" → reset to `"form"`

The stepper is always visible once out of form state. The result panel appears below stepper on success.

---

## Known Vitest Quirks

- **`next/link` mock causes double renders:** `vi.mock("next/link", ...)` loads both ESM and CJS versions, duplicating DOM nodes. Use `container.querySelectorAll("a")` in tests instead of `screen.getByRole("link")`.
- **Timer tests:** Use `vi.useFakeTimers()` / `vi.useRealTimers()` in `beforeEach`/`afterEach` when testing polling behavior. Wrap timer advances with `await act(async () => { vi.advanceTimersByTime(N); await vi.runAllTimersAsync(); })`.
- **Fetch mocking:** Use `vi.stubGlobal("fetch", vi.fn())` in `beforeEach`. `mockResolvedValueOnce(new Response(JSON.stringify(data), { status }))`.

---

## Project Context

- API server: `bosesph-api` (FastAPI at `http://localhost:8000`)
- Backend routes: `GET /project-status`, `GET /demo/options`, `POST /demo/transcribe`, `GET /jobs/{id}`
- CSS palette: parchment `#f4f1e8`, dark `#17231b`, red accent `#b33a2b`, border `#d7d0c0`, surface `#fffdf7`
- Font: Georgia/serif for body + headings, Geist (sans) for shadcn UI elements
- Package manager: pnpm (run all commands inside `apps/web/`)
