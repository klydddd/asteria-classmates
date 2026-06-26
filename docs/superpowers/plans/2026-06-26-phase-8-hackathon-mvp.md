# Phase 8 Hackathon MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish a two-page hackathon showcase with four real project metrics and one direct WAV-to-transcript demo.

**Architecture:** Keep the completed FastAPI project-status, controlled-option, and transient-transcription endpoints. Add fixed localhost CORS, then build a compact Next.js App Router frontend that calls FastAPI directly and uses the native browser audio player.

**Tech Stack:** Python 3.10+, FastAPI, pytest, Next.js 16, React 19, TypeScript, plain CSS, Vitest, Testing Library, ESLint, pnpm.

---

## Completed Backend Foundation

Do not reimplement these committed tasks:

- `630eaf6`, `d2d127a`, `68ee63d`: deterministic project status.
- `3f886b5`, `877ffe7`, `c62d9da`: controlled model/language options.
- `9f12e2a`: transient WAV transcription jobs and cleanup.

---

### Task 1: Add Fixed Localhost CORS

**Files:**
- Modify: `src/bosesph/api/app.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing CORS tests**

```python
def test_api_allows_local_frontend_origin(
    client: tuple[TestClient, Path],
) -> None:
    test_client, _ = client
    response = test_client.options(
        "/project-status",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:3000"
    )


def test_api_rejects_nonlocal_frontend_origin(
    client: tuple[TestClient, Path],
) -> None:
    test_client, _ = client
    response = test_client.options(
        "/project-status",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
```

- [ ] **Step 2: Run tests and verify failure**

```bash
PYTHONPATH=src /Users/klydu/PersonalProjects/Asteria/.venv/bin/pytest \
  tests/test_api.py -k "frontend_origin" -v
```

Expected: FAIL because no CORS middleware is installed.

- [ ] **Step 3: Add fixed local middleware**

In `src/bosesph/api/app.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

LOCAL_FRONTEND_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Immediately after FastAPI construction:
app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

- [ ] **Step 4: Verify**

```bash
PYTHONPATH=src /Users/klydu/PersonalProjects/Asteria/.venv/bin/pytest \
  tests/test_api.py -q
/Users/klydu/PersonalProjects/Asteria/.venv/bin/ruff check \
  src/bosesph/api/app.py tests/test_api.py
/Users/klydu/PersonalProjects/Asteria/.venv/bin/black --check \
  src/bosesph/api/app.py tests/test_api.py
```

- [ ] **Step 5: Commit**

```bash
git add src/bosesph/api/app.py tests/test_api.py
git commit -m "feat(api): allow local dashboard origins"
```

---

### Task 2: Scaffold Minimal Next.js Frontend

**Files:**
- Delete: `apps/web/.gitkeep`
- Create: `apps/web/package.json`
- Create: `apps/web/pnpm-lock.yaml`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/eslint.config.mjs`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/vitest.setup.ts`
- Create: `apps/web/.env.example`
- Create: `apps/web/app/layout.tsx`
- Create: `apps/web/app/globals.css`
- Create: `apps/web/app/page.tsx`

- [ ] **Step 1: Enable pnpm**

```bash
corepack enable
corepack prepare pnpm@10.17.1 --activate
pnpm --version
```

Expected: `10.17.1`.

- [ ] **Step 2: Create package metadata**

```json
{
  "name": "@bosesph/web",
  "version": "0.1.0",
  "private": true,
  "packageManager": "pnpm@10.17.1",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint .",
    "test": "vitest run --passWithNoTests"
  },
  "dependencies": {
    "next": "16.2.9",
    "react": "^19.2.0",
    "react-dom": "^19.2.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.0",
    "@testing-library/user-event": "^14.6.1",
    "@types/node": "^24.0.0",
    "@types/react": "^19.2.0",
    "@types/react-dom": "^19.2.0",
    "eslint": "^9.0.0",
    "eslint-config-next": "16.2.9",
    "jsdom": "^27.0.0",
    "typescript": "^5.9.0",
    "vitest": "^4.0.0"
  }
}
```

- [ ] **Step 3: Create configuration**

`apps/web/next.config.ts`:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = { reactStrictMode: true };
export default nextConfig;
```

`apps/web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "react-jsx",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

`apps/web/eslint.config.mjs`:

```javascript
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypeScript from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTypeScript,
  globalIgnores([".next/**", "coverage/**", "next-env.d.ts"]),
]);
```

`apps/web/vitest.config.ts`:

```typescript
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    restoreMocks: true,
  },
  resolve: { alias: { "@": root } },
});
```

`apps/web/vitest.setup.ts`:

```typescript
import "@testing-library/jest-dom/vitest";
```

`apps/web/.env.example`:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 4: Create minimum App Router files**

`apps/web/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "BosesPH Toolkit",
  description: "Kapampangan speech dataset and ASR demo.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

`apps/web/app/page.tsx`:

```tsx
export default function Home() {
  return <main>BosesPH Toolkit</main>;
}
```

`apps/web/app/globals.css`:

```css
:root {
  --ink: #17211b;
  --muted: #5e6a63;
  --paper: #f4f1e8;
  --card: #fffdf7;
  --line: #cbc8ba;
  --green: #1f5b46;
  --orange: #d77b32;
  font-family: Georgia, "Times New Roman", serif;
  color: var(--ink);
  background: var(--paper);
}

* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; background: var(--paper); }
button, input, select, textarea { font: inherit; }
a { color: inherit; }
```

- [ ] **Step 5: Install and verify**

```bash
pnpm --dir apps/web install
pnpm --dir apps/web lint
pnpm --dir apps/web test
pnpm --dir apps/web build
```

- [ ] **Step 6: Commit**

```bash
git add apps/web
git commit -m "feat(web): scaffold hackathon dashboard"
```

---

### Task 3: Build Four-Card Dashboard

**Files:**
- Create: `apps/web/lib/api.ts`
- Create: `apps/web/lib/dashboard.ts`
- Create: `apps/web/components/app-shell.tsx`
- Create: `apps/web/components/dashboard.tsx`
- Modify: `apps/web/app/page.tsx`
- Modify: `apps/web/app/globals.css`
- Create: `apps/web/tests/dashboard.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
import { render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import Dashboard from "@/components/dashboard";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

beforeEach(() => vi.resetAllMocks());

test("renders four real project metrics", async () => {
  vi.mocked(api.getProjectStatus).mockResolvedValue({
    dataset_available: true,
    dataset_stats: { total_clips: 68, total_speakers: 4 },
    baseline_metrics: { wer: 0.91, cer: 0.52 },
    finetuned_metrics: { wer: 0.75, cer: 0.34 },
    model_available: true,
    model_dir: "model/bosesph-kapampangan-v1",
    model_version: "bosesph-kapampangan-v1",
  });

  render(<Dashboard />);

  expect(await screen.findByText("68")).toBeInTheDocument();
  expect(screen.getByText("4")).toBeInTheDocument();
  expect(screen.getByText("91.0%")).toBeInTheDocument();
  expect(screen.getByText("75.0%")).toBeInTheDocument();
});

test("shows unavailable values without fabricating data", async () => {
  vi.mocked(api.getProjectStatus).mockResolvedValue({
    dataset_available: false,
    dataset_stats: null,
    baseline_metrics: null,
    finetuned_metrics: null,
    model_available: false,
    model_dir: null,
    model_version: null,
  });

  render(<Dashboard />);

  expect(await screen.findAllByText("Not available")).toHaveLength(4);
});
```

- [ ] **Step 2: Run and verify failure**

```bash
pnpm --dir apps/web test tests/dashboard.test.tsx
```

- [ ] **Step 3: Add typed API client**

`apps/web/lib/api.ts`:

```typescript
export type ProjectStatus = {
  dataset_available: boolean;
  dataset_stats: { total_clips?: number; total_speakers?: number } | null;
  baseline_metrics: { wer: number; cer: number } | null;
  finetuned_metrics: { wer: number; cer: number } | null;
  model_available: boolean;
  model_dir: string | null;
  model_version: string | null;
};

export type DemoOptions = {
  languages: { id: string; label: string; description: string }[];
  models: {
    id: string;
    label: string;
    model_path: string;
    available: boolean;
    unavailable_reason: string | null;
    decoding_language: string | null;
  }[];
  default_language_id: string;
  default_model_id: string;
};

export type DemoResult = {
  prediction: string;
  model_id: string;
  model_label: string;
  language_id: string;
  wer: number | null;
  cer: number | null;
};

export type Job = {
  id: string;
  type: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: string | null;
  result: DemoResult | null;
  error: string | null;
};

const API =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, init);
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(body?.detail ?? `API request failed (${response.status}).`);
  }
  return (await response.json()) as T;
}

export const getProjectStatus = () =>
  json<ProjectStatus>("/project-status", { cache: "no-store" });
export const getDemoOptions = () =>
  json<DemoOptions>("/demo/options", { cache: "no-store" });
export const submitDemo = (body: FormData) =>
  json<Job>("/demo/transcribe", { method: "POST", body });
export const getJob = (id: string) =>
  json<Job>(`/jobs/${id}`, { cache: "no-store" });
```

- [ ] **Step 4: Add card mapping**

`apps/web/lib/dashboard.ts`:

```typescript
import type { ProjectStatus } from "@/lib/api";

export const percent = (value: number | undefined) =>
  value === undefined ? "Not available" : `${(value * 100).toFixed(1)}%`;

export function dashboardCards(status: ProjectStatus) {
  const number = (value: number | undefined) =>
    value === undefined ? "Not available" : String(value);
  return [
    ["Dataset Clips", number(status.dataset_stats?.total_clips)],
    ["Speakers", number(status.dataset_stats?.total_speakers)],
    ["Baseline WER", percent(status.baseline_metrics?.wer)],
    ["Fine-tuned WER", percent(status.finetuned_metrics?.wer)],
  ] as const;
}
```

- [ ] **Step 5: Add shell and Dashboard**

`apps/web/components/app-shell.tsx`:

```tsx
import Link from "next/link";
import type { ReactNode } from "react";

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="shell">
      <header className="topbar">
        <Link className="brand" href="/">BosesPH</Link>
        <nav>
          <Link href="/">Dashboard</Link>
          <Link href="/demo">Demo</Link>
        </nav>
      </header>
      {children}
    </div>
  );
}
```

`apps/web/components/dashboard.tsx`:

```tsx
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getProjectStatus, type ProjectStatus } from "@/lib/api";
import { dashboardCards } from "@/lib/dashboard";

export default function Dashboard() {
  const [status, setStatus] = useState<ProjectStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getProjectStatus().then(setStatus).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "Unable to load status.");
    });
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Kapampangan speech toolkit</p>
        <h1>Build speech resources. Measure the model. Hear the result.</h1>
        <Link className="button" href="/demo">Open live demo</Link>
      </section>
      <section className="metrics">
        {error ? <p role="alert">{error}</p> : null}
        {!status && !error ? <p>Loading project status...</p> : null}
        {status
          ? dashboardCards(status).map(([label, value]) => (
              <article className="metric" key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </article>
            ))
          : null}
      </section>
    </main>
  );
}
```

Replace `apps/web/app/page.tsx`:

```tsx
import AppShell from "@/components/app-shell";
import Dashboard from "@/components/dashboard";

export default function Home() {
  return <AppShell><Dashboard /></AppShell>;
}
```

- [ ] **Step 6: Add compact responsive styles**

Append:

```css
.shell { width: min(1080px, calc(100% - 32px)); margin: auto; }
.topbar { display: flex; justify-content: space-between; padding: 24px 0; }
.topbar nav { display: flex; gap: 18px; }
.brand, .topbar a { text-decoration: none; font-weight: 700; }
.hero {
  padding: clamp(40px, 8vw, 86px);
  border: 1px solid var(--line);
  border-radius: 28px 8px;
  background: var(--card);
}
.hero h1 {
  max-width: 800px;
  margin: 10px 0 28px;
  font-size: clamp(2.7rem, 7vw, 5.8rem);
  line-height: .95;
}
.eyebrow { color: var(--orange); font-weight: 700; text-transform: uppercase; }
.button {
  display: inline-block;
  padding: 13px 18px;
  border-radius: 999px;
  color: white;
  background: var(--green);
  text-decoration: none;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  padding: 36px 0 72px;
}
.metric {
  min-height: 150px;
  padding: 20px;
  border: 1px solid var(--line);
  border-top: 5px solid var(--green);
  border-radius: 18px 5px;
  background: var(--card);
}
.metric span { color: var(--muted); font-size: .8rem; }
.metric strong { display: block; margin-top: 28px; font-size: 2rem; }
@media (max-width: 760px) {
  .metrics { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .metrics { grid-template-columns: 1fr; }
}
```

- [ ] **Step 7: Verify and commit**

```bash
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web build
git add apps/web
git commit -m "feat(web): build hackathon dashboard"
```

---

### Task 4: Build Native-Audio Demo

**Files:**
- Create: `apps/web/components/demo-form.tsx`
- Create: `apps/web/app/demo/page.tsx`
- Modify: `apps/web/app/globals.css`
- Create: `apps/web/tests/demo.test.tsx`

- [ ] **Step 1: Write failing focused tests**

Test controlled options, disabled unavailable model, successful result with
metrics, and failed job:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import DemoForm from "@/components/demo-form";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

beforeEach(() => vi.resetAllMocks());

const options: api.DemoOptions = {
  languages: [
    { id: "kapampangan", label: "Kapampangan", description: "Default" },
    { id: "auto", label: "Auto-detect", description: "Automatic" },
  ],
  models: [
    {
      id: "baseline",
      label: "Whisper Small (baseline)",
      model_path: "openai/whisper-small",
      available: true,
      unavailable_reason: null,
      decoding_language: null,
    },
    {
      id: "finetuned",
      label: "BosesPH fine-tuned model",
      model_path: "",
      available: false,
      unavailable_reason: "No local fine-tuned model found.",
      decoding_language: null,
    },
  ],
  default_language_id: "kapampangan",
  default_model_id: "baseline",
};

test("renders controlled choices", async () => {
  vi.mocked(api.getDemoOptions).mockResolvedValue(options);
  render(<DemoForm />);
  expect(await screen.findByText("Whisper Small (baseline)")).toBeInTheDocument();
  expect(screen.getByRole("option", { name: /fine-tuned/i })).toBeDisabled();
});

test("submits WAV and renders transcript metrics", async () => {
  const user = userEvent.setup();
  vi.mocked(api.getDemoOptions).mockResolvedValue(options);
  vi.mocked(api.submitDemo).mockResolvedValue({
    id: "job-1",
    type: "demo-transcribe",
    status: "queued",
    progress: null,
    result: null,
    error: null,
  });
  vi.mocked(api.getJob).mockResolvedValue({
    id: "job-1",
    type: "demo-transcribe",
    status: "succeeded",
    progress: "transcribing",
    result: {
      prediction: "Masanting ya ing aldo",
      model_id: "baseline",
      model_label: "Whisper Small (baseline)",
      language_id: "kapampangan",
      wer: 0,
      cer: 0,
    },
    error: null,
  });

  render(<DemoForm />);
  await screen.findByText("Whisper Small (baseline)");
  await user.upload(
    screen.getByLabelText("WAV audio"),
    new File(["audio"], "clip.wav", { type: "audio/wav" }),
  );
  await user.click(screen.getByRole("button", { name: "Transcribe" }));

  expect(await screen.findByText("Masanting ya ing aldo")).toBeInTheDocument();
  expect(screen.getAllByText("0.0%")).toHaveLength(2);
});
```

- [ ] **Step 2: Run and verify failure**

```bash
pnpm --dir apps/web test tests/demo.test.tsx
```

- [ ] **Step 3: Implement form**

Create `apps/web/components/demo-form.tsx` with:

- Options fetched on mount.
- One `.wav` input.
- `URL.createObjectURL(file)` native `<audio controls>`.
- URL revoked when file changes or component unmounts.
- Language and model selects.
- Optional reference textarea.
- FormData submission.
- Polling `getJob()` every 750 ms until terminal status.
- Queued/running text.
- Result transcript, model, WER, CER.
- Actionable error message.
- Inputs retained after failure.

Use this polling helper inside the component:

```typescript
async function waitForJob(id: string): Promise<Job> {
  for (;;) {
    const job = await getJob(id);
    if (job.status === "succeeded" || job.status === "failed") return job;
    await new Promise((resolve) => window.setTimeout(resolve, 750));
  }
}
```

The metric display uses:

```typescript
const metric = (value: number | null) =>
  value === null ? "Not available" : `${(value * 100).toFixed(1)}%`;
```

- [ ] **Step 4: Add page**

```tsx
import AppShell from "@/components/app-shell";
import DemoForm from "@/components/demo-form";

export default function DemoPage() {
  return (
    <AppShell>
      <main className="demo-page">
        <header>
          <p className="eyebrow">Live transcription</p>
          <h1>Upload one Kapampangan WAV clip.</h1>
        </header>
        <DemoForm />
      </main>
    </AppShell>
  );
}
```

- [ ] **Step 5: Add compact form/result CSS**

Use a two-column desktop layout and one-column mobile layout. Controls must be
at least 44px high. Use native audio controls; do not add waveform libraries.

- [ ] **Step 6: Verify and commit**

```bash
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web build
git add apps/web
git commit -m "feat(web): add hackathon transcription demo"
```

---

### Task 5: Document And Verify Phase 8 MVP

**Files:**
- Modify: `README.md`
- Modify: `Tasks.md`
- Modify: `Simple_Tasks.md`
- Modify: `docs/phase8_implementation_handoff.md`

- [ ] **Step 1: Update documentation**

Document:

```bash
corepack enable
corepack prepare pnpm@10.17.1 --activate
pnpm --dir apps/web install
cp apps/web/.env.example apps/web/.env.local
bosesph-api
pnpm --dir apps/web dev
```

Describe `/` and `/demo`, controlled models, optional reference scoring, and
temporary upload deletion.

- [ ] **Step 2: Mark active Phase 8 tasks complete**

Mark Dashboard, demo flow, and status cards complete. Keep Collect, Annotate,
Dataset, Train, Evaluate, and Docs pages under Future Implementations.

- [ ] **Step 3: Run full verification**

```bash
PYTHONPATH=src /Users/klydu/PersonalProjects/Asteria/.venv/bin/pytest -q
/Users/klydu/PersonalProjects/Asteria/.venv/bin/ruff check .
/Users/klydu/PersonalProjects/Asteria/.venv/bin/black --check .
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web build
git diff --check
```

- [ ] **Step 4: Smoke test**

Run API and frontend, load `/` and `/demo`, submit one WAV with and without a
reference, and verify:

```bash
test ! -d outputs/.demo_uploads
```

- [ ] **Step 5: Commit**

```bash
git add README.md Tasks.md Simple_Tasks.md docs apps/web src tests
git commit -m "docs: complete Phase 8 hackathon MVP"
```

