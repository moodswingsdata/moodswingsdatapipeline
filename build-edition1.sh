#!/usr/bin/env bash
set -euo pipefail

# Build Edition 1 YAML files from raw data.
# Assumes raw_data/ exists (except raw_data/card_images/ which may be downloaded).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

INPUT_HTML="raw_data/msw-edition1/mood-swings-card-notes.html"
IMAGE_DIR="raw_data/card_images/2026-06-02"
LOVE_PREMIUM="raw_data/msw-edition1/love-premium.yaml"
ERRATA="raw_data/msw-edition1/instability-errata.yaml"

CARDS_YAML="out/cards.yaml"
PRINTINGS_YAML="out/printings_partial.yaml"
PRINTINGS_ENRICHED="out/printings.yaml"
REVIEW_HTML="out/review.html"

mkdir -p out

# Step 1: Extract cards from HTML
echo "==> Extracting cards from HTML..."
uv run ms extract-cards "$INPUT_HTML" \
    -o "$CARDS_YAML" \
    -p "$PRINTINGS_YAML"

# Step 2: Download card images if not already present
if [ -d "$IMAGE_DIR" ] && [ "$(ls -A "$IMAGE_DIR" 2>/dev/null)" ]; then
    echo "==> Card images already exist in $IMAGE_DIR, skipping download."
else
    echo "==> Downloading card images to $IMAGE_DIR..."
    uv run ms download-images "$CARDS_YAML" "$PRINTINGS_YAML" \
        --output-dir "$IMAGE_DIR"
fi

# Step 3: Extract metadata from images (artist, dice color, reminder icon)
echo "==> Extracting metadata from card images..."
uv run ms extract-from-images "$CARDS_YAML" "$PRINTINGS_YAML" "$IMAGE_DIR" \
    -o "$PRINTINGS_ENRICHED"

# Step 4: Add the Love premium card printing
echo "==> Adding Love premium printing..."
uv run ms add-printing "$CARDS_YAML" "$PRINTINGS_ENRICHED" \
    --from "$LOVE_PREMIUM"

# Step 5: Generate review HTML with errata
echo "==> Generating review HTML..."
uv run ms review-html "$CARDS_YAML" "$PRINTINGS_ENRICHED" \
    -o "$REVIEW_HTML" \
    --image-dir "$IMAGE_DIR" \
    --errata "$ERRATA"

echo "==> Done! Review at $REVIEW_HTML"
