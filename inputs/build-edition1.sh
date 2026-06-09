#!/usr/bin/env bash
set -euo pipefail

# Build YAML files for a single edition from raw data.
# Reads input paths from editions.yaml based on set code.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SET_CODE="msw"

EDITIONS_INPUT="editions.yaml"
EXTRA_CARDS_INPUT="game/hurt-feelings-card.yaml"
OUT_BASE="../out/"
EDITIONS_YAML="${OUT_BASE}editions.yaml"
CARDS_YAML="${OUT_BASE}cards.yaml"
PRINTINGS_YAML="${OUT_BASE}printings_partial.yaml"
PRINTINGS_ENRICHED="${OUT_BASE}printings.yaml"
REVIEW_HTML="${OUT_BASE}review.html"

# Extract data source paths from editions.yaml for this set code
read_edition_field() {
    uv run python -c "
import yaml, sys
with open('$EDITIONS_INPUT') as f:
    editions = yaml.safe_load(f)
edition = next((e for e in editions if e['set_code'] == '$SET_CODE'), None)
if edition is None:
    print(f'Error: set_code $SET_CODE not found', file=sys.stderr)
    sys.exit(1)
field = '$1'
ds = edition.get('data_sources', [])
if field == 'core_file':
    for item in ds:
        if 'core_file' in item:
            print(item['core_file'])
            sys.exit(0)
elif field == 'date':
    for item in ds:
        if 'date' in item:
            print(item['date'])
            sys.exit(0)
elif field == 'additional_printings':
    for item in ds:
        if 'additional_printings' in item:
            for p in item['additional_printings']:
                print(p)
            sys.exit(0)
elif field == 'errata':
    for item in ds:
        if 'errata' in item:
            for e in item['errata']:
                print(e)
            sys.exit(0)
"
}

INPUT_HTML="$(read_edition_field core_file)"
IMAGE_DIR="sets/msw-edition1/card_images"

mkdir -p "${OUT_BASE}"

# Step 1: Prepare editions
echo "==> Preparing editions..."
uv run ms prepare-editions "$EDITIONS_INPUT" -o "$EDITIONS_YAML"

# Step 2: Extract cards from HTML
echo "==> Extracting cards from HTML..."
uv run ms extract-cards "$INPUT_HTML" \
    -o "$CARDS_YAML" \
    -p "$PRINTINGS_YAML" \
    --editions "$EDITIONS_YAML" \
    --set-code "$SET_CODE"

# Step 3: Merge in the Hurt Feelings token
echo "==> Merging additional known cards..."
uv run ms merge-cards "$CARDS_YAML" "$EXTRA_CARDS_INPUT" \
    -o "$CARDS_YAML"

# Step 4: Download card images if not already present
if [ -d "$IMAGE_DIR" ] && [ "$(ls -A "$IMAGE_DIR" 2>/dev/null)" ]; then
    echo "==> Card images already exist in $IMAGE_DIR, skipping download."
else
    echo "==> Downloading card images to $IMAGE_DIR..."
    uv run ms download-images "$CARDS_YAML" "$PRINTINGS_YAML" \
        --output-dir "$IMAGE_DIR"
fi

# Step 5: Extract metadata from images (artist, dice color, reminder icon)
echo "==> Extracting metadata from card images..."
uv run ms extract-from-images "$CARDS_YAML" "$PRINTINGS_YAML" "$IMAGE_DIR" \
    -o "$PRINTINGS_ENRICHED" \
    --editions "$EDITIONS_YAML"

# Step 6: Add additional printings
ADDITIONAL_PRINTINGS="$(read_edition_field additional_printings)"
if [ -n "$ADDITIONAL_PRINTINGS" ]; then
    while IFS= read -r printing_file; do
        echo "==> Merging printings from ${printing_file}..."
        uv run ms merge-printings "$PRINTINGS_ENRICHED" "${printing_file}" \
            --cards "$CARDS_YAML" \
            --editions "$EDITIONS_YAML" \
            -o "$PRINTINGS_ENRICHED"
    done <<< "$ADDITIONAL_PRINTINGS"
fi

# Step 7: Download card images for additional printings (rely on download-images to skip existing)
echo "==> Downloading additional card images to $IMAGE_DIR..."
uv run ms download-images "$CARDS_YAML" "$PRINTINGS_ENRICHED" \
    --output-dir "$IMAGE_DIR"

# Step 8: Make JSON versions
echo "==> Converting YAML to JSON..."
uv run ms to-json "$EDITIONS_YAML" -o "${OUT_BASE}editions.json"
uv run ms to-json "$CARDS_YAML" -o "${OUT_BASE}cards.json"
uv run ms to-json "$PRINTINGS_ENRICHED" -o "${OUT_BASE}printings.json"

# Step 9: Generate review HTML with errata
ERRATA_FILES="$(read_edition_field errata)"
ERRATA_ARGS=""
if [ -n "$ERRATA_FILES" ]; then
    while IFS= read -r errata_file; do
        ERRATA_ARGS="--errata ${errata_file}"
    done <<< "$ERRATA_FILES"
fi

echo "==> Generating review HTML..."
uv run ms review-html "$CARDS_YAML" "$PRINTINGS_ENRICHED" \
    -o "$REVIEW_HTML" \
    --editions "$EDITIONS_YAML" \
    --image-dir "$IMAGE_DIR" \
    $ERRATA_ARGS

echo "==> Done! Review at $REVIEW_HTML"
