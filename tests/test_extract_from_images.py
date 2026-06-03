"""Tests for image-based extraction (OCR and pixel analysis)."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from moodswings.extract_from_images import (
    detect_dice_color,
    detect_reminder_icon,
    extract_artist_from_text,
    extract_collector_number,
    match_artist,
)


class TestDetectDiceColor:
    def _make_card_image(self, dice_fill: str) -> Image.Image:
        """Create a synthetic card image with a dice region of the given fill color."""
        img = Image.new("RGB", (750, 1050), color=(180, 180, 180))
        draw = ImageDraw.Draw(img)
        # DIE_FACE_REGION = (0.795, 0.050, 0.865, 0.125)
        w, h = img.size
        x1, y1, x2, y2 = int(w * 0.795), int(h * 0.050), int(w * 0.865), int(h * 0.125)
        draw.rectangle([x1, y1, x2, y2], fill=dice_fill)
        return img

    def test_white_dice(self):
        img = self._make_card_image("white")
        assert detect_dice_color(img) == "white"

    def test_black_dice(self):
        img = self._make_card_image("black")
        assert detect_dice_color(img) == "black"


class TestDetectReminderIcon:
    def _make_card_image(self, icon_fill: str) -> Image.Image:
        """Create a synthetic card image with an icon region of the given fill color."""
        img = Image.new("RGB", (750, 1050), color=(50, 50, 50))
        draw = ImageDraw.Draw(img)
        # ICON_REGION = (0.70, 0.05, 0.77, 0.12)
        w, h = img.size
        x1, y1, x2, y2 = int(w * 0.70), int(h * 0.05), int(w * 0.77), int(h * 0.12)
        draw.rectangle([x1, y1, x2, y2], fill=icon_fill)
        return img

    def test_icon_present(self):
        img = self._make_card_image("white")
        assert detect_reminder_icon(img) == "!"

    def test_icon_absent(self):
        img = self._make_card_image("black")
        assert detect_reminder_icon(img) is None


class TestExtractCollectorNumber:
    def test_four_digit_number(self):
        assert extract_collector_number("0001 White RARE") == 1

    def test_higher_number(self):
        assert extract_collector_number("0055 Black COMMON") == 55

    def test_no_number(self):
        assert extract_collector_number("no numbers here") is None

    def test_embedded_in_text(self):
        assert extract_collector_number("MSW ® 0042 Green UNCOMMON ™ & ©") == 42


class TestExtractArtistFromText:
    def test_standard_format(self):
        # The regex expects: MSW<symbol> <one_token> <artist> ™ &
        # Real OCR output looks like: "MSW® Ww Jane Smith ™ & © 2026"
        text = "MSW® Ww Jane Smith ™ & © 2026"
        artist = extract_artist_from_text(text)
        assert artist == "Jane Smith"

    def test_no_artist(self):
        text = "some random text without the pattern"
        assert extract_artist_from_text(text) is None


class TestMatchArtist:
    def test_exact_match(self):
        lookup = ["Jane Smith", "John Doe", "Alice Wonder"]
        name, matched = match_artist("Jane Smith", lookup)
        assert name == "Jane Smith"
        assert matched is True

    def test_fuzzy_match(self):
        lookup = ["Jane Smith", "John Doe"]
        name, matched = match_artist("Jane Smlth", lookup)  # typo
        assert name == "Jane Smith"
        assert matched is True

    def test_no_match(self):
        lookup = ["Jane Smith", "John Doe"]
        name, matched = match_artist("Completely Different", lookup)
        assert matched is False

    def test_empty_lookup(self):
        name, matched = match_artist("Anyone", [])
        assert name == "Anyone"
        assert matched is False
