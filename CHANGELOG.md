# Schema Changelog

## Dev
- Renamed `Card.rulings_text` to `Card.notes` in `models.py` and `types/moodswings.d.ts`.
- Added `Errata` type (`fields`, `note`) to `models.py` and `types/moodswings.d.ts`.
- Added optional `errata` marker to `Card` and `Printing` to flag corrected fields for downstream consumers.
- Added `printed_rules_text` to `Printing`: the as-printed text when it differs from the card's oracle `rules_text` (null when identical). `Card.rules_text` is now documented as the canonical oracle value.

## 0.9.0
- First true "versioned" schema. Everything that came before was practice.
- Added `SCHEMA_VERSION` constant to `models.py` and `types/moodswings.d.ts`.
- Builds now emit `meta.yaml`/`meta.json` recording the schema version and SHA256 hashes of every output file.
