"""Tests for image-based extraction (OCR and pixel analysis)."""

from pathlib import Path

import pytest
from PIL import Image

from moodswings.extract_from_images import (
    detect_dice_color,
    detect_reminder_icon,
    extract_artist_from_text,
    extract_collector_number,
    match_artist,
    ocr_card_bottom,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def ambivalence_img():
    """003_ambivalence.webp: black dice, no reminder icon, collector #27."""
    return Image.open(FIXTURES / "003_ambivalence.webp").convert("RGB")


@pytest.fixture
def arrogance_img():
    """009_arrogance.webp: white dice, reminder icon '!', collector #82."""
    return Image.open(FIXTURES / "009_arrogance.webp").convert("RGB")


class TestDetectDiceColor:
    def test_black_dice(self, ambivalence_img):
        assert detect_dice_color(ambivalence_img) == "black"

    def test_white_dice(self, arrogance_img):
        assert detect_dice_color(arrogance_img) == "white"


class TestDetectReminderIcon:
    def test_icon_present(self, arrogance_img):
        assert detect_reminder_icon(arrogance_img) == "!"

    def test_icon_absent(self, ambivalence_img):
        assert detect_reminder_icon(ambivalence_img) is None


class TestOcrCardBottom:
    """Tests that use Tesseract OCR on real card images."""

    @pytest.fixture
    def ambivalence_ocr(self, ambivalence_img):
        return ocr_card_bottom(ambivalence_img)

    @pytest.fixture
    def arrogance_ocr(self, arrogance_img):
        return ocr_card_bottom(arrogance_img)

    def test_collector_number_ambivalence(self, ambivalence_ocr):
        num = extract_collector_number(ambivalence_ocr)
        assert num == 27

    def test_collector_number_arrogance(self, arrogance_ocr):
        num = extract_collector_number(arrogance_ocr)
        assert num == 82

    def test_artist_ambivalence_multiple(self, ambivalence_ocr):
        artist = extract_artist_from_text(ambivalence_ocr)
        assert artist is not None
        # Multiple artists separated by & in the raw text
        assert "&" in artist or len(artist.split()) > 1


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
