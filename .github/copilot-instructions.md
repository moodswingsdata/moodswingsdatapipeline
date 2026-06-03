# Copilot Instructions for moodswingsdata

## Commands

- **Run any tool**: `uv run ms <subcommand>` (or `uv run moodswings <subcommand>`)
- **Install dependencies**: `uv sync`
- **Run Python**: `uv run python` (never use bare `python3`)

There are no tests or linters configured yet.

## Architecture

This is a data pipeline for the card game *Mood Swings*. Raw data (HTML snapshots, card images) flows through a series of CLI tools to produce structured YAML output.

**Pipeline flow:**
1. `extract-cards` — Parses HTML card notes into YAML with fields extractable from text
2. `download-images` — Fetches card images from URLs in the YAML
3. `extract-from-images` — Uses OCR (Tesseract) and pixel analysis to fill in artist, dice color, and reminder icon
4. `review-html` — Generates a static HTML page for human review of the output

**Key directories:**
- `src/moodswings/` — All Python source
- `raw_data/` — Input files (HTML snapshots, card images in `card_images/` which is gitignored)
- `out/` — Pipeline output YAML files

## Conventions

- Each pipeline tool is a Click command in its own module under `src/moodswings/`, registered in `cli.py`.
- The entry point is a Click group (`main`) exported from `__init__.py`.
- Pipeline tools do not overwrite their inputs — they write to a specified output path.
- Card images are stored in `raw_data/card_images/<date>/` and are not committed to git.
- YAML output uses `sort_keys=False, allow_unicode=True, default_flow_style=False`.
- External tool dependency: Tesseract OCR must be installed on the system for `extract-from-images`.
- When adding or updating a tool, make sure to update README.md.
