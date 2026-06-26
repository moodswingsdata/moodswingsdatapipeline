"""Tests for the apply-errata command."""

import yaml
from pathlib import Path

from click.testing import CliRunner

from moodswings.apply_errata import (
    apply_errata,
    apply_card_errata,
    apply_printing_errata,
)


class TestApplyCardErrata:
    def test_corrects_card_field_and_sets_marker(self):
        cards = [{"id": "c1", "rules_text": "old text"}]
        errata = [{"card_id": "c1", "rules_text": {
            "as_printed": "old text", "corrected": "new text", "note": "Fixed."}}]
        applied, skipped, warnings = apply_card_errata(cards, errata)
        assert applied == 1
        assert warnings == []
        assert cards[0]["rules_text"] == "new text"
        assert cards[0]["errata"] == {"fields": ["rules_text"], "note": "Fixed."}

    def test_idempotent_skip(self):
        cards = [{"id": "c1", "rules_text": "new text"}]
        errata = [{"card_id": "c1", "rules_text": {
            "as_printed": "old text", "corrected": "new text", "note": "Fixed."}}]
        applied, skipped, warnings = apply_card_errata(cards, errata)
        assert applied == 0
        assert skipped == 1
        assert cards[0]["errata"]["fields"] == ["rules_text"]

    def test_warn_on_unexpected_value(self):
        cards = [{"id": "c1", "rules_text": "unrelated"}]
        errata = [{"card_id": "c1", "rules_text": {
            "as_printed": "old text", "corrected": "new text"}}]
        applied, skipped, warnings = apply_card_errata(cards, errata)
        assert applied == 0
        assert len(warnings) == 1
        assert "c1" in warnings[0]
        assert "errata" not in cards[0]

    def test_warn_on_missing_card(self):
        cards = [{"id": "c1", "rules_text": "x"}]
        errata = [{"card_id": "c99", "rules_text": {"corrected": "y"}}]
        applied, skipped, warnings = apply_card_errata(cards, errata)
        assert applied == 0
        assert "c99" in warnings[0]

    def test_append_adds_note(self):
        cards = [{"id": "c1", "notes": ["first"]}]
        errata = [{"card_id": "c1", "notes": {
            "append": ["second"], "note": "Designer addition."}}]
        applied, skipped, warnings = apply_card_errata(cards, errata)
        assert applied == 1
        assert warnings == []
        assert cards[0]["notes"] == ["first", "second"]
        assert cards[0]["errata"] == {"fields": ["notes"], "note": "Designer addition."}

    def test_append_to_missing_notes_field(self):
        cards = [{"id": "c1"}]
        errata = [{"card_id": "c1", "notes": {"append": ["only"]}}]
        applied, skipped, warnings = apply_card_errata(cards, errata)
        assert applied == 1
        assert cards[0]["notes"] == ["only"]

    def test_append_idempotent_skip(self):
        cards = [{"id": "c1", "notes": ["first", "second"]}]
        errata = [{"card_id": "c1", "notes": {"append": ["second"], "note": "Add."}}]
        applied, skipped, warnings = apply_card_errata(cards, errata)
        assert applied == 0
        assert skipped == 1
        assert cards[0]["notes"] == ["first", "second"]
        assert cards[0]["errata"]["fields"] == ["notes"]

    def test_append_normalizes_whitespace_for_dedup(self):
        cards = [{"id": "c1", "notes": ["alpha beta"]}]
        errata = [{"card_id": "c1", "notes": {"append": ["alpha\n  beta"]}}]
        applied, skipped, warnings = apply_card_errata(cards, errata)
        assert applied == 0
        assert skipped == 1
        assert cards[0]["notes"] == ["alpha beta"]

    def test_corrected_and_append_mutually_exclusive(self):
        cards = [{"id": "c1", "notes": ["first"]}]
        errata = [{"card_id": "c1", "notes": {"corrected": ["x"], "append": ["y"]}}]
        applied, skipped, warnings = apply_card_errata(cards, errata)
        assert applied == 0
        assert len(warnings) == 1
        assert "not both" in warnings[0]
        assert "errata" not in cards[0]

    def test_append_to_non_list_field_warns(self):
        cards = [{"id": "c1", "rules_text": "scalar"}]
        errata = [{"card_id": "c1", "rules_text": {"append": ["x"]}}]
        applied, skipped, warnings = apply_card_errata(cards, errata)
        assert applied == 0
        assert len(warnings) == 1
        assert "non-list" in warnings[0]


class TestApplyPrintingErrata:
    def test_oracle_field_propagates_to_card_and_preserves_printed(self):
        cards = [{"id": "c1", "rules_text": "gives it to you"}]
        printings = [{"id": "p1", "card_id": "c1", "printed_rules_text": None, "errata": None}]
        errata = [{"printing_id": "p1", "rules_text": {
            "as_printed": "gives it to you", "corrected": "give it to you", "note": "Typo."}}]
        applied, skipped, warnings = apply_printing_errata(cards, printings, errata)
        assert applied == 1
        assert warnings == []
        # oracle corrected on the card
        assert cards[0]["rules_text"] == "give it to you"
        # original printed text preserved on the printing
        assert printings[0]["printed_rules_text"] == "gives it to you"
        # marker on the printing
        assert printings[0]["errata"] == {"fields": ["rules_text"], "note": "Typo."}

    def test_as_printed_defaults_to_card_current(self):
        cards = [{"id": "c1", "rules_text": "gives it to you"}]
        printings = [{"id": "p1", "card_id": "c1"}]
        errata = [{"printing_id": "p1", "rules_text": {"corrected": "give it to you"}}]
        applied, skipped, warnings = apply_printing_errata(cards, printings, errata)
        assert applied == 1
        assert printings[0]["printed_rules_text"] == "gives it to you"
        assert cards[0]["rules_text"] == "give it to you"

    def test_idempotent_when_as_printed_omitted(self):
        # Re-running with as_printed omitted must not overwrite the preserved
        # printed text with the (now corrected) card oracle value.
        cards = [{"id": "c1", "rules_text": "gives it to you"}]
        printings = [{"id": "p1", "card_id": "c1"}]
        errata = [{"printing_id": "p1", "rules_text": {"corrected": "give it to you"}}]
        apply_printing_errata(cards, printings, errata)
        applied, skipped, warnings = apply_printing_errata(cards, printings, errata)
        assert applied == 0
        assert skipped == 1
        assert printings[0]["printed_rules_text"] == "gives it to you"
        assert cards[0]["rules_text"] == "give it to you"

    def test_idempotent_skip(self):
        cards = [{"id": "c1", "rules_text": "give it to you"}]
        printings = [{"id": "p1", "card_id": "c1", "printed_rules_text": "gives it to you"}]
        errata = [{"printing_id": "p1", "rules_text": {
            "as_printed": "gives it to you", "corrected": "give it to you", "note": "Typo."}}]
        applied, skipped, warnings = apply_printing_errata(cards, printings, errata)
        assert applied == 0
        assert skipped == 1
        assert printings[0]["errata"]["fields"] == ["rules_text"]

    def test_whitespace_normalized(self):
        cards = [{"id": "c1", "rules_text": "alpha beta gamma"}]
        printings = [{"id": "p1", "card_id": "c1"}]
        errata = [{"printing_id": "p1", "rules_text": {
            "as_printed": "alpha\nbeta   gamma\n", "corrected": "alpha beta delta"}}]
        applied, skipped, warnings = apply_printing_errata(cards, printings, errata)
        assert applied == 1
        assert warnings == []
        assert cards[0]["rules_text"] == "alpha beta delta"

    def test_printing_only_field(self):
        cards = [{"id": "c1"}]
        printings = [{"id": "p1", "card_id": "c1", "artist": "Alice"}]
        errata = [{"printing_id": "p1", "artist": {"as_printed": "Alice", "corrected": "Bob"}}]
        applied, skipped, warnings = apply_printing_errata(cards, printings, errata)
        assert applied == 1
        assert printings[0]["artist"] == "Bob"
        assert printings[0]["errata"]["fields"] == ["artist"]

    def test_warn_on_missing_printing(self):
        cards = [{"id": "c1"}]
        printings = [{"id": "p1", "card_id": "c1"}]
        errata = [{"printing_id": "p99", "rules_text": {"corrected": "y"}}]
        applied, skipped, warnings = apply_printing_errata(cards, printings, errata)
        assert applied == 0
        assert "p99" in warnings[0]


class TestApplyErrataCLI:
    def _write(self, tmp_path, cards, printings, errata):
        cf = tmp_path / "cards.yaml"
        pf = tmp_path / "printings.yaml"
        ef = tmp_path / "errata.yaml"
        cf.write_text(yaml.safe_dump(cards), encoding="utf-8")
        pf.write_text(yaml.safe_dump(printings), encoding="utf-8")
        ef.write_text(yaml.safe_dump(errata), encoding="utf-8")
        return cf, pf, ef

    def test_printing_errata_end_to_end(self, tmp_path: Path):
        cards = [{"id": "c1", "rules_text": "gives it to you"}]
        printings = [{"id": "p1", "card_id": "c1", "printed_rules_text": None, "errata": None}]
        errata = [{"printing_id": "p1", "rules_text": {
            "as_printed": "gives it to you", "corrected": "give it to you", "note": "Typo."}}]
        cf, pf, ef = self._write(tmp_path, cards, printings, errata)
        co, po = tmp_path / "co.yaml", tmp_path / "po.yaml"

        result = CliRunner().invoke(apply_errata, [
            str(cf), str(pf), str(ef), "--cards-out", str(co), "--printings-out", str(po)])
        assert result.exit_code == 0, result.output
        assert "Applied 1 erratum" in result.output

        out_cards = yaml.safe_load(co.read_text(encoding="utf-8"))
        out_printings = yaml.safe_load(po.read_text(encoding="utf-8"))
        assert out_cards[0]["rules_text"] == "give it to you"
        assert out_printings[0]["printed_rules_text"] == "gives it to you"
        assert out_printings[0]["errata"]["note"] == "Typo."

    def test_card_errata_end_to_end(self, tmp_path: Path):
        cards = [{"id": "c1", "rules_text": "old"}]
        printings = [{"id": "p1", "card_id": "c1"}]
        errata = [{"card_id": "c1", "rules_text": {"as_printed": "old", "corrected": "new", "note": "Fix."}}]
        cf, pf, ef = self._write(tmp_path, cards, printings, errata)
        co, po = tmp_path / "co.yaml", tmp_path / "po.yaml"

        result = CliRunner().invoke(apply_errata, [
            str(cf), str(pf), str(ef), "--cards-out", str(co), "--printings-out", str(po)])
        assert result.exit_code == 0, result.output
        out_cards = yaml.safe_load(co.read_text(encoding="utf-8"))
        assert out_cards[0]["rules_text"] == "new"
        assert out_cards[0]["errata"]["fields"] == ["rules_text"]

    def test_mixed_ids_rejected(self, tmp_path: Path):
        errata = [
            {"card_id": "c1", "rules_text": {"corrected": "x"}},
            {"printing_id": "p1", "artist": {"corrected": "y"}},
        ]
        cf, pf, ef = self._write(tmp_path, [{"id": "c1"}], [{"id": "p1", "card_id": "c1"}], errata)
        result = CliRunner().invoke(apply_errata, [
            str(cf), str(pf), str(ef),
            "--cards-out", str(tmp_path / "co.yaml"), "--printings-out", str(tmp_path / "po.yaml")])
        assert result.exit_code != 0
        assert "mixes card_id and printing_id" in result.output

    def test_warnings_emitted(self, tmp_path: Path):
        cards = [{"id": "c1", "rules_text": "current"}]
        printings = [{"id": "p1", "card_id": "c1"}]
        errata = [{"printing_id": "p1", "rules_text": {"as_printed": "different", "corrected": "fixed"}}]
        cf, pf, ef = self._write(tmp_path, cards, printings, errata)
        result = CliRunner().invoke(apply_errata, [
            str(cf), str(pf), str(ef),
            "--cards-out", str(tmp_path / "co.yaml"), "--printings-out", str(tmp_path / "po.yaml")])
        assert result.exit_code == 0
        assert "WARNING" in result.output
