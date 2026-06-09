# Copilot Instructions for moodswingsdata

## Commands

- **Run any tool**: `uv run ms <subcommand>` (or `uv run moodswings <subcommand>`)
- **Install dependencies**: `uv sync`
- **Run Python**: `uv run python` (never use bare `python3`)
- **Run tests**: `uv run pytest`
- **Run a single test file**: `uv run pytest tests/test_extract.py`
- **Run a single test**: `uv run pytest tests/test_extract.py::TestParseHeading::test_standard_format`
- **Full pipeline build**: `./build-edition1.sh`

## Architecture

This is a data pipeline for the card game *Mood Swings*. Raw data (HTML snapshots, card images) flows through a series of CLI tools to produce structured YAML and JSON output.

The pipeline produces three data files: **editions** (set identity/metadata), **cards** (game-mechanical identity), and **printings** (edition-specific physical details like frame, artist, rarity). Each record gets a stable UUID5 ID generated from a fixed namespace in `extract.py`. Printings reference cards and editions by ID.

Data model types are documented in `src/moodswings/models.py` (Python `TypedDict`) and `types/moodswings.d.ts` (TypeScript interfaces). These are reference docs for data consumers, not enforced at runtime.

**Pipeline flow:**
1. `prepare-editions` — Generates stable IDs for editions and strips internal `data_sources`
2. `extract-cards` — Parses HTML card notes into cards YAML + printings YAML
3. `add-card` / `add-printing` — Add cards or printings from file or interactively
4. `download-images` — Fetches card images from URLs in printings YAML (skips existing)
5. `extract-from-images` — Uses OCR (Tesseract) and pixel analysis to fill in artist, dice color, reminder icon, and collector number
6. `to-json` — Converts YAML output files to JSON
7. `review-html` — Generates a static HTML page for human review of the output

## Conventions

- Each pipeline tool is a Click command in its own module under `src/moodswings/`, registered in `cli.py`.
- The entry point is a Click group (`main`) exported from `__init__.py`.
- Pipeline tools do not overwrite their inputs — they write to a specified output path.
- Card images are stored in `inputs/sets/<set_dir>/card_images/` and are not committed to git.
- YAML output uses `sort_keys=False, allow_unicode=True, default_flow_style=False`.
- External tool dependency: Tesseract OCR must be installed on the system for `extract-from-images`.
- When adding or updating a tool, make sure to update README.md.
