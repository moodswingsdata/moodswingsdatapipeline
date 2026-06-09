"""Extract card metadata from card images (artist, dice color, reminder icon)."""

import json
import re
from pathlib import Path

import click
import pytesseract
import yaml
from PIL import Image, ImageEnhance, ImageStat
from thefuzz import process as fuzz_process

from moodswings.download_images import IMAGE_MAP_FILENAME
from moodswings.extract import generate_printing_id


# Region where the reminder icon (!) appears: upper-right, left of dice
ICON_REGION = (0.70, 0.05, 0.77, 0.12)
# Threshold for bright pixels to detect icon presence
ICON_BRIGHT_THRESHOLD = 25.0  # percent

# Region of the die face for color detection
DIE_FACE_REGION = (0.795, 0.050, 0.865, 0.125)
# Threshold for dark pixels to distinguish black vs white dice
DICE_DARK_THRESHOLD = 40.0  # percent

# Minimum fuzzy match score to accept a lookup match
FUZZY_MATCH_THRESHOLD = 75


def load_artist_lookup(path: Path) -> list[str]:
    """Load the canonical artist names from a lookup file (one per line).

    Lines starting with '#' are comments (skipped entirely).
    Lines starting with '*' are unreviewed entries (included for matching
    but flagged as needing human review).
    """
    if not path.exists():
        return []
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Strip leading '*' for matching purposes
        if stripped.startswith("*"):
            stripped = stripped[1:].strip()
        names.append(stripped)
    return names


def detect_reminder_icon(img: Image.Image) -> str | None:
    """Detect if the card has a reminder icon (!) in the upper-right area.

    Returns "!" if the icon is present, None otherwise.
    """
    gray = img.convert("L")
    w, h = gray.size
    x1, y1, x2, y2 = ICON_REGION
    region = gray.crop((int(w * x1), int(h * y1), int(w * x2), int(h * y2)))
    pixels = region.get_flattened_data()
    bright_pct = sum(1 for p in pixels if p > 200) / len(pixels) * 100
    return "!" if bright_pct > ICON_BRIGHT_THRESHOLD else None


def detect_dice_color(img: Image.Image) -> str:
    """Detect whether the card has white or black dice.

    White dice = value is fixed, black dice = value can change during play.
    Returns "white" or "black".
    """
    gray = img.convert("L")
    w, h = gray.size
    x1, y1, x2, y2 = DIE_FACE_REGION
    region = gray.crop((int(w * x1), int(h * y1), int(w * x2), int(h * y2)))
    pixels = region.get_flattened_data()
    dark_pct = sum(1 for p in pixels if p < 80) / len(pixels) * 100
    return "black" if dark_pct > DICE_DARK_THRESHOLD else "white"


def ocr_card_bottom(img: Image.Image) -> str:
    """Run OCR on the bottom of the card and return the raw text.

    Applies preprocessing (grayscale, contrast boost, upscale) to improve
    results on small text.
    """
    w, h = img.size
    bottom = img.crop((0, int(h * 0.92), w, h))

    # Preprocess: grayscale, boost contrast, upscale for small text
    gray = bottom.convert("L")
    enhanced = ImageEnhance.Contrast(gray).enhance(2.0)
    scaled = enhanced.resize(
        (enhanced.width * 3, enhanced.height * 3), Image.LANCZOS
    )
    return pytesseract.image_to_string(scaled).strip()


def extract_collector_number(ocr_text: str) -> int | None:
    """Extract the collector number from OCR text.

    The bottom of the card has a line like '0001 White RARE' or '0055 Black COMMON'.
    """
    match = re.search(r"\b(\d{4})\b", ocr_text)
    if match:
        return int(match.group(1))
    return None


def extract_artist_from_text(ocr_text: str) -> str | None:
    """Extract the artist name from OCR text.

    Looks for text between 'MSW [symbol]' and '™ &'.
    """
    patterns = [
        r"MSW\S*\s+\S+\s+(.+?)\s*(?:™|T™|1™|_™)\s*&",
        r"MSW\S*\s+\S+\s+(.+?)\s+[™T]\S*\s*&",
        r"MSW\S*\s+\S+\s+(.+?)\s+&\s+©",
    ]
    for pattern in patterns:
        match = re.search(pattern, ocr_text)
        if match:
            return match.group(1).strip().rstrip("_.,")

    return None


def match_artist(raw_ocr: str, lookup: list[str]) -> tuple[str, bool]:
    """Match raw OCR text against the canonical artist lookup list.

    Uses fuzzy string matching to find the best canonical name.
    Returns (name, matched) where matched is True if a good match was found.
    """
    if not lookup:
        return raw_ocr, False

    result = fuzz_process.extractOne(raw_ocr, lookup)
    if result is None:
        return raw_ocr, False

    best_match, score = result[0], result[1]
    if score >= FUZZY_MATCH_THRESHOLD:
        return best_match, True

    return raw_ocr, False


def load_image_map(image_dir: Path) -> dict[str, str]:
    """Load the image map JSON from the image directory."""
    map_path = image_dir / IMAGE_MAP_FILENAME
    if map_path.exists():
        with open(map_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def find_image_for_printing(printing: dict, image_dir: Path, image_map: dict[str, str]) -> Path | None:
    """Find the local image file for a printing using the image map.

    Falls back to filename pattern matching if the map doesn't have the URL.
    """
    url = printing.get("card_image_url")
    if url and url in image_map:
        path = image_dir / image_map[url]
        if path.exists():
            return path

    # Fallback: match by filename pattern (for backwards compatibility)
    card_name = printing.get("_card_name", "")
    if not card_name:
        return None
    safe_name = card_name.lower().replace(" ", "_").replace("'", "")
    for f in sorted(image_dir.iterdir()):
        if f.name == IMAGE_MAP_FILENAME:
            continue
        stem = f.stem
        parts = stem.split("_", 1)
        if len(parts) == 2 and parts[0].isdigit():
            if parts[1] == safe_name:
                return f
    return None


@click.command("extract-from-images")
@click.argument("cards_yaml", type=click.Path(exists=True, path_type=Path))
@click.argument("printings_yaml", type=click.Path(exists=True, path_type=Path))
@click.argument("image_dir", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output printings YAML file path (will not overwrite input).",
)
@click.option(
    "--editions",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Editions YAML file (output of prepare-editions).",
)
@click.option(
    "--artist-lookup",
    type=click.Path(path_type=Path),
    default=Path("inputs/artists.txt"),
    help="Path to the artist names database (one per line). Default: inputs/artists.txt",
)
def extract_from_images(
    cards_yaml: Path, printings_yaml: Path, image_dir: Path, output: Path, editions: Path, artist_lookup: Path
):
    """Extract artist, dice color, reminder icon, and collector number from card images.

    Takes a cards YAML file (for card names), a printings YAML file, and an image
    directory. Emits an updated printings YAML with artist, dice_color,
    reminder_icon, and collector_number fields populated.

    OCR results are fuzzy-matched against the artist lookup database. If a name
    doesn't match, it's added to the database with a leading '*' for human
    review.
    """
    if output.resolve() == printings_yaml.resolve():
        raise click.ClickException("Output path must differ from input printings YAML file.")

    with open(cards_yaml, "r", encoding="utf-8") as f:
        cards = yaml.safe_load(f)
    with open(printings_yaml, "r", encoding="utf-8") as f:
        printings = yaml.safe_load(f)
    with open(editions, "r", encoding="utf-8") as f:
        editions_data = yaml.safe_load(f)

    if not cards or not printings:
        raise click.ClickException("No data found in input YAML files.")

    # Build a lookup from edition_id to set_code
    edition_set_code = {ed["id"]: ed["set_code"] for ed in editions_data}

    # Build a lookup from card id to card name
    id_to_name = {card["id"]: card["name"] for card in cards}

    # Ensure lookup file exists
    if not artist_lookup.exists():
        artist_lookup.touch()

    lookup = load_artist_lookup(artist_lookup)
    click.echo(f"Loaded {len(lookup)} artist names from {artist_lookup}", err=True)

    updated = 0
    missing = 0
    new_artists: list[str] = []

    image_map = load_image_map(image_dir)

    for idx, printing in enumerate(printings, 1):
        card_name = id_to_name.get(printing["card_id"], "Unknown")
        printing["_card_name"] = card_name
        img_path = find_image_for_printing(printing, image_dir, image_map)
        printing.pop("_card_name", None)
        if img_path is None:
            click.echo(
                f"  Warning: no image found for {card_name}",
                err=True,
            )
            missing += 1
            continue

        img = Image.open(img_path).convert("RGB")

        printing["reminder_icon"] = detect_reminder_icon(img)
        printing["dice_color"] = detect_dice_color(img)

        # OCR the bottom strip once for both collector number and artist
        ocr_text = ocr_card_bottom(img)

        collector_num = extract_collector_number(ocr_text)
        if collector_num is not None:
            printing["collector_number"] = collector_num
            set_code = edition_set_code.get(printing.get("edition_id"), "")
            printing["id"] = generate_printing_id(
                card_name, set_code, collector_num
            )

        raw_artist = extract_artist_from_text(ocr_text)
        if raw_artist:
            # Split on '&' for multi-artist credits
            raw_parts = [p.strip() for p in raw_artist.split("&") if p.strip()]
            resolved_artists = []
            for part in raw_parts:
                matched_name, was_matched = match_artist(part, lookup)
                if was_matched:
                    resolved_artists.append(matched_name)
                else:
                    resolved_artists.append(part)
                    if part not in new_artists:
                        new_artists.append(part)
                        lookup.append(part)
                        click.echo(
                            f"  New artist (unmatched): {part} (card: {card_name})",
                            err=True,
                        )
            printing["artist"] = resolved_artists if len(resolved_artists) > 1 else resolved_artists[0]
        else:
            printing["artist"] = None

        updated += 1

    # Append new artists to the lookup file with '*' prefix
    if new_artists:
        with open(artist_lookup, "a", encoding="utf-8") as f:
            for name in new_artists:
                f.write(f"*{name}\n")
        click.echo(
            f"Added {len(new_artists)} new artist(s) to {artist_lookup} (marked with '*' for review)",
            err=True,
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    yaml_output = yaml.safe_dump(
        printings,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    output.write_text(yaml_output, encoding="utf-8")

    click.echo(
        f"Done: {updated} cards updated, {missing} missing images. Written to {output}",
        err=True,
    )
