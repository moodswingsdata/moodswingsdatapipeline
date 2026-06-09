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

Optionally include an errata file to show corrections below affected cards
(collapsed by default):

```bash
uv run ms review-html out/cards.yaml out/printings_enriched.yaml -o review.html --image-dir inputs/sets/msw-edition1/card_images --errata inputs/errata.yaml
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

## Data Format

The pipeline produces three YAML files: **editions** (set identity and metadata),
**cards** (game-mechanical identity), and **printings** (edition-specific physical
details). Printings reference their edition via `edition_id`. Type stubs
documenting these shapes are available in:

- **Python**: `src/moodswings/models.py` — `TypedDict` classes (`Card`, `Edition`, `Printing`)
- **TypeScript**: `types/moodswings.d.ts` — interfaces (`Card`, `Edition`, `Printing`)

These are reference documentation for consumers of the data; they are not
enforced at runtime by the pipeline.

## Tests

Run the test suite with:

```bash
uv run pytest
```

## Fan content

MoodSwingsData is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.
