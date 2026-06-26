# Schema Changelog

## 0.9.0
- First true "versioned" schema. Everything that came before was practice.
- Added `SCHEMA_VERSION` constant to `models.py` and `types/moodswings.d.ts`.
- Builds now emit `meta.yaml`/`meta.json` recording the schema version and SHA256 hashes of every output file.
