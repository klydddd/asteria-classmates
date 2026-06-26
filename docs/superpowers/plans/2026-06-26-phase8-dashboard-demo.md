# Phase 8 Dashboard & Demo UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Dashboard (`/`) and Demo (`/demo`) pages for BosesPH Toolkit, connecting to the existing FastAPI backend.

**Architecture:** Typed `lib/api.ts` wraps all fetch calls; both pages are Client Components that poll the API on intervals. The Dashboard auto-refreshes every 10 s; the Demo polls `/jobs/{id}` every 2 s during transcription. shadcn/ui + Tailwind v4 provides the component library on top of the existing parchment/red CSS palette.

**Tech Stack:** Next.js 16, React 19, TypeScript, Tailwind CSS v4, shadcn/ui, Vitest 4, @testing-library/react

## Global Constraints

- All commands run inside `apps/web/` unless stated otherwise.
- Package manager: `pnpm` (v10). Use `pnpm dlx` for one-off executables.
- Path alias `@/*` maps to `apps/web/*` — use it in all imports.
- `NEXT_PUBLIC_API_BASE_URL` defaults to `http://localhost:8000`.
- Job status values from the API: `"queued" | "running" | "succeeded" | "failed"`.
- WER/CER are floats (e.g. `0.342` = 34.2%) — multiply by 100 and show one decimal place.
- The stepper advances when `job.status === "succeeded"` and shows an error on `"failed"`.
- `dataset_stats` field names from `GET /project-status`: `total_clips`, `approved_clips`, `num_speakers`, `total_duration_minutes`.
- Preserve existing `:root` CSS variables — they are used by `body` styles in `globals.css`.
- Never commit `node_modules`, `.next/`, or `.env.local`.

---

## File Map

**Create:**
```
apps/web/postcss.config.mjs
apps/web/lib/api.ts
apps/web/components/nav.tsx
apps/web/components/status-card.tsx
apps/web/components/dashboard-grid.tsx
apps/web/components/demo-form.tsx
apps/web/components/demo-stepper.tsx
apps/web/components/demo-result.tsx
apps/web/app/demo/page.tsx
apps/web/__tests__/api.test.ts
apps/web/__tests__/nav.test.tsx
apps/web/__tests__/status-card.test.tsx
apps/web/__tests__/dashboard-grid.test.tsx
apps/web/__tests__/demo-form.test.tsx
apps/web/__tests__/demo-stepper.test.tsx
apps/web/__tests__/demo-result.test.tsx
apps/web/__tests__/demo-page.test.tsx
```

**Modify:**
```
apps/web/app/globals.css        — add Tailwind import + @theme block (above :root)
apps/web/app/layout.tsx         — add <Nav /> above {children}
apps/web/app/page.tsx           — replace stub with <DashboardGrid />
apps/web/vitest.config.ts       — add @vitejs/plugin-react + path alias
```

---

## Task 1: Tailwind v4 + shadcn/ui Setup

**Files:**
- Create: `apps/web/postcss.config.mjs`
- Modify: `apps/web/app/globals.css`
- Modify: `apps/web/vitest.config.ts`
- Modify: `apps/web/package.json` (via pnpm add)

**Interfaces:**
- Produces: Tailwind utilities `bg-background`, `bg-surface`, `text-foreground`, `bg-accent`, `text-accent`, `border-border`; shadcn components at `@/components/ui/*`

- [ ] **Step 1: Install Tailwind and its PostCSS plugin**

```bash
pnpm add tailwindcss @tailwindcss/postcss
```

- [ ] **Step 2: Create PostCSS config**

Create `apps/web/postcss.config.mjs`:

```js
const config = {
  plugins: { "@tailwindcss/postcss": {} },
};
export default config;
```

- [ ] **Step 3: Update globals.css — add Tailwind import and theme block**

Insert these lines at the very top of `apps/web/app/globals.css`, before the existing `:root` block:

```css
@import "tailwindcss";

@theme {
  --color-background: #f4f1e8;
  --color-foreground: #17231b;
  --color-surface: #fffdf7;
  --color-accent: #b33a2b;
  --color-border: #d7d0c0;
}
```

Leave the existing `:root { --background: ... }` block unchanged below.

- [ ] **Step 4: Initialize shadcn/ui**

```bash
pnpm dlx shadcn@latest init
```

When prompted, answer:
- **Which style?** → `default`
- **Which base color?** → `neutral`
- **Where is your global CSS file?** → `app/globals.css`
- **Do you want to use CSS variables for theming?** → `yes`
- **Where is your tailwind.config.js?** → press Enter (Tailwind v4 auto-detected, no config file needed)
- **Configure the import alias for components?** → `@/components`
- **Configure the import alias for utils?** → `@/lib/utils`

This creates `apps/web/components.json` and adds shadcn boilerplate to `globals.css`.

- [ ] **Step 5: Add required shadcn components**

```bash
pnpm dlx shadcn@latest add card button select textarea skeleton badge
```

Verify `apps/web/components/ui/` now contains: `card.tsx`, `button.tsx`, `select.tsx`, `textarea.tsx`, `skeleton.tsx`, `badge.tsx`.

- [ ] **Step 6: Add Vitejs React plugin for JSX in tests**

```bash
pnpm add -D @vitejs/plugin-react
```

- [ ] **Step 7: Update vitest.config.ts**

Replace the full content of `apps/web/vitest.config.ts`:

```ts
import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, ".") },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
  },
});
```

- [ ] **Step 8: Verify setup**

```bash
pnpm dev
```

Open `http://localhost:3000` in a browser. Expect: a blank page with no console errors (the stub `<main />` is still there). Kill the server.

```bash
pnpm test
```

Expected output: `No test files found, exiting with code 0` or `0 tests passed`.

- [ ] **Step 9: Commit**

```bash
git add apps/web/postcss.config.mjs apps/web/app/globals.css apps/web/vitest.config.ts apps/web/package.json apps/web/pnpm-lock.yaml apps/web/components.json apps/web/components/ui apps/web/lib/utils.ts
git commit -m "feat(web): add Tailwind v4 and shadcn/ui"
```

---

## Task 2: API Types and Client

**Files:**
- Create: `apps/web/lib/api.ts`
- Create: `apps/web/__tests__/api.test.ts`

**Interfaces:**
- Produces:
  - `getProjectStatus(): Promise<ProjectStatus>`
  - `getDemoOptions(): Promise<DemoOptions>`
  - `submitDemo(form: FormData): Promise<Job>`
  - `getJob(id: string): Promise<Job>`
  - Types: `ProjectStatus`, `DemoOptions`, `DemoLanguageOption`, `DemoModelOption`, `Job`, `DemoTranscriptionResult`

- [ ] **Step 1: Write the failing tests**

Create `apps/web/__tests__/api.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getProjectStatus,
  getDemoOptions,
  submitDemo,
  getJob,
} from "@/lib/api";

const BASE = "http://localhost:8000";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  process.env.NEXT_PUBLIC_API_BASE_URL = BASE;
});

function mockFetch(data: unknown, status = 200) {
  vi.mocked(fetch).mockResolvedValueOnce(
    new Response(JSON.stringify(data), { status })
  );
}

describe("getProjectStatus", () => {
  it("fetches /project-status and returns the parsed body", async () => {
    const payload = { dataset_available: true, dataset_stats: { total_clips: 100 } };
    mockFetch(payload);
    const result = await getProjectStatus();
    expect(fetch).toHaveBeenCalledWith(`${BASE}/project-status`, undefined);
    expect(result).toEqual(payload);
  });

  it("throws on non-2xx response", async () => {
    mockFetch({ detail: "not found" }, 404);
    await expect(getProjectStatus()).rejects.toThrow("404");
  });
});

describe("getDemoOptions", () => {
  it("fetches /demo/options", async () => {
    const payload = { languages: [], models: [], default_language_id: "pam", default_model_id: "baseline" };
    mockFetch(payload);
    const result = await getDemoOptions();
    expect(fetch).toHaveBeenCalledWith(`${BASE}/demo/options`, undefined);
    expect(result).toEqual(payload);
  });
});

describe("submitDemo", () => {
  it("POSTs /demo/transcribe with the FormData body", async () => {
    const job = { id: "abc123", type: "demo-transcribe", status: "queued" };
    mockFetch(job);
    const form = new FormData();
    const result = await submitDemo(form);
    expect(fetch).toHaveBeenCalledWith(
      `${BASE}/demo/transcribe`,
      expect.objectContaining({ method: "POST", body: form })
    );
    expect(result).toEqual(job);
  });
});

describe("getJob", () => {
  it("fetches /jobs/{id}", async () => {
    const job = { id: "abc123", status: "succeeded", result: { prediction: "hello" } };
    mockFetch(job);
    const result = await getJob("abc123");
    expect(fetch).toHaveBeenCalledWith(`${BASE}/jobs/abc123`, undefined);
    expect(result).toEqual(job);
  });
});
```

- [ ] **Step 2: Run tests — expect failures**

```bash
pnpm test __tests__/api.test.ts
```

Expected: `Cannot find module '@/lib/api'`

- [ ] **Step 3: Create lib/api.ts**

```ts
export interface ProjectStatus {
  dataset_available: boolean;
  dataset_stats: Record<string, number> | null;
  baseline_metrics: { wer: number; cer: number } | null;
  finetuned_metrics: { wer: number; cer: number } | null;
  model_available: boolean;
  model_dir: string | null;
  model_version: string | null;
}

export interface DemoLanguageOption {
  id: string;
  label: string;
  description: string;
}

export interface DemoModelOption {
  id: string;
  label: string;
  model_path: string;
  available: boolean;
  unavailable_reason: string | null;
}

export interface DemoOptions {
  languages: DemoLanguageOption[];
  models: DemoModelOption[];
  default_language_id: string;
  default_model_id: string;
}

export interface DemoTranscriptionResult {
  prediction: string;
  model_id: string;
  model_label: string;
  language_id: string;
  wer: number | null;
  cer: number | null;
}

export interface Job {
  id: string;
  type: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: string | null;
  result: DemoTranscriptionResult | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

const base = (): string =>
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base()}${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export function getProjectStatus(): Promise<ProjectStatus> {
  return request<ProjectStatus>("/project-status");
}

export function getDemoOptions(): Promise<DemoOptions> {
  return request<DemoOptions>("/demo/options");
}

export function submitDemo(form: FormData): Promise<Job> {
  return request<Job>("/demo/transcribe", { method: "POST", body: form });
}

export function getJob(id: string): Promise<Job> {
  return request<Job>(`/jobs/${id}`);
}
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pnpm test __tests__/api.test.ts
```

Expected: `4 tests passed`

- [ ] **Step 5: Commit**

```bash
git add apps/web/lib/api.ts apps/web/__tests__/api.test.ts
git commit -m "feat(web): add typed API client"
```

---

## Task 3: Nav Component + Layout

**Files:**
- Create: `apps/web/components/nav.tsx`
- Modify: `apps/web/app/layout.tsx`
- Create: `apps/web/__tests__/nav.test.tsx`

**Interfaces:**
- Consumes: nothing (standalone)
- Produces: `<Nav />` — top nav with BosesPH wordmark and Dashboard/Demo links

- [ ] **Step 1: Write the failing test**

Create `apps/web/__tests__/nav.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Nav from "@/components/nav";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/"),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

describe("Nav", () => {
  it("renders the wordmark", () => {
    render(<Nav />);
    expect(screen.getByText("BosesPH")).toBeInTheDocument();
  });

  it("renders Dashboard and Demo links", () => {
    render(<Nav />);
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Demo" })).toHaveAttribute("href", "/demo");
  });

  it("underlines the active link", () => {
    render(<Nav />);
    const dashLink = screen.getByRole("link", { name: "Dashboard" });
    expect(dashLink).toHaveClass("underline");
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
pnpm test __tests__/nav.test.tsx
```

Expected: `Cannot find module '@/components/nav'`

- [ ] **Step 3: Create nav.tsx**

```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/demo", label: "Demo" },
] as const;

export default function Nav() {
  const pathname = usePathname();
  return (
    <nav className="flex items-center justify-between h-14 px-6 bg-surface border-b border-border">
      <span className="font-bold text-lg text-foreground font-serif">BosesPH</span>
      <div className="flex gap-6">
        {links.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`text-foreground text-sm hover:text-accent transition-colors ${
              pathname === href ? "underline" : ""
            }`}
          >
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
```

- [ ] **Step 4: Update layout.tsx to include Nav**

Replace the full content of `apps/web/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import type { ReactNode } from "react";
import Nav from "@/components/nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "BosesPH Toolkit",
  description: "Kapampangan speech recognition dashboard and demo",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
```

- [ ] **Step 5: Run tests — expect all pass**

```bash
pnpm test __tests__/nav.test.tsx
```

Expected: `3 tests passed`

- [ ] **Step 6: Commit**

```bash
git add apps/web/components/nav.tsx apps/web/app/layout.tsx apps/web/__tests__/nav.test.tsx
git commit -m "feat(web): add Nav component and update layout"
```

---

## Task 4: StatusCard Component

**Files:**
- Create: `apps/web/components/status-card.tsx`
- Create: `apps/web/__tests__/status-card.test.tsx`

**Interfaces:**
- Produces: `<StatusCard label={string} value={string | null} loading={boolean} />`

- [ ] **Step 1: Write the failing test**

Create `apps/web/__tests__/status-card.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StatusCard from "@/components/status-card";

describe("StatusCard", () => {
  it("renders label and value", () => {
    render(<StatusCard label="Dataset Clips" value="42" loading={false} />);
    expect(screen.getByText("Dataset Clips")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders em dash when value is null", () => {
    render(<StatusCard label="Baseline WER" value={null} loading={false} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders a skeleton when loading", () => {
    render(<StatusCard label="Speakers" value={null} loading={true} />);
    expect(screen.getByTestId("status-card-skeleton")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
pnpm test __tests__/status-card.test.tsx
```

Expected: `Cannot find module '@/components/status-card'`

- [ ] **Step 3: Create status-card.tsx**

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface StatusCardProps {
  label: string;
  value: string | null;
  loading: boolean;
}

export default function StatusCard({ label, value, loading }: StatusCardProps) {
  return (
    <Card className="bg-surface border-border">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-foreground/70 font-serif">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton data-testid="status-card-skeleton" className="h-8 w-24" />
        ) : (
          <p className="text-2xl font-bold text-foreground font-serif">
            {value ?? "—"}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pnpm test __tests__/status-card.test.tsx
```

Expected: `3 tests passed`

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/status-card.tsx apps/web/__tests__/status-card.test.tsx
git commit -m "feat(web): add StatusCard component"
```

---

## Task 5: DashboardGrid + Dashboard Page

**Files:**
- Create: `apps/web/components/dashboard-grid.tsx`
- Modify: `apps/web/app/page.tsx`
- Create: `apps/web/__tests__/dashboard-grid.test.tsx`

**Interfaces:**
- Consumes: `getProjectStatus(): Promise<ProjectStatus>` from `@/lib/api`; `<StatusCard />` from `@/components/status-card`
- Produces: `<DashboardGrid />` — self-contained grid that polls and renders 7 cards

- [ ] **Step 1: Write the failing tests**

Create `apps/web/__tests__/dashboard-grid.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DashboardGrid from "@/components/dashboard-grid";
import type { ProjectStatus } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getProjectStatus: vi.fn(),
}));

import { getProjectStatus } from "@/lib/api";

const mockStatus: ProjectStatus = {
  dataset_available: true,
  dataset_stats: { total_clips: 50, approved_clips: 40, num_speakers: 5, total_duration_minutes: 12.3 },
  baseline_metrics: { wer: 0.342, cer: 0.145 },
  finetuned_metrics: { wer: 0.198, cer: 0.091 },
  model_available: true,
  model_dir: "model/v1",
  model_version: "v1",
};

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe("DashboardGrid", () => {
  it("shows skeleton cards while loading", () => {
    vi.mocked(getProjectStatus).mockReturnValue(new Promise(() => {}));
    render(<DashboardGrid />);
    expect(screen.getAllByTestId("status-card-skeleton")).toHaveLength(7);
  });

  it("renders all 7 cards with data after fetch resolves", async () => {
    vi.mocked(getProjectStatus).mockResolvedValue(mockStatus);
    render(<DashboardGrid />);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(screen.getByText("50")).toBeInTheDocument();
    expect(screen.getByText("40")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("12.3 min")).toBeInTheDocument();
    expect(screen.getByText("34.2%")).toBeInTheDocument();
    expect(screen.getByText("19.8%")).toBeInTheDocument();
    expect(screen.getByText("v1")).toBeInTheDocument();
  });

  it("shows em dash for null fields", async () => {
    vi.mocked(getProjectStatus).mockResolvedValue({
      ...mockStatus,
      finetuned_metrics: null,
      model_version: null,
    });
    render(<DashboardGrid />);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(screen.getAllByText("—")).toHaveLength(2);
  });

  it("shows error banner when fetch fails", async () => {
    vi.mocked(getProjectStatus).mockRejectedValue(new Error("Network error"));
    render(<DashboardGrid />);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(screen.getByText(/could not reach the API/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("re-fetches on retry click", async () => {
    vi.mocked(getProjectStatus)
      .mockRejectedValueOnce(new Error("fail"))
      .mockResolvedValueOnce(mockStatus);
    render(<DashboardGrid />);
    await act(async () => { await vi.runAllTimersAsync(); });
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(screen.getByText("50")).toBeInTheDocument();
  });

  it("re-fetches after 10 seconds", async () => {
    vi.mocked(getProjectStatus).mockResolvedValue(mockStatus);
    render(<DashboardGrid />);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(vi.mocked(getProjectStatus)).toHaveBeenCalledTimes(1);
    await act(async () => { vi.advanceTimersByTime(10_000); await vi.runAllTimersAsync(); });
    expect(vi.mocked(getProjectStatus)).toHaveBeenCalledTimes(2);
  });
});
```

- [ ] **Step 2: Install userEvent (needed for retry test)**

```bash
pnpm add -D @testing-library/user-event
```

- [ ] **Step 3: Run tests — expect failure**

```bash
pnpm test __tests__/dashboard-grid.test.tsx
```

Expected: `Cannot find module '@/components/dashboard-grid'`

- [ ] **Step 4: Create dashboard-grid.tsx**

```tsx
"use client";
import { useCallback, useEffect, useState } from "react";
import { getProjectStatus, type ProjectStatus } from "@/lib/api";
import StatusCard from "@/components/status-card";
import { Button } from "@/components/ui/button";

function formatWer(value: number | undefined | null): string | null {
  if (value == null) return null;
  return `${(value * 100).toFixed(1)}%`;
}

function formatMinutes(value: number | undefined | null): string | null {
  if (value == null) return null;
  return `${value.toFixed(1)} min`;
}

function buildCards(status: ProjectStatus | null) {
  const s = status?.dataset_stats;
  return [
    { label: "Dataset Clips", value: s?.total_clips != null ? String(s.total_clips) : null },
    { label: "Approved Clips", value: s?.approved_clips != null ? String(s.approved_clips) : null },
    { label: "Speakers", value: s?.num_speakers != null ? String(s.num_speakers) : null },
    { label: "Total Minutes", value: formatMinutes(s?.total_duration_minutes) },
    { label: "Baseline WER", value: formatWer(status?.baseline_metrics?.wer) },
    { label: "Fine-tuned WER", value: formatWer(status?.finetuned_metrics?.wer) },
    { label: "Model Version", value: status?.model_version ?? null },
  ];
}

export default function DashboardGrid() {
  const [status, setStatus] = useState<ProjectStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchStatus = useCallback(() => {
    setError(false);
    getProjectStatus()
      .then((data) => {
        setStatus(data);
        setLoading(false);
        setLastUpdated(new Date());
      })
      .catch(() => {
        setLoading(false);
        setError(true);
      });
  }, []);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, 10_000);
    return () => clearInterval(id);
  }, [fetchStatus]);

  const cards = buildCards(status);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold font-serif text-foreground">Pipeline Status</h1>
        {lastUpdated && (
          <span className="text-xs text-foreground/50">
            Last updated {lastUpdated.toLocaleTimeString()}
          </span>
        )}
      </div>

      {error && (
        <div className="mb-6 p-4 rounded border border-accent/30 bg-accent/5 flex items-center justify-between">
          <span className="text-sm text-accent">Could not reach the API. Check that the server is running.</span>
          <Button variant="outline" size="sm" onClick={fetchStatus}>Retry</Button>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card) => (
          <StatusCard key={card.label} label={card.label} value={card.value} loading={loading} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Update app/page.tsx**

Replace the full content of `apps/web/app/page.tsx`:

```tsx
import DashboardGrid from "@/components/dashboard-grid";

export default function Home() {
  return <DashboardGrid />;
}
```

- [ ] **Step 6: Run tests — expect all pass**

```bash
pnpm test __tests__/dashboard-grid.test.tsx
```

Expected: `5 tests passed`

- [ ] **Step 7: Commit**

```bash
git add apps/web/components/dashboard-grid.tsx apps/web/app/page.tsx apps/web/__tests__/dashboard-grid.test.tsx apps/web/package.json apps/web/pnpm-lock.yaml
git commit -m "feat(web): add DashboardGrid with polling and Dashboard page"
```

---

## Task 6: DemoForm Component

**Files:**
- Create: `apps/web/components/demo-form.tsx`
- Create: `apps/web/__tests__/demo-form.test.tsx`

**Interfaces:**
- Consumes: `DemoOptions` from `@/lib/api`
- Produces: `<DemoForm options={DemoOptions} onSubmit={(form: FormData, filename: string) => void} />`

- [ ] **Step 1: Write the failing tests**

Create `apps/web/__tests__/demo-form.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DemoForm from "@/components/demo-form";
import type { DemoOptions } from "@/lib/api";

const options: DemoOptions = {
  languages: [
    { id: "pam", label: "Kapampangan", description: "Central Luzon language" },
    { id: "ilo", label: "Ilocano", description: "Northern Luzon language" },
  ],
  models: [
    { id: "baseline", label: "Whisper Small (baseline)", model_path: "openai/whisper-small", available: true, unavailable_reason: null },
    { id: "finetuned", label: "Fine-tuned (v1)", model_path: "model/v1/model", available: false, unavailable_reason: "Not trained yet" },
  ],
  default_language_id: "pam",
  default_model_id: "baseline",
};

describe("DemoForm", () => {
  it("renders language and model selects with defaults", () => {
    render(<DemoForm options={options} onSubmit={vi.fn()} />);
    expect(screen.getByText("Kapampangan")).toBeInTheDocument();
    expect(screen.getByText("Whisper Small (baseline)")).toBeInTheDocument();
  });

  it("disables Transcribe button when no file is selected", () => {
    render(<DemoForm options={options} onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: /transcribe/i })).toBeDisabled();
  });

  it("enables Transcribe button after a file is selected", async () => {
    render(<DemoForm options={options} onSubmit={vi.fn()} />);
    const file = new File(["audio"], "test.wav", { type: "audio/wav" });
    await userEvent.upload(screen.getByTestId("audio-input"), file);
    expect(screen.getByRole("button", { name: /transcribe/i })).toBeEnabled();
  });

  it("calls onSubmit with FormData and filename when submitted", async () => {
    const onSubmit = vi.fn();
    render(<DemoForm options={options} onSubmit={onSubmit} />);
    const file = new File(["audio"], "speech.wav", { type: "audio/wav" });
    await userEvent.upload(screen.getByTestId("audio-input"), file);
    await userEvent.click(screen.getByRole("button", { name: /transcribe/i }));
    expect(onSubmit).toHaveBeenCalledOnce();
    const [formArg, filenameArg] = onSubmit.mock.calls[0] as [FormData, string];
    expect(formArg.get("model_id")).toBe("baseline");
    expect(formArg.get("language_id")).toBe("pam");
    expect(filenameArg).toBe("speech.wav");
  });

  it("shows unavailable reason as disabled option label", () => {
    render(<DemoForm options={options} onSubmit={vi.fn()} />);
    expect(screen.getByText(/Fine-tuned \(v1\)/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
pnpm test __tests__/demo-form.test.tsx
```

Expected: `Cannot find module '@/components/demo-form'`

- [ ] **Step 3: Create demo-form.tsx**

```tsx
"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { DemoOptions } from "@/lib/api";

interface DemoFormProps {
  options: DemoOptions;
  onSubmit: (form: FormData, filename: string) => void;
}

export default function DemoForm({ options, onSubmit }: DemoFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [languageId, setLanguageId] = useState(options.default_language_id);
  const [modelId, setModelId] = useState(options.default_model_id);
  const [reference, setReference] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    const form = new FormData();
    form.append("audio", file);
    form.append("language_id", languageId);
    form.append("model_id", modelId);
    if (reference.trim()) form.append("reference", reference.trim());
    onSubmit(form, file.name);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-foreground/70 mb-1 font-serif">
          Audio file
        </label>
        <div className="border-2 border-dashed border-border rounded-lg p-6 text-center">
          <input
            data-testid="audio-input"
            type="file"
            accept=".wav,.mp3,.flac,.ogg"
            className="hidden"
            id="audio-upload"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <label htmlFor="audio-upload" className="cursor-pointer">
            {file ? (
              <span className="text-sm text-foreground">{file.name}</span>
            ) : (
              <span className="text-sm text-foreground/50">
                Click to select or drag a .wav / .mp3 / .flac / .ogg file
              </span>
            )}
          </label>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-foreground/70 mb-1 font-serif">
            Language
          </label>
          <Select value={languageId} onValueChange={setLanguageId}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {options.languages.map((lang) => (
                <SelectItem key={lang.id} value={lang.id}>
                  {lang.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground/70 mb-1 font-serif">
            Model
          </label>
          <Select value={modelId} onValueChange={setModelId}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {options.models.map((model) => (
                <SelectItem
                  key={model.id}
                  value={model.id}
                  disabled={!model.available}
                >
                  {model.label}
                  {!model.available && model.unavailable_reason
                    ? ` (${model.unavailable_reason})`
                    : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-foreground/70 mb-1 font-serif">
          Reference transcript{" "}
          <span className="font-normal text-foreground/40">(optional — enables WER/CER)</span>
        </label>
        <Textarea
          value={reference}
          onChange={(e) => setReference(e.target.value)}
          placeholder="Paste the correct transcript here to compute WER and CER…"
          rows={3}
        />
      </div>

      <Button
        type="submit"
        disabled={!file}
        className="w-full bg-accent text-white hover:bg-accent/90"
      >
        Transcribe
      </Button>
    </form>
  );
}
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pnpm test __tests__/demo-form.test.tsx
```

Expected: `5 tests passed`

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/demo-form.tsx apps/web/__tests__/demo-form.test.tsx
git commit -m "feat(web): add DemoForm component"
```

---

## Task 7: DemoStepper Component

**Files:**
- Create: `apps/web/components/demo-stepper.tsx`
- Create: `apps/web/__tests__/demo-stepper.test.tsx`

**Interfaces:**
- Produces: `<DemoStepper step={"uploading"|"transcribing"|"done"|"error"} error?: string onRetry: () => void />`

- [ ] **Step 1: Write the failing tests**

Create `apps/web/__tests__/demo-stepper.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DemoStepper from "@/components/demo-stepper";

describe("DemoStepper", () => {
  it("shows Upload as complete when step is transcribing", () => {
    render(<DemoStepper step="transcribing" onRetry={vi.fn()} />);
    expect(screen.getByTestId("step-upload-done")).toBeInTheDocument();
    expect(screen.getByTestId("step-transcribing-active")).toBeInTheDocument();
  });

  it("shows all steps complete when step is done", () => {
    render(<DemoStepper step="done" onRetry={vi.fn()} />);
    expect(screen.getByTestId("step-upload-done")).toBeInTheDocument();
    expect(screen.getByTestId("step-transcribing-done")).toBeInTheDocument();
    expect(screen.getByTestId("step-done-done")).toBeInTheDocument();
  });

  it("shows error indicator and retry button when step is error", async () => {
    const onRetry = vi.fn();
    render(<DemoStepper step="error" error="Model unavailable" onRetry={onRetry} />);
    expect(screen.getByText("Model unavailable")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("shows Upload as active when step is uploading", () => {
    render(<DemoStepper step="uploading" onRetry={vi.fn()} />);
    expect(screen.getByTestId("step-upload-active")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
pnpm test __tests__/demo-stepper.test.tsx
```

Expected: `Cannot find module '@/components/demo-stepper'`

- [ ] **Step 3: Create demo-stepper.tsx**

```tsx
import { Button } from "@/components/ui/button";

type StepState = "uploading" | "transcribing" | "done" | "error";

interface DemoStepperProps {
  step: StepState;
  error?: string;
  onRetry: () => void;
}

const STEPS = [
  { key: "upload", label: "Upload" },
  { key: "transcribing", label: "Transcribe" },
  { key: "done", label: "Done" },
] as const;

type StepKey = (typeof STEPS)[number]["key"];

function stepStatus(key: StepKey, current: StepState): "done" | "active" | "pending" {
  const order: StepKey[] = ["upload", "transcribing", "done"];
  const currentIndex = order.indexOf(
    current === "error" ? "transcribing" : current === "uploading" ? "upload" : current
  );
  const keyIndex = order.indexOf(key);
  if (keyIndex < currentIndex) return "done";
  if (keyIndex === currentIndex && current !== "error") return "active";
  return "pending";
}

export default function DemoStepper({ step, error, onRetry }: DemoStepperProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-0">
        {STEPS.map((s, i) => {
          const status = stepStatus(s.key, step);
          const isError = step === "error" && s.key === "transcribing";
          return (
            <div key={s.key} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center gap-1">
                <div
                  data-testid={`step-${s.key}-${isError ? "error" : status}`}
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors ${
                    isError
                      ? "bg-accent text-white"
                      : status === "done"
                      ? "bg-foreground text-white"
                      : status === "active"
                      ? "bg-accent text-white animate-pulse"
                      : "bg-border text-foreground/40"
                  }`}
                >
                  {isError ? "✕" : status === "done" ? "✓" : i + 1}
                </div>
                <span className="text-xs text-foreground/60">{s.label}</span>
              </div>
              {i < STEPS.length - 1 && (
                <div className="flex-1 h-px bg-border mx-2 mb-4" />
              )}
            </div>
          );
        })}
      </div>

      {step === "error" && (
        <div className="p-4 rounded border border-accent/30 bg-accent/5 flex items-center justify-between gap-4">
          <span className="text-sm text-accent">{error ?? "Transcription failed."}</span>
          <Button variant="outline" size="sm" onClick={onRetry}>Try again</Button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pnpm test __tests__/demo-stepper.test.tsx
```

Expected: `4 tests passed`

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/demo-stepper.tsx apps/web/__tests__/demo-stepper.test.tsx
git commit -m "feat(web): add DemoStepper component"
```

---

## Task 8: DemoResult Component

**Files:**
- Create: `apps/web/components/demo-result.tsx`
- Create: `apps/web/__tests__/demo-result.test.tsx`

**Interfaces:**
- Consumes: `DemoTranscriptionResult` from `@/lib/api`
- Produces: `<DemoResult result={DemoTranscriptionResult} filename={string} onReset={() => void} />`

- [ ] **Step 1: Write the failing tests**

Create `apps/web/__tests__/demo-result.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DemoResult from "@/components/demo-result";
import type { DemoTranscriptionResult } from "@/lib/api";

const resultWithMetrics: DemoTranscriptionResult = {
  prediction: "Malagung dampa kang meyap.",
  model_id: "baseline",
  model_label: "Whisper Small (baseline)",
  language_id: "pam",
  wer: 0.342,
  cer: 0.145,
};

const resultWithoutMetrics: DemoTranscriptionResult = {
  ...resultWithMetrics,
  wer: null,
  cer: null,
};

describe("DemoResult", () => {
  it("renders the predicted transcript", () => {
    render(<DemoResult result={resultWithMetrics} filename="speech.wav" onReset={vi.fn()} />);
    expect(screen.getByText("Malagung dampa kang meyap.")).toBeInTheDocument();
  });

  it("renders the model label", () => {
    render(<DemoResult result={resultWithMetrics} filename="speech.wav" onReset={vi.fn()} />);
    expect(screen.getByText("Whisper Small (baseline)")).toBeInTheDocument();
  });

  it("renders the filename as header", () => {
    render(<DemoResult result={resultWithMetrics} filename="speech.wav" onReset={vi.fn()} />);
    expect(screen.getByText("speech.wav")).toBeInTheDocument();
  });

  it("renders an audio element", () => {
    render(<DemoResult result={resultWithMetrics} filename="speech.wav" onReset={vi.fn()} />);
    expect(screen.getByTestId("audio-player")).toBeInTheDocument();
  });

  it("renders WER and CER chips when present", () => {
    render(<DemoResult result={resultWithMetrics} filename="speech.wav" onReset={vi.fn()} />);
    expect(screen.getByText("WER: 34.2%")).toBeInTheDocument();
    expect(screen.getByText("CER: 14.5%")).toBeInTheDocument();
  });

  it("hides metric chips when wer and cer are null", () => {
    render(<DemoResult result={resultWithoutMetrics} filename="speech.wav" onReset={vi.fn()} />);
    expect(screen.queryByText(/WER:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/CER:/)).not.toBeInTheDocument();
  });

  it("calls onReset when Try another file is clicked", async () => {
    const onReset = vi.fn();
    render(<DemoResult result={resultWithMetrics} filename="speech.wav" onReset={onReset} />);
    await userEvent.click(screen.getByRole("button", { name: /try another file/i }));
    expect(onReset).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
pnpm test __tests__/demo-result.test.tsx
```

Expected: `Cannot find module '@/components/demo-result'`

- [ ] **Step 3: Create demo-result.tsx**

```tsx
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DemoTranscriptionResult } from "@/lib/api";

interface DemoResultProps {
  result: DemoTranscriptionResult;
  filename: string;
  onReset: () => void;
}

export default function DemoResult({ result, filename, onReset }: DemoResultProps) {
  return (
    <div className="space-y-4">
      <Card className="bg-surface border-border">
        <CardHeader>
          <CardTitle className="text-base font-serif flex items-center justify-between">
            <span>{filename}</span>
            <span className="text-sm font-normal text-foreground/50">{result.model_label}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <audio
            data-testid="audio-player"
            controls
            className="w-full"
          />

          <div>
            <p className="text-xs font-medium text-foreground/50 mb-1 uppercase tracking-wide">
              Transcript
            </p>
            <p className="text-base text-foreground font-serif leading-relaxed">
              {result.prediction}
            </p>
          </div>

          {result.wer != null && result.cer != null && (
            <div className="flex gap-2">
              <Badge variant="secondary" className="font-mono">
                WER: {(result.wer * 100).toFixed(1)}%
              </Badge>
              <Badge variant="secondary" className="font-mono">
                CER: {(result.cer * 100).toFixed(1)}%
              </Badge>
            </div>
          )}
        </CardContent>
      </Card>

      <Button variant="outline" className="w-full" onClick={onReset}>
        Try another file
      </Button>
    </div>
  );
}
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pnpm test __tests__/demo-result.test.tsx
```

Expected: `7 tests passed`

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/demo-result.tsx apps/web/__tests__/demo-result.test.tsx
git commit -m "feat(web): add DemoResult component"
```

---

## Task 9: Demo Page

**Files:**
- Create: `apps/web/app/demo/page.tsx`
- Create: `apps/web/__tests__/demo-page.test.tsx`

**Interfaces:**
- Consumes: `getDemoOptions()`, `submitDemo()`, `getJob()` from `@/lib/api`; `<DemoForm />`, `<DemoStepper />`, `<DemoResult />` from their respective components
- Produces: Fully wired Demo page at `/demo`

- [ ] **Step 1: Write the failing tests**

Create `apps/web/__tests__/demo-page.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DemoPage from "@/app/demo/page";
import type { DemoOptions, Job } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getDemoOptions: vi.fn(),
  submitDemo: vi.fn(),
  getJob: vi.fn(),
}));

import { getDemoOptions, submitDemo, getJob } from "@/lib/api";

const options: DemoOptions = {
  languages: [{ id: "pam", label: "Kapampangan", description: "" }],
  models: [{ id: "baseline", label: "Whisper Small", model_path: "openai/whisper-small", available: true, unavailable_reason: null }],
  default_language_id: "pam",
  default_model_id: "baseline",
};

const queuedJob: Job = { id: "j1", type: "demo-transcribe", status: "queued", progress: null, result: null, error: null, created_at: "", updated_at: "" };
const succeededJob: Job = {
  id: "j1", type: "demo-transcribe", status: "succeeded", progress: null,
  result: { prediction: "Nung abe mu ku", model_id: "baseline", model_label: "Whisper Small", language_id: "pam", wer: null, cer: null },
  error: null, created_at: "", updated_at: "",
};
const failedJob: Job = { ...queuedJob, status: "failed", error: "Out of memory" };

beforeEach(() => {
  vi.useFakeTimers();
  vi.mocked(getDemoOptions).mockResolvedValue(options);
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe("DemoPage", () => {
  it("shows loading state then renders form after options load", async () => {
    render(<DemoPage />);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(screen.getByRole("button", { name: /transcribe/i })).toBeInTheDocument();
  });

  it("transitions to stepper after form submit", async () => {
    vi.mocked(submitDemo).mockResolvedValue(queuedJob);
    vi.mocked(getJob).mockResolvedValue(queuedJob);
    render(<DemoPage />);
    await act(async () => { await vi.runAllTimersAsync(); });

    const file = new File(["audio"], "clip.wav", { type: "audio/wav" });
    await userEvent.upload(screen.getByTestId("audio-input"), file);
    await userEvent.click(screen.getByRole("button", { name: /transcribe/i }));

    await act(async () => { await vi.runAllTimersAsync(); });
    expect(screen.getByTestId("step-upload-done")).toBeInTheDocument();
  });

  it("transitions to result view when job succeeds", async () => {
    vi.mocked(submitDemo).mockResolvedValue(queuedJob);
    vi.mocked(getJob).mockResolvedValue(succeededJob);
    render(<DemoPage />);
    await act(async () => { await vi.runAllTimersAsync(); });

    const file = new File(["audio"], "clip.wav", { type: "audio/wav" });
    await userEvent.upload(screen.getByTestId("audio-input"), file);
    await userEvent.click(screen.getByRole("button", { name: /transcribe/i }));

    await act(async () => { vi.advanceTimersByTime(2_000); await vi.runAllTimersAsync(); });
    expect(screen.getByText("Nung abe mu ku")).toBeInTheDocument();
  });

  it("shows error step when job fails", async () => {
    vi.mocked(submitDemo).mockResolvedValue(queuedJob);
    vi.mocked(getJob).mockResolvedValue(failedJob);
    render(<DemoPage />);
    await act(async () => { await vi.runAllTimersAsync(); });

    const file = new File(["audio"], "clip.wav", { type: "audio/wav" });
    await userEvent.upload(screen.getByTestId("audio-input"), file);
    await userEvent.click(screen.getByRole("button", { name: /transcribe/i }));

    await act(async () => { vi.advanceTimersByTime(2_000); await vi.runAllTimersAsync(); });
    expect(screen.getByText("Out of memory")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("resets to form when Try another file is clicked", async () => {
    vi.mocked(submitDemo).mockResolvedValue(queuedJob);
    vi.mocked(getJob).mockResolvedValue(succeededJob);
    render(<DemoPage />);
    await act(async () => { await vi.runAllTimersAsync(); });

    const file = new File(["audio"], "clip.wav", { type: "audio/wav" });
    await userEvent.upload(screen.getByTestId("audio-input"), file);
    await userEvent.click(screen.getByRole("button", { name: /transcribe/i }));
    await act(async () => { vi.advanceTimersByTime(2_000); await vi.runAllTimersAsync(); });

    await userEvent.click(screen.getByRole("button", { name: /try another file/i }));
    expect(screen.getByRole("button", { name: /transcribe/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
pnpm test __tests__/demo-page.test.tsx
```

Expected: `Cannot find module '@/app/demo/page'`

- [ ] **Step 3: Create app/demo/page.tsx**

```tsx
"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { getDemoOptions, getJob, submitDemo } from "@/lib/api";
import type { DemoOptions, DemoTranscriptionResult } from "@/lib/api";
import DemoForm from "@/components/demo-form";
import DemoStepper from "@/components/demo-stepper";
import DemoResult from "@/components/demo-result";
import { Skeleton } from "@/components/ui/skeleton";

type Phase =
  | { kind: "form" }
  | { kind: "polling"; jobId: string; filename: string }
  | { kind: "result"; result: DemoTranscriptionResult; filename: string }
  | { kind: "error"; message: string; filename: string };

export default function DemoPage() {
  const [options, setOptions] = useState<DemoOptions | null>(null);
  const [phase, setPhase] = useState<Phase>({ kind: "form" });
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getDemoOptions().then(setOptions).catch(console.error);
  }, []);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (phase.kind !== "polling") return;
    const { jobId, filename } = phase;

    intervalRef.current = setInterval(async () => {
      try {
        const job = await getJob(jobId);
        if (job.status === "succeeded") {
          stopPolling();
          setPhase({ kind: "result", result: job.result as DemoTranscriptionResult, filename });
        } else if (job.status === "failed") {
          stopPolling();
          setPhase({ kind: "error", message: job.error ?? "Transcription failed.", filename });
        }
      } catch {
        stopPolling();
        setPhase({ kind: "error", message: "Could not check job status.", filename });
      }
    }, 2_000);

    return stopPolling;
  }, [phase, stopPolling]);

  async function handleSubmit(form: FormData, filename: string) {
    try {
      const job = await submitDemo(form);
      setPhase({ kind: "polling", jobId: job.id, filename });
    } catch (err) {
      setPhase({ kind: "error", message: String(err), filename });
    }
  }

  function reset() {
    stopPolling();
    setPhase({ kind: "form" });
  }

  const stepperStep =
    phase.kind === "polling"
      ? "transcribing"
      : phase.kind === "result"
      ? "done"
      : phase.kind === "error"
      ? "error"
      : "uploading";

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold font-serif text-foreground mb-6">Live Demo</h1>

      {phase.kind !== "form" && (
        <div className="mb-6">
          <DemoStepper
            step={stepperStep}
            error={phase.kind === "error" ? phase.message : undefined}
            onRetry={reset}
          />
        </div>
      )}

      {phase.kind === "form" && (
        options ? (
          <DemoForm options={options} onSubmit={handleSubmit} />
        ) : (
          <div className="space-y-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        )
      )}

      {phase.kind === "result" && (
        <DemoResult result={phase.result} filename={phase.filename} onReset={reset} />
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pnpm test __tests__/demo-page.test.tsx
```

Expected: `5 tests passed`

- [ ] **Step 5: Run full test suite**

```bash
pnpm test
```

Expected: all tests pass.

- [ ] **Step 6: Smoke-test in browser**

```bash
pnpm dev
```

Open `http://localhost:3000` — verify the Dashboard page renders the pipeline status grid.
Open `http://localhost:3000/demo` — verify the Demo form renders with the language and model selects.
Kill the server.

- [ ] **Step 7: Commit**

```bash
git add apps/web/app/demo/page.tsx apps/web/__tests__/demo-page.test.tsx
git commit -m "feat(web): add Demo page — completes Phase 8 UI"
```

---

## Self-Review Notes

- **Spec coverage:** All 7 dashboard cards ✓, polling ✓, error/skeleton states ✓, demo form ✓, step stepper ✓, results with WER/CER ✓, "try another" reset ✓, shadcn/ui + Tailwind ✓, shared nav ✓.
- **Types:** `Job.status` uses `"succeeded"/"failed"` (not "completed") — matches the API. `DemoTranscriptionResult` shape matches `src/bosesph/api/models.py`. All types used in tests match the shapes defined in Task 2.
- **Naming:** `stepperStep` variable in demo page derives `"error"` for both error and missing-file states — the stepper's `error` prop provides the message, so no ambiguity.
- **Placeholder scan:** No TBDs. All test assertions reference real component outputs.
