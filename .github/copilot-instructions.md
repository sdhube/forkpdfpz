# Copilot instructions for this repo

Keep responses short and scoped to the file(s) under discussion — do not
restate unrelated parts of the codebase.

- Language/stack: Python 3.x
- Package manager: pip / uv (confirm which — update this line, it changes
  the install/lock commands Copilot will suggest)
- Build: n/a (pure Python) — confirm if there's a packaging step (setup.py,
  pyproject.toml build backend)
- Test: `pytest`
- Lint/format: `ruff check .` (repo uses `.ruff_cache/` per .gitignore)

## Extended token-saving config

### Lock file & dependencies
- **Strategy:** TBD (no lock file committed yet)
- **Regenerate:** `uv lock` or `pip freeze > requirements.txt` — Copilot will use
  this command when suggesting deps/updates, avoiding needless explanations.
- **Protected:** `*requirements*.txt`, `uv.lock`, `pdm.lock`, `poetry.lock` — do not
  hand-edit; regenerate only.

### Module structure
- **Main package:** `src/pdf_metadata/` or repo root (confirm when adding code)
- Copilot will import/reference paths accordingly, avoiding guesses.

### Type checking & static analysis
- **Mypy:** Not yet enabled (add if adopting type hints)
- **Pyright/Pylance:** No config yet
- **Ruff rules:** Extend ruff config in pyproject.toml or ruff.toml as needed.

### Pre-commit hooks
- None configured yet. If added, document the exact commands so Copilot aligns.

### Common patterns
- Prefer functions over classes for simple utilities.
- Avoid external dependencies unless necessary.

## Conventions
- Match existing code style; don't reformat unrelated lines.
- Prefer editing existing modules over creating new files unless asked.
- No new dependencies without calling it out first.

## Do not touch
- Anything under `/dist`, `/build`, `/.venv`, `__pycache__/` — build
  artifacts, not source.
- Lock files — regenerate via the package manager, don't hand-edit.

## Reusable prompts
This repo has task-specific prompt files in `.github/prompts/*.prompt.md`.
Invoke them with `/name` in Copilot Chat (VS Code, Visual Studio, or
JetBrains only — not Copilot CLI) instead of re-typing the same
instructions each time:
- `/add-feature` — new class/function, no test scaffolding
- `/refactor-python` — refactor existing code, diff-only output
- `/api-design` — REST endpoint design/review
- `/explain-code` — terse bug/refactor explanations

<!--
  Why this file is short: every line here is added to EVERY Copilot Chat
  and code-review request in this repo. It doesn't reduce Copilot's
  context window usage — it reduces wasted back-and-forth by getting
  the stack/conventions right the first time. Padding this file with
  prose does not "save tokens"; it costs them on every single call.
-->
