"""Data models for Mood Swings card data.

These TypedDicts document the shape of Card and Printing records
as they flow through the pipeline. They are not enforced at runtime
but serve as documentation and enable type-checking with mypy/pyright.
"""

from datetime import date
from typing import TypedDict

SCHEMA_VERSION = (0, 9, 0)
"""Semantic version of the data schema as a (major, minor, patch) tuple."""


class Card(TypedDict):
    """A unique card identity with its game-mechanical properties."""

    id: str
    """Stable UUID5 generated from the card name."""

    name: str
    """The card's display name."""

    color: list[str]
    """Card colors: e.g. ['White'], ['Blue', 'Black'], or [] for colorless."""

    dice: str | None
    """Primary dice notation, e.g. '[3]' or '[6][1]'. None for helper cards."""

    dice_value: int
    """Integer sum of pips in the primary dice. 0 if dice is None."""

    secondary_dice: str | None
    """Secondary dice notation after '/', or None."""

    secondary_dice_value: int
    """Integer sum of pips in the secondary dice. 0 if secondary_dice is None."""

    rules_text: str | None
    """HTML-formatted rules text, or None for vanilla cards."""

    rulings_text: list[str] | None
    """List of ruling strings, or None if no rulings exist."""


class Edition(TypedDict):
    """An edition or set of cards."""

    id: str
    """Stable UUID5 generated from set_code."""

    set_code: str
    """Set code, e.g. 'MSW'."""

    edition_name: str
    """Human-readable edition name, e.g. 'Edition 1'."""

    release_date: date
    """When this set first came out."""

    language: str
    """Language code, like 'en' or 'es-mx'."""


class Printing(TypedDict):
    """A specific physical printing of a card."""

    id: str | None
    """Stable UUID5 generated from card_name:set_code:collector_number. None until collector_number is known."""

    card_id: str
    """References the Card.id this printing belongs to."""

    edition_id: str
    """References the Edition.id this printing belongs to."""

    frame: str
    """Frame color/style, e.g. 'White', 'Blue', 'Black', 'Red', 'Green'."""

    reminder_icon: str | None
    """Reminder icon glyph (e.g. '!') or None."""

    rarity: str
    """Rarity: Common, Uncommon, Rare, or Mythic Rare."""

    dice_color: str | None
    """Color of the physical die: 'white', 'black', or None if unknown."""

    collector_number: int | None
    """Collector number within the set, or None if unknown."""

    treatment: str
    """Print treatment, e.g. 'Standard', 'Foil'."""

    artist: str | list[str] | None
    """Artist name, list of names for multi-artist credits, or None if unknown."""

    card_image_url: str | None
    """URL to the card image, or None if unavailable."""
