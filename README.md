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

Parse the raw HTML card notes file and output structured YAML.

```bash
uv run ms extract-cards raw_data/2026-06-02-mood-swings-card-notes.html -o out/edition1.yaml
```

### `download-images`

Download card images from URLs in the YAML file.

```bash
uv run ms download-images out/edition1.yaml --output-dir raw_data/card_images/2026-06-02
```

### `extract-from-images`

Extract artist, dice color, and reminder icon from card images using OCR and
pixel analysis. Requires Tesseract to be installed.

```bash
uv run ms extract-from-images out/edition1.yaml raw_data/card_images/2026-06-02 -o out/edition1_enriched.yaml
```

**Note:** Artist names are extracted via OCR and may contain casing inconsistencies
or minor errors that require manual review.
