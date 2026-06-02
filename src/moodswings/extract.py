"""Extract card data from the Mood Swings card notes HTML file."""

import re
import uuid
from pathlib import Path

import click
import yaml
from bs4 import BeautifulSoup, NavigableString, Tag


# Fixed namespace for deterministic UUID5 generation
MSDATA_NAMESPACE = uuid.UUID("f47ac10b-58cc-4372-a567-0d02b2c3d479")


def generate_card_id(card_name: str) -> str:
    """Generate a stable card ID (UUID5) from card name."""
    return str(uuid.uuid5(MSDATA_NAMESPACE, card_name))


def generate_printing_id(card_name: str, set_code: str, collector_number: int) -> str:
    """Generate a stable printing ID (UUID5) from card name + set code + collector number."""
    key = f"{card_name}:{set_code}:{collector_number}"
    return str(uuid.uuid5(MSDATA_NAMESPACE, key))


# Color-to-frame mapping for first edition (monocolor only)
COLOR_FRAME_MAP = {
    "White": "White",
    "Blue": "Blue",
    "Black": "Black",
    "Red": "Red",
    "Green": "Green",
}


def dice_to_int(dice_str: str) -> int:
    """Convert a dice string like '[3]' or '[6][1]' to an integer sum.

    '[3]' -> 3, '[6][1]' -> 7
    """
    pips = re.findall(r"\[(\d+)\]", dice_str)
    return sum(int(p) for p in pips)


def parse_dice_line(dice_text: str) -> dict:
    """Parse a dice line like '[3]/[6][1]' into components.

    Returns dict with:
      - dice: the primary dice string (e.g. "[3]")
      - dice_value: integer sum of pips (e.g. 3)
      - secondary_dice: the secondary string after "/" or None
      - secondary_dice_value: integer sum of secondary pips or None
    """
    # Normalize letter O to digit 0
    dice_text = dice_text.replace("[O]", "[0]")

    parts = dice_text.split("/")
    primary = parts[0].strip()
    secondary = parts[1].strip() if len(parts) > 1 else None

    return {
        "dice": primary,
        "dice_value": dice_to_int(primary),
        "secondary_dice": secondary,
        "secondary_dice_value": dice_to_int(secondary) if secondary else None,
    }




def extract_rules_html(p_tag: Tag) -> str:
    """Extract the rules text portion of a card paragraph, preserving markup.

    The paragraph structure is:
      <strong>Name (Color Rarity)</strong><br>
      [dice]<br>
      [rules text with markup...]

    We want everything after the second <br>.
    """
    contents = list(p_tag.children)

    # Find the second <br> tag
    br_count = 0
    rules_start_idx = None
    for i, node in enumerate(contents):
        if isinstance(node, Tag) and node.name == "br":
            br_count += 1
            if br_count == 2:
                rules_start_idx = i + 1
                break

    if rules_start_idx is None:
        return ""

    # Collect everything after the second <br>
    rules_parts = []
    for node in contents[rules_start_idx:]:
        if isinstance(node, NavigableString):
            rules_parts.append(str(node))
        elif isinstance(node, Tag):
            rules_parts.append(str(node))

    rules_html = "".join(rules_parts).strip()
    # Strip leading newline that sometimes appears
    rules_html = rules_html.lstrip("\n")
    return rules_html


def extract_rulings(p_tag: Tag) -> str | None:
    """Extract rulings from the <ul> following the card paragraph."""
    # Find next sibling elements after this <p>
    sibling = p_tag.next_sibling
    while sibling is not None:
        if isinstance(sibling, Tag):
            if sibling.name == "ul":
                # Collect all <li> text
                items = []
                for li in sibling.find_all("li", recursive=False):
                    items.append(li.decode_contents().strip())
                return items if items else None
            else:
                # Next element is not a <ul>, so no rulings
                return None
        sibling = sibling.next_sibling
    return None


def parse_heading(strong_text: str) -> tuple[str, str, str]:
    """Parse 'Name (Color Rarity)' or 'Name [Color Rarity]' heading.

    Also handles reversed order like 'Name (Rarity Color)'.
    Returns (name, color, rarity).
    """
    colors = {"White", "Blue", "Black", "Red", "Green"}
    rarities = {"Common", "Uncommon", "Rare", "Mythic Rare"}

    # Handle both () and [] delimiters, color-first or rarity-first
    match = re.match(
        r"^(.+?)\s*[\(\[](White|Blue|Black|Red|Green)\s+(Common|Uncommon|Rare|Mythic Rare)[\)\]]$",
        strong_text,
    )
    if match:
        return match.group(1).strip(), match.group(2), match.group(3)

    # Try reversed: Rarity Color
    match = re.match(
        r"^(.+?)\s*[\(\[](Common|Uncommon|Rare|Mythic Rare)\s+(White|Blue|Black|Red|Green)[\)\]]$",
        strong_text,
    )
    if match:
        return match.group(1).strip(), match.group(3), match.group(2)

    raise ValueError(f"Cannot parse card heading: {strong_text!r}")


def parse_html(html_path: Path) -> list[dict]:
    """Parse the HTML file and extract all card data."""
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    cards = []
    printings = []

    # Find all magic-card elements to get image URLs
    magic_cards = soup.find_all("magic-card")
    # Find all card text paragraphs
    card_paragraphs = soup.find_all("p", style="margin-left:.5in;font-family:courier")

    if len(magic_cards) != len(card_paragraphs):
        click.echo(
            f"Warning: found {len(magic_cards)} card images but {len(card_paragraphs)} card text blocks",
            err=True,
        )

    # Build a map from card name to image URL for safe pairing
    image_map: dict[str, str] = {}
    for mc in magic_cards:
        caption = mc.get("caption", "")
        face_url = mc.get("face", "")
        if caption and face_url:
            image_map[caption] = face_url

    for idx, p_tag in enumerate(card_paragraphs, start=1):
        # Parse the heading (first <strong>)
        first_strong = p_tag.find("strong")
        if not first_strong:
            click.echo(f"Warning: card #{idx} has no <strong> heading, skipping", err=True)
            continue

        heading_text = first_strong.get_text()
        try:
            name, color, rarity = parse_heading(heading_text)
        except ValueError as e:
            click.echo(f"Warning: {e}, skipping card #{idx}", err=True)
            continue

        # Parse dice line (text between first and second <br>)
        contents = list(p_tag.children)
        br_indices = [
            i for i, node in enumerate(contents)
            if isinstance(node, Tag) and node.name == "br"
        ]

        if len(br_indices) < 2:
            # Card might only have name + dice (no rules text), e.g. blank cards
            # Try to get dice from text after first <br>
            if len(br_indices) >= 1:
                dice_text_parts = []
                for node in contents[br_indices[0] + 1:]:
                    if isinstance(node, Tag) and node.name == "br":
                        break
                    if isinstance(node, NavigableString):
                        dice_text_parts.append(str(node))
                dice_text = "".join(dice_text_parts).strip()
            else:
                dice_text = ""
        else:
            # Get text between first and second <br>
            dice_text_parts = []
            for node in contents[br_indices[0] + 1: br_indices[1]]:
                if isinstance(node, NavigableString):
                    dice_text_parts.append(str(node))
                elif isinstance(node, Tag):
                    dice_text_parts.append(node.get_text())
            dice_text = "".join(dice_text_parts).strip()

        dice_info = parse_dice_line(dice_text)

        # Extract rules text (HTML after second <br>)
        rules_html = extract_rules_html(p_tag)

        # Extract rulings
        rulings = extract_rulings(p_tag)

        # Get image URL by matching name
        image_url = image_map.get(name)
        if image_url is None:
            click.echo(f"Warning: no image found for card '{name}'", err=True)

        card_id = generate_card_id(name)

        card = {
            "id": card_id,
            "name": name,
            "color": color,
            "dice": dice_info["dice"],
            "dice_value": dice_info["dice_value"],
            "secondary_dice": dice_info["secondary_dice"],
            "secondary_dice_value": dice_info["secondary_dice_value"],
            "rules_text": rules_html if rules_html else None,
            "rulings_text": rulings,
        }

        printing = {
            "id": None,
            "card-id": card_id,
            "frame": COLOR_FRAME_MAP[color],
            "reminder_icon": None,
            "rarity": rarity,
            "dice_color": None,
            "collector_number": None,
            "set_code": "MSW",
            "edition_name": "Edition 1",
            "artist": None,
            "card_image_url": image_url,
        }

        cards.append(card)
        printings.append(printing)

    return cards, printings


@click.command("extract-cards")
@click.argument("html_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output YAML file for cards. Defaults to stdout.",
)
@click.option(
    "-p", "--printings-output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output YAML file for printings. If not set, uses <output>_printings.yaml.",
)
def extract_cards(html_file: Path, output: Path | None, printings_output: Path | None):
    """Extract card data from HTML and output as YAML (cards + printings)."""
    cards, printings = parse_html(html_file)
    click.echo(f"Extracted {len(cards)} cards", err=True)

    cards_yaml = yaml.safe_dump(
        cards,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    printings_yaml = yaml.safe_dump(
        printings,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )

    if output:
        output.write_text(cards_yaml, encoding="utf-8")
        click.echo(f"Cards written to {output}", err=True)

        if printings_output is None:
            printings_output = output.with_name(
                output.stem + "_printings" + output.suffix
            )
        printings_output.write_text(printings_yaml, encoding="utf-8")
        click.echo(f"Printings written to {printings_output}", err=True)
    else:
        click.echo("--- cards ---")
        click.echo(cards_yaml)
        click.echo("--- printings ---")
        click.echo(printings_yaml)
