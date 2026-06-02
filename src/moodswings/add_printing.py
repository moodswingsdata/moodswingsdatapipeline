"""Add printing entries for existing cards, interactively or from files."""

from pathlib import Path

import click
import yaml

from moodswings.extract import generate_card_id, generate_printing_id


PRINTING_FIELDS = [
    ("frame", "Frame (e.g., White, Blue, Black, Red, Green)"),
    ("reminder_icon", "Reminder icon (e.g., '!' or leave blank for none)"),
    ("rarity", "Rarity (Common, Uncommon, Rare, Mythic)"),
    ("dice_color", "Dice color (white, black, or leave blank)"),
    ("collector_number", "Collector number (integer)"),
    ("set_code", "Set code"),
    ("edition_name", "Edition name"),
    ("treatment", "Treatment (e.g., Standard, Foil)"),
    ("artist", "Artist name (use '&' to separate multiple artists)"),
    ("card_image_url", "Card image URL (or leave blank)"),
]


def resolve_printing(entry: dict, cards: list[dict]) -> dict:
    """Resolve a printing entry from file input.

    The entry must have a 'card_name' field (used to look up the card_id).
    Generates the printing id if collector_number and set_code are present.
    """
    card_name = entry.get("card_name")
    if not card_name:
        raise click.ClickException("Printing entry missing 'card_name' field.")

    # Find the card
    card = None
    for c in cards:
        if c["name"].lower() == card_name.lower():
            card = c
            break

    if card is None:
        raise click.ClickException(f"Card '{card_name}' not found in cards YAML.")

    printing = {"id": None, "card_id": card["id"]}

    # Copy known printing fields from the entry
    for field, _ in PRINTING_FIELDS:
        value = entry.get(field)
        if field == "collector_number" and value is not None:
            printing[field] = int(value)
        elif field == "artist" and isinstance(value, str) and "&" in value:
            printing[field] = [a.strip() for a in value.split("&") if a.strip()]
        else:
            printing[field] = value

    # Generate printing ID
    if printing.get("collector_number") is not None and printing.get("set_code"):
        printing["id"] = generate_printing_id(
            card["name"], printing["set_code"], printing["collector_number"]
        )

    return printing


def load_printings_from_path(source: Path) -> list[dict]:
    """Load printing entries from a YAML file or directory of YAML files."""
    entries = []
    if source.is_file():
        with open(source, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, list):
            entries.extend(data)
        elif isinstance(data, dict):
            entries.append(data)
    elif source.is_dir():
        for p in sorted(source.glob("*.yaml")) + sorted(source.glob("*.yml")):
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, list):
                entries.extend(data)
            elif isinstance(data, dict):
                entries.append(data)
    else:
        raise click.ClickException(f"Path does not exist: {source}")
    return entries


@click.command("add-printing")
@click.argument("cards_yaml", type=click.Path(exists=True, path_type=Path))
@click.argument("printings_yaml", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--from", "from_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="YAML file or directory of YAML files with printing entries to append.",
)
@click.option(
    "--card-name",
    default=None,
    help="Card name for interactive mode (prompts for fields).",
)
def add_printing(cards_yaml: Path, printings_yaml: Path, from_path: Path | None, card_name: str | None):
    """Add printing(s) to the printings file.

    Use --from to load from a YAML file or directory. Each entry needs a
    'card_name' field to link to the correct card.

    Use --card-name for interactive mode (prompts for each field).
    """
    with open(cards_yaml, "r", encoding="utf-8") as f:
        cards = yaml.safe_load(f)

    with open(printings_yaml, "r", encoding="utf-8") as f:
        printings = yaml.safe_load(f) or []

    new_printings = []

    if from_path:
        entries = load_printings_from_path(from_path)
        if not entries:
            raise click.ClickException(f"No printing entries found in {from_path}")

        for entry in entries:
            printing = resolve_printing(entry, cards)
            new_printings.append(printing)
            click.echo(
                f"  Resolved: {entry.get('card_name')} #{printing.get('collector_number')} "
                f"({printing.get('treatment', 'Standard')})",
                err=True,
            )

    elif card_name:
        # Interactive mode
        card = None
        for c in cards:
            if c["name"].lower() == card_name.lower():
                card = c
                break

        if card is None:
            raise click.ClickException(
                f"Card '{card_name}' not found in {cards_yaml}. "
                f"Available: {', '.join(c['name'] for c in cards[:10])}..."
            )

        click.echo(f"Adding printing for: {card['name']} (id: {card['id']})")
        click.echo()

        printing = {"id": None, "card_id": card["id"]}

        for field, prompt_text in PRINTING_FIELDS:
            value = click.prompt(prompt_text, default="", show_default=False)

            if field == "collector_number":
                printing[field] = int(value) if value else None
            elif field in ("reminder_icon", "dice_color", "card_image_url"):
                printing[field] = value if value else None
            elif field == "artist":
                if not value:
                    printing[field] = None
                elif "&" in value:
                    printing[field] = [a.strip() for a in value.split("&") if a.strip()]
                else:
                    printing[field] = value
            else:
                printing[field] = value if value else None

        if printing["collector_number"] is not None and printing["set_code"]:
            printing["id"] = generate_printing_id(
                card["name"], printing["set_code"], printing["collector_number"]
            )

        click.echo()
        click.echo("New printing entry:")
        click.echo(yaml.safe_dump([printing], sort_keys=False, allow_unicode=True))

        if not click.confirm("Add this printing?", default=True):
            click.echo("Cancelled.")
            return

        new_printings.append(printing)

    else:
        raise click.ClickException("Provide either --from or --card-name.")

    # Append and write
    printings.extend(new_printings)
    yaml_output = yaml.safe_dump(
        printings,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    printings_yaml.write_text(yaml_output, encoding="utf-8")
    click.echo(f"Added {len(new_printings)} printing(s) to {printings_yaml}", err=True)
