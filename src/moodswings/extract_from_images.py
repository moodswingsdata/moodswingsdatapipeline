"""Extract card metadata from card images (artist, dice color, reminder icon)."""

import re
from pathlib import Path

import click
import pytesseract
import yaml
from PIL import Image, ImageStat


# Region where the reminder icon (!) appears: upper-right, left of dice
ICON_REGION = (0.70, 0.05, 0.77, 0.12)
# Threshold for bright pixels to detect icon presence
ICON_BRIGHT_THRESHOLD = 25.0  # percent

# Region of the die face for color detection
DIE_FACE_REGION = (0.795, 0.050, 0.865, 0.125)
# Threshold for dark pixels to distinguish black vs white dice
DICE_DARK_THRESHOLD = 40.0  # percent


def detect_reminder_icon(img: Image.Image) -> str | None:
    """Detect if the card has a reminder icon (!) in the upper-right area.

    Returns "!" if the icon is present, None otherwise.
    """
    gray = img.convert("L")
    w, h = gray.size
    x1, y1, x2, y2 = ICON_REGION
    region = gray.crop((int(w * x1), int(h * y1), int(w * x2), int(h * y2)))
    pixels = list(region.getdata())
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
    pixels = list(region.getdata())
    dark_pct = sum(1 for p in pixels if p < 80) / len(pixels) * 100
    return "black" if dark_pct > DICE_DARK_THRESHOLD else "white"


def extract_artist(img: Image.Image) -> str | None:
    """Extract the artist name from the bottom of the card using OCR.

    The bottom region contains text like:
    'NNNN Color RARITY\\nMSW [symbol] Artist Name ™ & © 2026 Wizards of the Coast'
    """
    w, h = img.size
    bottom = img.crop((0, int(h * 0.92), w, h))
    text = pytesseract.image_to_string(bottom).strip()

    # Try several patterns to extract artist name between MSW and ™/&
    patterns = [
        r"MSW\S*\s+\S+\s+(.+?)\s*(?:™|T™|1™|_™)\s*&",
        r"MSW\S*\s+\S+\s+(.+?)\s+[™T]\S*\s*&",
        r"MSW\S*\s+\S+\s+(.+?)\s+&\s+©",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            artist = match.group(1).strip().rstrip("_.,")
            return artist

    return None


def find_image_for_card(card: dict, image_dir: Path) -> Path | None:
    """Find the image file matching a card by collector number and name."""
    collector_num = card["collector_number"]
    safe_name = card["name"].lower().replace(" ", "_").replace("'", "")
    # Try the expected filename pattern
    for ext in [".webp", ".png", ".jpg"]:
        filename = f"{collector_num:03d}_{safe_name}{ext}"
        filepath = image_dir / filename
        if filepath.exists():
            return filepath
    # Fallback: search by collector number prefix
    for f in image_dir.iterdir():
        if f.name.startswith(f"{collector_num:03d}_"):
            return f
    return None


@click.command("extract-from-images")
@click.argument("yaml_file", type=click.Path(exists=True, path_type=Path))
@click.argument("image_dir", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output YAML file path (will not overwrite input).",
)
def extract_from_images(yaml_file: Path, image_dir: Path, output: Path):
    """Extract artist, dice color, and reminder icon from card images.

    Takes an input YAML file and image directory, and emits a new YAML file
    with the artist, dice_color, and reminder_icon fields updated.
    """
    if output.resolve() == yaml_file.resolve():
        raise click.ClickException("Output path must differ from input YAML file.")

    with open(yaml_file, "r", encoding="utf-8") as f:
        cards = yaml.safe_load(f)

    if not cards:
        raise click.ClickException("No cards found in input YAML file.")

    updated = 0
    missing = 0

    for card in cards:
        img_path = find_image_for_card(card, image_dir)
        if img_path is None:
            click.echo(
                f"  Warning: no image found for {card['name']} (#{card['collector_number']})",
                err=True,
            )
            missing += 1
            continue

        img = Image.open(img_path).convert("RGB")

        card["reminder_icon"] = detect_reminder_icon(img)
        card["dice_color"] = detect_dice_color(img)
        card["artist"] = extract_artist(img)

        updated += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    yaml_output = yaml.safe_dump(
        cards,
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
