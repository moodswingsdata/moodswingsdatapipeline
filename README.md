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

### `extract-cards`

Parse the raw HTML card notes file and output structured YAML. Produces two
files: a cards file (abstract card data) and a printings file (edition-specific
data). Each card and printing share a stable `id` (UUID5).

```bash
uv run ms extract-cards raw_data/msw-edition1/mood-swings-card-notes.html -o out/cards.yaml -p out/printings.yaml
```

### `download-images`

Download card images from URLs in the printings YAML file.

```bash
uv run ms download-images out/printings.yaml --output-dir raw_data/card_images/2026-06-02
```

### `extract-from-images`

Extract artist, dice color, reminder icon, and collector number from card images
using OCR and pixel analysis. Requires Tesseract to be installed. Operates on
the printings file (uses the cards file for name lookup).

```bash
uv run ms extract-from-images out/cards.yaml out/printings.yaml raw_data/card_images/2026-06-02 -o out/printings_enriched.yaml
```

Artist names are fuzzy-matched against `raw_data/artists.txt` (the default
lookup database). If an OCR result doesn't match any known name, it's appended
to the file with a leading `*`. Review the file, correct starred entries,
remove the `*`, and re-run.

### `review-html`

Put card images side-by-side with extracted data for human review. Supports
client-side sorting by name, collector number, color, frame, rarity, reminder
icon, dice value, secondary dice value, and treatment.

```bash
uv run ms review-html out/cards.yaml out/printings_enriched.yaml -o review.html --image-dir raw_data/card_images/2026-06-02
```

Optionally include an errata file to show corrections below affected cards
(collapsed by default):

```bash
uv run ms review-html out/cards.yaml out/printings_enriched.yaml -o review.html --image-dir raw_data/card_images/2026-06-02 --errata raw_data/errata.yaml
```

Errata YAML format:
```yaml
- printing_id: "9d9f6896-b0f7-..."
  rules_text:
    as_printed: "Reroll tis card when any player rolls doubles."
    corrected: "Reroll this card when any player rolls doubles."
    note: "Typo: 'tis' should be 'this'"
```

The `corrected` value overrides the displayed field in the card data table.
The errata details section (collapsed) shows both the as-printed and corrected
versions alongside the note.

### `add-printing`

Add printing(s) for existing cards. Supports two modes:

**From file** (for repeatable/automated additions):
```bash
uv run ms add-printing out/cards.yaml out/printings.yaml --from raw_data/extra_printings.yaml
```

Each entry in the YAML file needs a `card_name` field plus any printing fields
(frame, rarity, collector_number, set_code, edition_name, treatment, artist, etc.).
Can also point `--from` at a directory of YAML files.

**Interactive** (prompts for each field):
```bash
uv run ms add-printing out/cards.yaml out/printings.yaml --card-name "Love"
```

## Data Format

The pipeline produces two YAML files: **cards** (game-mechanical identity) and
**printings** (edition-specific physical details). Type stubs documenting
these shapes are available in:

- **Python**: `src/moodswings/models.py` — `TypedDict` classes (`Card`, `Printing`)
- **TypeScript**: `types/moodswings.d.ts` — interfaces (`Card`, `Printing`)

These are reference documentation for consumers of the data; they are not
enforced at runtime by the pipeline.

## Fan content

MoodSwingsData is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.
