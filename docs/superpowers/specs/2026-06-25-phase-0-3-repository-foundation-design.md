# Phase 0.3 Repository Foundation Design

## Scope

Prepare the current `Asteria` directory as the BosesPH Toolkit repository. Phase 0.1 and Phase 0.2 are explicitly out of scope. This phase establishes project structure and repository policy without generating application code or installing dependencies.

## Repository Structure

Create and track the following directories:

```text
apps/
  web/
  api/
ml/
  data/
  training/
  evaluation/
docs/
sample_data/
scripts/
outputs/
```

Empty directories will contain `.gitkeep` files until implementation files replace them.

## Root Files

- `README.md` will summarize the toolkit, planned architecture, repository layout, and current setup status.
- `LICENSE` will contain the Apache License 2.0 text.
- `.gitignore` will exclude operating-system files, editor state, secrets, Python and Node artifacts, local databases, generated datasets, model weights, and incomplete browser downloads.
- Existing `AGENTS.md`, `Requirements.md`, and `Tasks.md` will remain unchanged.

## Version Control

Initialize a Git repository in the current directory. The large `Unconfirmed 324162.crdownload` file must remain on disk but be ignored and untracked. The initial repository content must not include generated output, private audio, secrets, or model artifacts.

## Verification

Completion requires:

1. Git recognizes the current directory as a work tree.
2. Every planned directory exists.
3. `README.md`, `LICENSE`, and `.gitignore` exist.
4. `LICENSE` identifies Apache License 2.0.
5. The incomplete download is ignored.
6. No application framework or dependency scaffold has been introduced.
