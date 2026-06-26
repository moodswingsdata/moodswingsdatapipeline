"""Tests for card extraction from HTML."""

from pathlib import Path

import pytest

from moodswings.extract import (
    extract_timing,
    generate_card_id,
    generate_printing_id,
    parse_dice_line,
    parse_heading,
    parse_html,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseHeading:
    def test_standard_format(self):
        name, color, rarity = parse_heading("Altruism (White Rare)")
        assert name == "Altruism"
        assert color == "White"
        assert rarity == "Rare"

    def test_common(self):
        name, color, rarity = parse_heading("Ambition (Black Common)")
        assert name == "Ambition"
        assert color == "Black"
        assert rarity == "Common"

    def test_uncommon(self):
        name, color, rarity = parse_heading("Anger (Red Uncommon)")
        assert name == "Anger"
        assert color == "Red"
        assert rarity == "Uncommon"

    def test_mythic_rare(self):
        name, color, rarity = parse_heading("Love (Green Mythic Rare)")
        assert name == "Love"
        assert color == "Green"
        assert rarity == "Mythic Rare"

    def test_bracket_delimiters(self):
        name, color, rarity = parse_heading("Bliss [Green Common]")
        assert name == "Bliss"
        assert color == "Green"
        assert rarity == "Common"

    def test_reversed_order(self):
        name, color, rarity = parse_heading("Fury (Uncommon Red)")
        assert name == "Fury"
        assert color == "Red"
        assert rarity == "Uncommon"

    def test_multi_word_name(self):
        name, color, rarity = parse_heading("Hurt Feelings (Blue Rare)")
        assert name == "Hurt Feelings"
        assert color == "Blue"
        assert rarity == "Rare"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_heading("Not A Card")


class TestParseDiceLine:
    def test_single_die(self):
        result = parse_dice_line("[3]")
        assert result["dice"] == "[3]"
        assert result["dice_value"] == 3
        assert result["secondary_dice"] is None
        assert result["secondary_dice_value"] is None

    def test_multi_die(self):
        result = parse_dice_line("[6][1]")
        assert result["dice"] == "[6][1]"
        assert result["dice_value"] == 7
        assert result["secondary_dice"] is None

    def test_primary_and_secondary(self):
        result = parse_dice_line("[3]/[6][1]")
        assert result["dice"] == "[3]"
        assert result["dice_value"] == 3
        assert result["secondary_dice"] == "[6][1]"
        assert result["secondary_dice_value"] == 7

    def test_zero_value(self):
        result = parse_dice_line("[0]")
        assert result["dice"] == "[0]"
        assert result["dice_value"] == 0

    def test_letter_o_normalized(self):
        result = parse_dice_line("[O]")
        assert result["dice"] == "[0]"
        assert result["dice_value"] == 0


class TestGenerateIds:
    def test_card_id_deterministic(self):
        id1 = generate_card_id("Altruism")
        id2 = generate_card_id("Altruism")
        assert id1 == id2

    def test_card_id_differs_by_name(self):
        id1 = generate_card_id("Altruism")
        id2 = generate_card_id("Anger")
        assert id1 != id2

    def test_printing_id_deterministic(self):
        id1 = generate_printing_id("Altruism", "MSW", 1)
        id2 = generate_printing_id("Altruism", "MSW", 1)
        assert id1 == id2

    def test_printing_id_differs_by_collector_number(self):
        id1 = generate_printing_id("Altruism", "MSW", 1)
        id2 = generate_printing_id("Altruism", "MSW", 2)
        assert id1 != id2


class TestExtractTiming:
    def test_single_timing(self):
        assert extract_timing("<strong>While in play</strong> — do a thing") == ["in_play"]

    def test_after_playing(self):
        assert extract_timing("<strong>After playing this mood</strong> — x") == ["after_playing"]

    def test_to_play(self):
        assert extract_timing("<strong>To play this card</strong> — x") == ["to_play"]

    def test_multiple_in_order(self):
        html = "<strong>To play this card</strong> — a <strong>While in play</strong> — b"
        assert extract_timing(html) == ["to_play", "in_play"]

    def test_dedupes(self):
        html = "<strong>While in play</strong> a <strong>while in play</strong> b"
        assert extract_timing(html) == ["in_play"]

    def test_case_and_whitespace_insensitive(self):
        assert extract_timing("<strong>after\n  playing  this mood</strong>") == ["after_playing"]

    def test_ignores_non_timing_bold(self):
        assert extract_timing("Take the <strong>next</strong> card") == []

    def test_none_and_empty(self):
        assert extract_timing(None) == []
        assert extract_timing("") == []


class TestParseHtml:
    @pytest.fixture
    def parsed(self):
        html_path = FIXTURES / "sample_cards.html"
        cards, printings = parse_html(html_path)
        return cards, printings

    def test_extracts_correct_count(self, parsed):
        cards, printings = parsed
        assert len(cards) == 5
        assert len(printings) == 5

    def test_card_names(self, parsed):
        cards, _ = parsed
        names = [c["name"] for c in cards]
        assert "Altruism" in names
        assert "Ambition" in names
        assert "Anger" in names
        assert "Bliss" in names
        assert "Ambivalence" in names

    def test_card_colors(self, parsed):
        cards, _ = parsed
        by_name = {c["name"]: c for c in cards}
        assert by_name["Altruism"]["color"] == ["White"]
        assert by_name["Ambition"]["color"] == ["Black"]
        assert by_name["Anger"]["color"] == ["Red"]
        assert by_name["Bliss"]["color"] == ["Green"]
        assert by_name["Ambivalence"]["color"] == ["Blue"]

    def test_card_dice_values(self, parsed):
        cards, _ = parsed
        by_name = {c["name"]: c for c in cards}

        # Altruism: [3]/[6][1]
        assert by_name["Altruism"]["dice"] == "[3]"
        assert by_name["Altruism"]["dice_value"] == 3
        assert by_name["Altruism"]["secondary_dice"] == "[6][1]"
        assert by_name["Altruism"]["secondary_dice_value"] == 7

        # Ambition: [2]
        assert by_name["Ambition"]["dice"] == "[2]"
        assert by_name["Ambition"]["dice_value"] == 2
        assert by_name["Ambition"]["secondary_dice"] is None

        # Anger: [0]
        assert by_name["Anger"]["dice_value"] == 0

    def test_card_has_rules_text(self, parsed):
        cards, _ = parsed
        by_name = {c["name"]: c for c in cards}
        assert by_name["Altruism"]["rules_text"] is not None
        assert "After playing this mood" in by_name["Altruism"]["rules_text"]

    def test_vanilla_card_no_rules(self, parsed):
        cards, _ = parsed
        by_name = {c["name"]: c for c in cards}
        # Bliss has no rules text (just dice value)
        assert by_name["Bliss"]["rules_text"] is None or by_name["Bliss"]["rules_text"] == ""

    def test_card_has_notes(self, parsed):
        cards, _ = parsed
        by_name = {c["name"]: c for c in cards}
        assert by_name["Altruism"]["notes"] is not None
        assert len(by_name["Altruism"]["notes"]) == 2

    def test_card_without_notes(self, parsed):
        cards, _ = parsed
        by_name = {c["name"]: c for c in cards}
        assert by_name["Anger"]["notes"] is None

    def test_card_timing(self, parsed):
        cards, _ = parsed
        by_name = {c["name"]: c for c in cards}
        assert by_name["Altruism"]["timing"] == ["after_playing"]
        assert by_name["Ambivalence"]["timing"] == ["in_play"]

    def test_printing_has_image_url(self, parsed):
        _, printings = parsed
        # Find the Altruism printing
        altruism_card_id = generate_card_id("Altruism")
        altruism_printing = next(p for p in printings if p["card_id"] == altruism_card_id)
        assert altruism_printing["card_image_url"] == "https://example.com/altruism.webp"

    def test_printing_has_frame(self, parsed):
        _, printings = parsed
        altruism_card_id = generate_card_id("Altruism")
        altruism_printing = next(p for p in printings if p["card_id"] == altruism_card_id)
        assert altruism_printing["frame"] == "White"

    def test_printing_has_rarity(self, parsed):
        _, printings = parsed
        altruism_card_id = generate_card_id("Altruism")
        altruism_printing = next(p for p in printings if p["card_id"] == altruism_card_id)
        assert altruism_printing["rarity"] == "Rare"

    def test_printing_defaults(self, parsed):
        _, printings = parsed
        for p in printings:
            assert p["edition_id"] is None  # not filled in by parse_html
            assert p["treatment"] == "Standard"
