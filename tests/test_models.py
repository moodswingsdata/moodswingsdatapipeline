"""Tests that pipeline outputs conform to the data models.

Validates that Card and Printing dicts produced by the pipeline
have the correct keys and value types as documented in
src/moodswings/models.py and types/moodswings.d.ts.
"""

from pathlib import Path

import pytest

from moodswings.extract import parse_html
from moodswings.models import Card, Printing

FIXTURES = Path(__file__).parent / "fixtures"

# Expected fields and their allowed types, derived from the TypedDict definitions
CARD_FIELDS = {
    "id": (str,),
    "name": (str,),
    "color": (list,),
    "dice": (str,),
    "dice_value": (int,),
    "secondary_dice": (str, type(None)),
    "secondary_dice_value": (int, type(None)),
    "rules_text": (str, type(None)),
    "timing": (list,),
    "notes": (list, type(None)),
    "errata": (dict, type(None)),
}

PRINTING_FIELDS = {
    "id": (str, type(None)),
    "card_id": (str,),
    "edition_id": (str, type(None)),
    "frame": (str,),
    "reminder_icon": (str, type(None)),
    "rarity": (str,),
    "dice_color": (str, type(None)),
    "collector_number": (int, type(None)),
    "treatment": (str,),
    "artist": (str, list, type(None)),
    "card_image_url": (str, type(None)),
    "is_headliner": (bool,),
    "printed_rules_text": (str, type(None)),
    "errata": (dict, type(None)),
}

VALID_COLORS = {"White", "Blue", "Black", "Red", "Green"}
VALID_RARITIES = {"Common", "Uncommon", "Rare", "Mythic Rare"}
VALID_DICE_COLORS = {"white", "black", None}


@pytest.fixture
def parsed_data():
    html_path = FIXTURES / "sample_cards.html"
    cards, printings = parse_html(html_path)
    return cards, printings


class TestCardConformsToModel:
    def test_card_has_all_fields(self, parsed_data):
        cards, _ = parsed_data
        for card in cards:
            for field in CARD_FIELDS:
                assert field in card, f"Card {card.get('name', '?')} missing field '{field}'"

    def test_card_has_no_extra_fields(self, parsed_data):
        cards, _ = parsed_data
        for card in cards:
            for key in card:
                assert key in CARD_FIELDS, (
                    f"Card {card.get('name', '?')} has unexpected field '{key}'"
                )

    def test_card_field_types(self, parsed_data):
        cards, _ = parsed_data
        for card in cards:
            for field, allowed_types in CARD_FIELDS.items():
                value = card[field]
                assert isinstance(value, allowed_types), (
                    f"Card {card['name']}.{field} = {value!r} "
                    f"(type {type(value).__name__}), expected {allowed_types}"
                )

    def test_card_color_values(self, parsed_data):
        cards, _ = parsed_data
        for card in cards:
            assert isinstance(card["color"], list), (
                f"Card {card['name']} color should be a list, got {type(card['color'])}"
            )
            for c in card["color"]:
                assert c in VALID_COLORS, (
                    f"Card {card['name']} has invalid color '{c}'"
                )

    def test_card_notes_items_are_strings(self, parsed_data):
        cards, _ = parsed_data
        for card in cards:
            if card["notes"] is not None:
                for item in card["notes"]:
                    assert isinstance(item, str), (
                        f"Card {card['name']} has non-string note: {item!r}"
                    )

    def test_card_id_is_uuid_format(self, parsed_data):
        """Card IDs should be valid UUID strings."""
        import uuid

        cards, _ = parsed_data
        for card in cards:
            try:
                uuid.UUID(card["id"])
            except ValueError:
                pytest.fail(f"Card {card['name']} has invalid UUID id: {card['id']}")


class TestPrintingConformsToModel:
    def test_printing_has_all_fields(self, parsed_data):
        _, printings = parsed_data
        for printing in printings:
            for field in PRINTING_FIELDS:
                assert field in printing, (
                    f"Printing {printing.get('card_id', '?')} missing field '{field}'"
                )

    def test_printing_has_no_extra_fields(self, parsed_data):
        _, printings = parsed_data
        for printing in printings:
            for key in printing:
                assert key in PRINTING_FIELDS, (
                    f"Printing {printing.get('card_id', '?')} has unexpected field '{key}'"
                )

    def test_printing_field_types(self, parsed_data):
        _, printings = parsed_data
        for printing in printings:
            for field, allowed_types in PRINTING_FIELDS.items():
                value = printing[field]
                assert isinstance(value, allowed_types), (
                    f"Printing.{field} = {value!r} "
                    f"(type {type(value).__name__}), expected {allowed_types}"
                )

    def test_printing_rarity_values(self, parsed_data):
        _, printings = parsed_data
        for printing in printings:
            assert printing["rarity"] in VALID_RARITIES, (
                f"Printing has invalid rarity '{printing['rarity']}'"
            )

    def test_printing_frame_values(self, parsed_data):
        _, printings = parsed_data
        for printing in printings:
            assert printing["frame"] in VALID_COLORS, (
                f"Printing has invalid frame '{printing['frame']}'"
            )

    def test_printing_dice_color_values(self, parsed_data):
        _, printings = parsed_data
        for printing in printings:
            assert printing["dice_color"] in VALID_DICE_COLORS, (
                f"Printing has invalid dice_color '{printing['dice_color']}'"
            )

    def test_printing_card_id_references_card(self, parsed_data):
        cards, printings = parsed_data
        card_ids = {c["id"] for c in cards}
        for printing in printings:
            assert printing["card_id"] in card_ids, (
                f"Printing references unknown card_id '{printing['card_id']}'"
            )

    def test_printing_artist_list_items_are_strings(self, parsed_data):
        _, printings = parsed_data
        for printing in printings:
            if isinstance(printing["artist"], list):
                for item in printing["artist"]:
                    assert isinstance(item, str), (
                        f"Printing has non-string artist item: {item!r}"
                    )
