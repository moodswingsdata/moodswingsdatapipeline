# moodswingsdata

A project to make Mood Swings data available programmatically.

## Environment Setup

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (for image analysis)

### Install Tesseract

On macOS:
```bash
brew install tesseract
```

On Ubuntu/Debian:
```bash
sudo apt install tesseract-ocr
```

### Install Python dependencies

```bash
uv sync
```

## Tools

All tools are run via `uv run ms <subcommand>`.

### `prepare-editions`

Read the raw editions YAML, generate stable IDs, and produce the output editions
file (stripping pipeline-internal `data_sources`).

```bash
uv run ms prepare-editions inputs/editions.yaml -o out/editions.yaml
```

### `extract-cards`

Parse the raw HTML card notes file and output structured YAML. Produces two
files: a cards file (abstract card data) and a printings file (edition-specific
data). Each card and printing share a stable `id` (UUID5). Requires a prepared
editions file and the set code for the edition being extracted.

```bash
uv run ms extract-cards inputs/sets/msw-edition1/mood-swings-card-notes.html -o out/cards.yaml -p out/printings.yaml --editions out/editions.yaml --set-code MSW
```

### `download-images`

Download card images from URLs in the printings YAML file. Images are saved as
`{index}_{name}.{ext}` where the index is the printing's position in the YAML
list. This ensures each printing gets a unique file, even when two printings
share the same card name (e.g. Love at different collector numbers).

```bash
uv run ms download-images out/cards.yaml out/printings.yaml --output-dir inputs/sets/msw-edition1/card_images
```

After adding new printings with `merge-printings`, re-run `download-images` against
the same output directory — existing images are skipped and only the new
printings are fetched:

```bash
uv run ms merge-printings out/printings.yaml inputs/sets/msw-edition1/love-premium.yaml --cards out/cards.yaml --editions out/editions.yaml -o out/printings.yaml
uv run ms download-images out/cards.yaml out/printings.yaml --output-dir inputs/sets/msw-edition1/card_images
```

### `extract-from-images`

Extract artist, dice color, reminder icon, and collector number from card images
using OCR and pixel analysis. Requires Tesseract to be installed. Operates on
the printings file (uses the cards file for name lookup).

```bash
uv run ms extract-from-images out/cards.yaml out/printings.yaml inputs/sets/msw-edition1/card_images -o out/printings_enriched.yaml --editions out/editions.yaml
```

Artist names are fuzzy-matched against `inputs/artists.txt` (the default
lookup database). If an OCR result doesn't match any known name, it's appended
to the file with a leading `*`. Review the file, correct starred entries,
remove the `*`, and re-run.

### `review-html`

Put card images side-by-side with extracted data for human review. Supports
client-side sorting by name, collector number, color, frame, rarity, reminder
icon, dice value, secondary dice value, and treatment.

Printings without a matching image file display `inputs/missing.png` as a
fallback (auto-detected if present, or specify with `--missing`).

```bash
uv run ms review-html out/cards.yaml out/printings_enriched.yaml -o review.html --image-dir inputs/sets/msw-edition1/card_images
```

Errata baked into the data appear below the affected card (collapsed by
default). Card errata are read from `card.errata`; printing errata from
`printing.errata`, with the as-printed text shown from `printing.printed_rules_text`:

```bash
uv run ms review-html out/cards.yaml out/printings_enriched.yaml -o review.html --image-dir inputs/sets/msw-edition1/card_images
```

The errata details section (collapsed) shows the as-printed value alongside the
corrected oracle value and the note. The data is read straight from the baked
output — no separate errata files are passed. See [`apply-errata`](#apply-errata)
for how errata get into the data.

### `apply-errata`

Bake errata corrections into the cards and printings YAML files. Used by the
build so corrections reach the shipped output, not just the review page. A single
errata file is keyed by **either** `card_id` **or** `printing_id` (the two keys
may not be mixed in one file).

```bash
uv run ms apply-errata out/cards.yaml out/printings.yaml inputs/sets/msw-edition1/printings-errata.yaml --cards-out out/cards.yaml --printings-out out/printings.yaml
```

Errata is fundamentally a printing-side concept: a printing's as-printed text
differs from the card's canonical (oracle) text. A **printing-keyed** entry
preserves the original printed text on the printing (`printed_rules_text`),
writes the corrected oracle value to the referenced card, and records an `errata`
marker (which fields changed plus a note) on the printing. A **card-keyed** entry
corrects the card's oracle field directly and records the marker on the card.

Errata YAML format (printing example):
```yaml
- printing_id: "83974c7d-6793-..."
  rules_text:
    as_printed: "...gives it to you..."
    corrected: "...give it to you..."
    note: "Typo in the printed card."
```

Each entry replaces the oracle field with the `corrected` value and stores the
`errata` marker so downstream consumers can choose how to display the change. The
`as_printed` value is compared against the current data (ignoring whitespace
wrapping); a mismatch emits a warning and skips that field, so errata that have
drifted out of sync with the data are caught rather than silently applied.
Re-running is idempotent.

### `lint`

Check output YAML files for common issues: duplicate IDs, duplicate names,
and sort order (cards sorted by name, printings by collector number).

```bash
uv run ms lint --editions out/editions.yaml --cards out/cards.yaml --printings out/printings.yaml
```

Exits with code 1 if any issues are found.

### `merge-cards`

Merge two or more cards YAML files into a single output. Cards are deduplicated
by ID (first occurrence wins) and sorted by name.

```bash
uv run ms merge-cards out/cards.yaml inputs/sets/msw-edition1/hurt-feelings.yaml -o out/cards.yaml
```

### `create-card`

Create a card interactively and write it to a YAML file. If the file exists,
the new card is appended (keeping cards sorted by name). If it doesn't exist,
it is created.

```bash
uv run ms create-card inputs/sets/msw-edition1/hurt-feelings.yaml
```

After creating a card, you'll be reminded to create a printing for it to appear
in a set.

### `merge-printings`

Merge two or more printings YAML files into a single output. Printings are
deduplicated by ID (first occurrence wins) and sorted by collector number.
Input files may use `name`/`set_code` (resolved automatically) or
already-resolved `card_id`/`edition_id`.

```bash
uv run ms merge-printings out/printings.yaml inputs/sets/msw-edition1/love-premium.yaml --cards out/cards.yaml --editions out/editions.yaml -o out/printings.yaml
```

Can also point at a directory of YAML files as one of the inputs.

### `create-printing`

Create a printing interactively and write it to a YAML file. If the file exists,
the new printing is appended (keeping printings sorted by collector number).

```bash
uv run ms create-printing inputs/sets/msw-edition1/love-premium.yaml --cards out/cards.yaml --editions out/editions.yaml --card-name "Love"
```

### `write-meta`

Write a `meta.yaml` recording the current schema version and a SHA256 hash for
each output file. This is the final step of a build and lets downstream
consumers detect schema changes and verify file integrity.

```bash
uv run ms write-meta out/editions.yaml out/cards.yaml out/printings.yaml out/editions.json out/cards.json out/printings.json -o out/meta.yaml
```

The schema version comes from `SCHEMA_VERSION` in `src/moodswings/models.py`
(mirrored in `types/moodswings.d.ts`).

## Data Format

The pipeline produces three YAML files: **editions** (set identity and metadata),
**cards** (game-mechanical identity), and **printings** (edition-specific physical
details). Printings reference their edition via `edition_id`. Type stubs
documenting these shapes are available in:

- **Python**: `src/moodswings/models.py` — `TypedDict` classes (`Card`, `Edition`, `Printing`)
- **TypeScript**: `types/moodswings.d.ts` — interfaces (`Card`, `Edition`, `Printing`)

These are reference documentation for consumers of the data; they are not
enforced at runtime by the pipeline.

Cards carry the **oracle** (canonical) text in `rules_text`. A printing's
`printed_rules_text` holds the text physically printed on that card *only when it
differs* from the card's oracle text (otherwise `null`); this is how errata are
represented in the data. Both cards and printings have an optional `errata`
marker recording which fields were corrected and a note, so downstream apps can
choose how to surface the change (see [`apply-errata`](#apply-errata)).

The schema is versioned via `SCHEMA_VERSION` in both stub files. A build also
emits `meta.yaml`/`meta.json` recording that version alongside SHA256 hashes of
every output file (see [`write-meta`](#write-meta)).

## Tests

Run the test suite with:

```bash
uv run pytest
```

## Fan content

MoodSwingsData is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.
