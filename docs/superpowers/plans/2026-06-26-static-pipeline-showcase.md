# Static Pipeline Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone static showcase page for BosesPH Toolkit pipeline capabilities.

**Architecture:** Add static HTML files under `apps/web/public/showcase/`. The main showcase page uses embedded CSS copied from the existing app color and typography direction, static anchor navigation, and compact pipeline cards. A separate `/showcase/pipeline/` page uses a Mermaid CDN module for the full vertical pipeline diagram.

**Tech Stack:** Static HTML, embedded CSS, Mermaid CDN module, existing Next.js `public/` asset serving, pnpm verification commands.

---

## File Structure

- Create: `apps/web/public/showcase/index.html`
  - Static page with embedded CSS, anchor navigation, compact pipeline cards, command reference, output tree, interfaces, and data safety sections.
- Create: `apps/web/public/showcase/pipeline/index.html`
  - Static page with embedded CSS, a vertical Mermaid diagram, stage details, command sequence, and output summaries.
- No route changes are required because Next.js serves `public/showcase/index.html` at `/showcase/`.
- No package changes are required.

### Task 1: Add Static Showcase Page

**Files:**
- Create: `apps/web/public/showcase/index.html`

- [ ] **Step 1: Create the static HTML shell**

Add a complete HTML document with:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>BosesPH Toolkit Showcase</title>
    <meta
      name="description"
      content="Static showcase of the BosesPH Toolkit pipeline for Philippine-language speech datasets, benchmarks, and fine-tuned ASR models."
    />
  </head>
  <body>
    <main>
      <h1>BosesPH Toolkit</h1>
    </main>
  </body>
</html>
```

- [ ] **Step 2: Add embedded style tokens**

Use CSS variables matching the existing app:

```css
:root {
  --surface: #fffdf7;
  --background: #f4f1e8;
  --foreground: #17231b;
  --accent: #b33a2b;
  --border: #d7d0c0;
  --muted: #e8e4d8;
  --muted-foreground: #6b5f52;
}
```

Also define responsive layout, compact cards, code blocks, and typography using only CSS in this file.

- [ ] **Step 3: Add static content sections**

Add sections for:

```text
Hero
Pipeline overview
Capabilities
Command reference
Output artifacts
Interfaces
Data standards and safety
Run it locally
```

Use commands and content from `Requirements.md`, `Tasks.md`, and the BosesPH pipeline skill. The main showcase pipeline overview uses cards. The separate pipeline page uses a vertical Mermaid flowchart.

- [ ] **Step 4: Verify the static file exists and has expected sections**

Run:

```bash
test -f apps/web/public/showcase/index.html
test -f apps/web/public/showcase/pipeline/index.html
rg -n "Pipeline overview|Command reference|Output artifacts|Data standards|Run it locally" apps/web/public/showcase/index.html
rg -n "flowchart TD|Vertical pipeline|Pipeline command sequence|Final outputs" apps/web/public/showcase/pipeline/index.html
```

Expected: `test` exits successfully and `rg` prints matching section lines.

### Task 2: Run Web Verification

**Files:**
- Verify: `apps/web/public/showcase/index.html`

- [ ] **Step 1: Run lint**

Run:

```bash
pnpm --dir apps/web lint
```

Expected: exits successfully.

- [ ] **Step 2: Run tests**

Run:

```bash
pnpm --dir apps/web test
```

Expected: exits successfully.

- [ ] **Step 3: Run production build**

Run:

```bash
pnpm --dir apps/web build
```

Expected: exits successfully and keeps `/showcase/` available as a public static path.

## Self-Review

- Spec coverage: the plan creates the requested standalone static site, uses current web styles, includes all pipeline sections, and preserves the dashboard.
- Placeholder scan: no TBD/TODO placeholders are present.
- Type consistency: no TypeScript types or runtime interfaces are introduced.
