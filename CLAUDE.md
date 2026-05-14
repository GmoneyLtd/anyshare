# OpenWolf

@.wolf/OPENWOLF.md

This project uses OpenWolf for context management. Read and follow .wolf/OPENWOLF.md every session. Check .wolf/cerebrum.md before generating code. Check .wolf/anatomy.md before reading files.


# Claude Global Preferences for Python Projects (uv + ruff)

## 1. My Development Environment
- I use **macOS** with **zsh**.
- My Python projects use **uv** to manage virtual environments and dependencies.
- I use **ruff** for:
  - formatting (`ruff format`)
  - linting (`ruff check`)
  - import sorting (`ruff check --select I`)
- I prefer **single-file, reproducible, deterministic instructions**.
- Avoid ambiguity. Always provide explicit commands, paths, and file structures.

## 2. Project Structure Preferences
When generating or modifying Python projects, follow this structure:

- Tests must live under `tests/`.
- No top-level `.py` files except entrypoints explicitly requested.

## 3. Dependency Management (uv)
When suggesting commands, always use **uv**, not pip or venv.

Examples:
- Create project: `uv init <project>`
- Add dependency: `uv add <package>`
- Add dev dependency: `uv add --dev <package>`
- Run script: `uv run <script.py>`
- Run tests: `uv run pytest`

Never suggest:
- `pip install`
- `python -m venv`
- `requirements.txt`

## 4. Code Style (ruff)
All code must follow **ruff** rules:

- Use `ruff format` for formatting.
- Use `ruff check` for linting.
- Use `ruff check --fix` when auto-fixes are appropriate.
- Use `ruff` import sorting rules (PEP8 + alphabetical + grouped).

When generating code:
- Ensure imports are sorted.
- Ensure formatting matches ruff’s default style.
- Avoid unused imports.
- Avoid wildcard imports.
- Use type hints everywhere.

## 5. Python Coding Preferences
- Use Python 3.13.13 syntax.
- Prefer dataclasses when defining structured data.
- Prefer pathlib over os.path.
- Prefer f-strings.
- Avoid overly clever code; prioritize readability.
- Always include docstrings for public functions and classes.
- Use explicit return types.

## 6. Testing Preferences
- Use pytest.
- Test files must be named `test_*.py`.
- Prefer small, isolated tests.
- Use fixtures when appropriate.
- Avoid mocking unless necessary.

## 7. Architecture

**Stack**: Bottle (web), Beaker (sessions), gevent (WSGI + concurrency), APScheduler (cron jobs), SQLite (storage), Loguru (logging).
**front-end**: HTML+CSS+JS

## 7. Documentation Preferences
- Provide clear, structured explanations.
- Include code blocks with correct syntax highlighting.
- When generating README sections, include:
  - Installation (uv)
  - Usage
  - Development workflow
  - Testing instructions
  - Formatting/linting instructions

## 8. Communication Style
- Be direct, structured, and scenario-specific.
- Avoid generic advice.
- Provide complete, reproducible steps.
- When giving commands, assume zsh on macOS.
- When multiple options exist, list them and recommend the best one.

## 9. Safety & Reliability
- Never modify or delete files unless explicitly instructed.
- Always confirm before generating destructive commands.
- Prefer additive changes over replacements unless requested.

## 10. When Working Inside a Python Project
When I ask for:
- “refactor this”
- “add a feature”
- “fix this bug”
- “generate a module”
- “create a script”

You should:
1. Show the updated file(s).
2. Provide the exact path of each file.
3. Ensure code is ruff-compliant.
4. Ensure imports are correct.
5. Ensure the project remains uv-compatible.

## 11. When Unsure
If any detail is ambiguous:
- Ask a clarifying question.
- Or propose 2–3 valid interpretations and let me choose.

