# Phase 0.3 Repository Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the current directory as the version-controlled BosesPH Toolkit repository with its planned directory layout, core documentation, Apache 2.0 license, and safe ignore rules.

**Architecture:** This phase creates repository boundaries only. Placeholder files preserve empty directories, while root documentation and ignore rules define how later Next.js, FastAPI, data, and ML work will enter the repository without committing secrets or generated artifacts.

**Tech Stack:** Git, Markdown, Apache License 2.0

---

## File Map

- Create `.gitignore`: repository-wide exclusions for local, generated, sensitive, and large artifacts.
- Create `README.md`: project summary, planned architecture, layout, and current status.
- Create `LICENSE`: canonical Apache License 2.0 text.
- Create `.gitkeep` files under planned empty directories so Git tracks the structure.
- Preserve `AGENTS.md`, `Requirements.md`, and `Tasks.md` unchanged.

### Task 1: Add Repository Ignore Policy

**Files:**
- Create: `.gitignore`

- [x] **Step 1: Create `.gitignore`**

Add explicit rules for macOS/editor state, environment files, Node/Python artifacts, local databases, generated outputs, datasets, model weights, logs, caches, and incomplete browser downloads. Keep `.gitkeep` exceptions for `sample_data/` and `outputs/`.

- [x] **Step 2: Verify sensitive and generated files are ignored**

Run:

```bash
git check-ignore -v "Unconfirmed 324162.crdownload"
git check-ignore -v outputs/example.zip
git check-ignore -v sample_data/private.wav
```

Expected: each path is matched by `.gitignore`.

- [x] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: add repository ignore policy"
```

### Task 2: Create Planned Directory Structure

**Files:**
- Create: `apps/web/.gitkeep`
- Create: `apps/api/.gitkeep`
- Create: `ml/data/.gitkeep`
- Create: `ml/training/.gitkeep`
- Create: `ml/evaluation/.gitkeep`
- Create: `sample_data/.gitkeep`
- Create: `scripts/.gitkeep`
- Create: `outputs/.gitkeep`

- [x] **Step 1: Add placeholder files**

Create each listed `.gitkeep` as an empty file. The existing `docs/` directory already contains the design and plan documents and needs no placeholder.

- [x] **Step 2: Verify every planned directory exists**

Run:

```bash
test -d apps/web
test -d apps/api
test -d ml/data
test -d ml/training
test -d ml/evaluation
test -d docs
test -d sample_data
test -d scripts
test -d outputs
```

Expected: exit status 0.

- [x] **Step 3: Commit**

```bash
git add apps ml sample_data scripts outputs
git commit -m "chore: create initial repository structure"
```

### Task 3: Add License and Project README

**Files:**
- Create: `LICENSE`
- Create: `README.md`

- [x] **Step 1: Add the license**

Create `LICENSE` with the canonical Apache License, Version 2.0 text published at `https://www.apache.org/licenses/LICENSE-2.0`.

- [x] **Step 2: Add the README**

Document:

- BosesPH Toolkit as an open-source pipeline for Philippine-language speech resources.
- Planned Next.js dashboard, FastAPI API, and Python ML pipeline.
- The repository directory map.
- Current status: repository foundation only; applications and dependencies are not yet scaffolded.
- Links to `Requirements.md`, `Tasks.md`, and `AGENTS.md`.
- Apache 2.0 licensing.

- [x] **Step 3: Verify documentation**

Run:

```bash
grep -F "Apache License" LICENSE
grep -F "BosesPH Toolkit" README.md
grep -F "repository foundation" README.md
```

Expected: each command prints a matching line.

- [x] **Step 4: Commit**

```bash
git add LICENSE README.md
git commit -m "docs: add project overview and license"
```

### Task 4: Track Existing Project Guidance and Verify Phase 0.3

**Files:**
- Track unchanged: `AGENTS.md`
- Track unchanged: `Requirements.md`
- Track unchanged: `Tasks.md`
- Track: `docs/superpowers/plans/2026-06-25-phase-0-3-repository-foundation.md`

- [x] **Step 1: Add existing project documents and this plan**

```bash
git add AGENTS.md Requirements.md Tasks.md docs/superpowers/plans/2026-06-25-phase-0-3-repository-foundation.md
git commit -m "docs: add project requirements and contributor guidance"
```

- [x] **Step 2: Run final repository checks**

```bash
git rev-parse --is-inside-work-tree
git branch --show-current
git status --short
git check-ignore "Unconfirmed 324162.crdownload"
find apps ml docs sample_data scripts outputs -maxdepth 2 -type d | sort
```

Expected:

- Git reports `true`.
- The current branch is `main`.
- `git status --short` is empty.
- The incomplete download is ignored.
- All planned directories appear.

- [x] **Step 3: Confirm scope stayed within Phase 0.3**

Run:

```bash
test ! -e package.json
test ! -e pyproject.toml
test ! -e requirements.txt
```

Expected: exit status 0; no application dependencies were scaffolded.
