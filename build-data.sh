#!/usr/bin/env bash
set -euo pipefail

# Build YAML files for a single edition from raw data.
# Reads input paths from inputs/editions.yaml based on set code.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SET_CODES=('msw')

EDITIONS_INPUT="inputs/editions.yaml"
OUT_BASE="out/"
EDITIONS_YAML="${OUT_BASE}editions.yaml"
CARDS_YAML="${OUT_BASE}cards.yaml"
PRINTINGS_YAML="${OUT_BASE}printings.yaml"

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
elif field == 'card_errata':
    for item in ds:
        if 'card_errata' in item:
            for e in item['card_errata']:
                print(e)
            sys.exit(0)
elif field == 'printing_errata':
    for item in ds:
        if 'printing_errata' in item:
            for e in item['printing_errata']:
                print(e)
            sys.exit(0)
"
}

mkdir -p "${OUT_BASE}"

# Step 1: Prepare editions
echo "==> Preparing editions..."
uv run ms prepare-editions "$EDITIONS_INPUT" -o "$EDITIONS_YAML"

# Step 2: Build up card file
echo "==> Combining cards..."
touch "${CARDS_YAML}"
for SET_CODE in "${SET_CODES[@]}"; do
  INPUT_HTML="$(read_edition_field core_file)"
  SET_DIR="$(dirname $INPUT_HTML)"
  SET_CARDS="inputs/${SET_DIR}/cards_${SET_CODE}.yaml"
  echo "... $SET_CODE: ${SET_CARDS}"
  uv run ms merge-cards "$CARDS_YAML" "$SET_CARDS" \
    -o "$CARDS_YAML"
done

# Step 3: Build up printings file
echo "==> Combining printings..."
touch "${PRINTINGS_YAML}"
for SET_CODE in "${SET_CODES[@]}"; do
  INPUT_HTML="$(read_edition_field core_file)"
  SET_DIR="$(dirname $INPUT_HTML)"
  SET_PRINTINGS="inputs/${SET_DIR}/printings_${SET_CODE}.yaml"
  echo "... $SET_CODE: ${SET_PRINTINGS}"
  uv run ms merge-printings "$PRINTINGS_YAML" "$SET_PRINTINGS" \
    --cards "$CARDS_YAML" \
    --editions "$EDITIONS_YAML" \
    -o "$PRINTINGS_YAML"
done

# Step 4: Apply errata into cards and printings
echo "==> Applying errata..."
for SET_CODE in "${SET_CODES[@]}"; do
  INPUT_HTML="$(read_edition_field core_file)"
  SET_DIR="$(dirname $INPUT_HTML)"

  while IFS= read -r ERRATA; do
    [ -z "$ERRATA" ] && continue
    echo "... $SET_CODE: inputs/${ERRATA}"
    uv run ms apply-errata "$CARDS_YAML" "$PRINTINGS_YAML" "inputs/${ERRATA}" \
      --cards-out "$CARDS_YAML" --printings-out "$PRINTINGS_YAML"
  done < <(read_edition_field card_errata; read_edition_field printing_errata)
done

# Step 5: Lint before proceeding
echo "==> Linting output files..."
uv run ms lint --editions "$EDITIONS_YAML" --cards "$CARDS_YAML" --printings "$PRINTINGS_YAML"

# Step 6: Make JSON versions
echo "==> Converting YAML to JSON..."
uv run ms to-json "$EDITIONS_YAML" -o "${OUT_BASE}editions.json"
uv run ms to-json "$CARDS_YAML" -o "${OUT_BASE}cards.json"
uv run ms to-json "$PRINTINGS_YAML" -o "${OUT_BASE}printings.json"

# Step 7: Write meta file (schema version + output file hashes)
echo "==> Writing meta file..."
META_YAML="${OUT_BASE}meta.yaml"
uv run ms write-meta \
  "$EDITIONS_YAML" "$CARDS_YAML" "$PRINTINGS_YAML" \
  "${OUT_BASE}editions.json" "${OUT_BASE}cards.json" "${OUT_BASE}printings.json" \
  -o "$META_YAML"
uv run ms to-json "$META_YAML" -o "${OUT_BASE}meta.json"

echo "==> Done!"
