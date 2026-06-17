"""Tests for the apply-fix command."""

import yaml
from pathlib import Path

import pytest
from click.testing import CliRunner

from moodswings.apply_fix import apply_fix, apply_fixes


class TestApplyFixes:
    def test_apply_fix_updates_old_to_new(self):
        data = [{"id": "card-1", "name": "Altruism", "color": ["White"]}]
        fixes = [{"id": "card-1", "field_name": "name", "old": "Altruism", "new": "Bravado"}]
        applied, skipped, warnings = apply_fixes(data, fixes, "id")
        assert applied == 1
        assert skipped == 0
        assert warnings == []
        assert data[0]["name"] == "Bravado"

    def test_skip_already_applied(self):
        data = [{"id": "card-1", "name": "Bravado"}]
        fixes = [{"id": "card-1", "field_name": "name", "old": "Altruism", "new": "Bravado"}]
        applied, skipped, warnings = apply_fixes(data, fixes, "id")
        assert applied == 0
        assert skipped == 1
        assert warnings == []
        assert data[0]["name"] == "Bravado"

    def test_warn_on_unexpected_value(self):
        data = [{"id": "card-1", "name": "Courage"}]
        fixes = [{"id": "card-1", "field_name": "name", "old": "Altruism", "new": "Bravado"}]
        applied, skipped, warnings = apply_fixes(data, fixes, "id")
        assert applied == 0
        assert skipped == 0
        assert len(warnings) == 1
        assert "Courage" in warnings[0]

    def test_warn_on_missing_record(self):
        data = [{"id": "card-1", "name": "Altruism"}]
        fixes = [{"id": "card-99", "field_name": "name", "old": "X", "new": "Y"}]
        applied, skipped, warnings = apply_fixes(data, fixes, "id")
        assert applied == 0
        assert len(warnings) == 1
        assert "card-99" in warnings[0]

    def test_multiple_fixes(self):
        data = [
            {"id": "c1", "name": "A", "color": ["White"]},
            {"id": "c2", "name": "B", "color": ["Blue"]},
        ]
        fixes = [
            {"id": "c1", "field_name": "name", "old": "A", "new": "Alpha"},
            {"id": "c2", "field_name": "color", "old": ["Blue"], "new": ["Black"]},
        ]
        applied, skipped, warnings = apply_fixes(data, fixes, "id")
        assert applied == 2
        assert data[0]["name"] == "Alpha"
        assert data[1]["color"] == ["Black"]


class TestApplyFixCLI:
    def test_card_fix_end_to_end(self, tmp_path: Path):
        cards = [
            {"id": "c1", "name": "Altruism", "color": ["White"]},
            {"id": "c2", "name": "Bravado", "color": ["Blue"]},
        ]
        fixes = [
            {"card_id": "c1", "field_name": "name", "old": "Altruism", "new": "Awe"},
        ]
        cards_file = tmp_path / "cards.yaml"
        fixes_file = tmp_path / "fixes.yaml"
        output_file = tmp_path / "out.yaml"

        cards_file.write_text(yaml.safe_dump(cards), encoding="utf-8")
        fixes_file.write_text(yaml.safe_dump(fixes), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(apply_fix, [
            str(cards_file), str(fixes_file), "-o", str(output_file),
        ])
        assert result.exit_code == 0
        assert "Applied 1 fix" in result.output

        out_data = yaml.safe_load(output_file.read_text(encoding="utf-8"))
        assert out_data[0]["name"] == "Awe"
        assert out_data[1]["name"] == "Bravado"

    def test_printing_fix_end_to_end(self, tmp_path: Path):
        printings = [
            {"id": "p1", "card_id": "c1", "artist": "Alice"},
        ]
        fixes = [
            {"printing_id": "p1", "field_name": "artist", "old": "Alice", "new": "Bob"},
        ]
        printings_file = tmp_path / "printings.yaml"
        fixes_file = tmp_path / "fixes.yaml"
        output_file = tmp_path / "out.yaml"

        printings_file.write_text(yaml.safe_dump(printings), encoding="utf-8")
        fixes_file.write_text(yaml.safe_dump(fixes), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(apply_fix, [
            str(printings_file), str(fixes_file), "-o", str(output_file),
        ])
        assert result.exit_code == 0
        out_data = yaml.safe_load(output_file.read_text(encoding="utf-8"))
        assert out_data[0]["artist"] == "Bob"

    def test_mixed_ids_rejected(self, tmp_path: Path):
        fixes = [
            {"card_id": "c1", "field_name": "name", "old": "A", "new": "B"},
            {"printing_id": "p1", "field_name": "artist", "old": "X", "new": "Y"},
        ]
        data_file = tmp_path / "data.yaml"
        fixes_file = tmp_path / "fixes.yaml"

        data_file.write_text(yaml.safe_dump([{"id": "c1", "name": "A"}]), encoding="utf-8")
        fixes_file.write_text(yaml.safe_dump(fixes), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(apply_fix, [
            str(data_file), str(fixes_file), "-o", str(tmp_path / "out.yaml"),
        ])
        assert result.exit_code != 0
        assert "mixes card_id and printing_id" in result.output

    def test_warnings_emitted(self, tmp_path: Path):
        cards = [{"id": "c1", "name": "Courage"}]
        fixes = [{"card_id": "c1", "field_name": "name", "old": "Altruism", "new": "Bravado"}]

        cards_file = tmp_path / "cards.yaml"
        fixes_file = tmp_path / "fixes.yaml"
        output_file = tmp_path / "out.yaml"

        cards_file.write_text(yaml.safe_dump(cards), encoding="utf-8")
        fixes_file.write_text(yaml.safe_dump(fixes), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(apply_fix, [
            str(cards_file), str(fixes_file), "-o", str(output_file),
        ])
        assert result.exit_code == 0
        assert "WARNING" in result.output
        assert "Courage" in result.output
