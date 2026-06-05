"""Add card entries interactively or from sidecar files."""

from pathlib import Path

import click
import yaml

from moodswings.extract import generate_card_id, dice_to_int


VALID_COLORS = {"White", "Blue", "Black", "Red", "Green"}


def parse_color_input(raw: str) -> list[str]:
    """Parse a comma-separated color string into a validated list."""
    if not raw.strip():
        return []
    colors = [c.strip().title() for c in raw.split(",")]
    for c in colors:
        if c not in VALID_COLORS:
            raise click.ClickException(
                f"Invalid color '{c}'. Valid colors: {', '.join(sorted(VALID_COLORS))}"
            )
    return colors


def parse_dice_input(raw: str) -> tuple[str, int]:
    """Parse and validate a dice string like '[3]' or '[6][1]'.

    Returns (dice_str, dice_value).
    """
    raw = raw.strip()
    if not raw:
        raise click.ClickException("Dice value is required.")
    value = dice_to_int(raw)
    return raw, value


def build_card_from_entry(entry: dict) -> dict:
    """Build a Card dict from a sidecar file entry."""
    name = entry.get("name")
    if not name:
        raise click.ClickException("Card entry missing 'name' field.")

    card_id = generate_card_id(name)

    color = entry.get("color", [])
    if isinstance(color, str):
        color = parse_color_input(color)

    dice = entry.get("dice", "")
    dice_value = entry.get("dice_value")
    if dice_value is None:
        dice_value = dice_to_int(dice) if dice else 0

    secondary_dice = entry.get("secondary_dice")
    secondary_dice_value = entry.get("secondary_dice_value")
    if secondary_dice and secondary_dice_value is None:
        secondary_dice_value = dice_to_int(secondary_dice)

    return {
        "id": card_id,
        "name": name,
        "color": color,
        "dice": dice,
        "dice_value": dice_value,
        "secondary_dice": secondary_dice or None,
        "secondary_dice_value": secondary_dice_value,
        "rules_text": entry.get("rules_text") or None,
        "rulings_text": entry.get("rulings_text") or None,
    }


@click.command("add-card")
@click.argument("cards_yaml", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--from", "from_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Sidecar YAML file with card entries to add.",
)
def add_card(cards_yaml: Path, from_path: Path | None):
    """Add card(s) to the cards file.

    Use --from to load from a sidecar YAML file. Each entry needs at minimum
    a 'name' and 'dice' field.

    Without --from, runs in interactive mode prompting for each field.
    """
    with open(cards_yaml, "r", encoding="utf-8") as f:
        cards = yaml.safe_load(f) or []

    existing_names = {c["name"].lower() for c in cards}
    new_cards = []

    if from_path:
        with open(from_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        entries = data if isinstance(data, list) else [data]
        if not entries:
            raise click.ClickException(f"No card entries found in {from_path}")

        for entry in entries:
            card = build_card_from_entry(entry)
            if card["name"].lower() in existing_names:
                click.echo(f"  Skipping '{card['name']}' (already exists)", err=True)
                continue
            new_cards.append(card)
            existing_names.add(card["name"].lower())
            click.echo(f"  Added: {card['name']} (id: {card['id']})", err=True)

    else:
        # Interactive mode
        name = click.prompt("Card name")
        if name.lower() in existing_names:
            raise click.ClickException(f"Card '{name}' already exists in {cards_yaml}.")

        color_raw = click.prompt(
            "Color(s) (comma-separated, e.g. 'White' or 'Blue,Black'; blank for colorless)",
            default="",
            show_default=False,
        )
        color = parse_color_input(color_raw)

        dice_raw = click.prompt("Dice (e.g. '[3]' or '[6][1]')")
        dice, dice_value = parse_dice_input(dice_raw)

        secondary_raw = click.prompt(
            "Secondary dice (e.g. '[6][1]', or blank for none)",
            default="",
            show_default=False,
        )
        secondary_dice = None
        secondary_dice_value = None
        if secondary_raw.strip():
            secondary_dice = secondary_raw.strip()
            secondary_dice_value = dice_to_int(secondary_dice)

        rules_text = click.prompt(
            "Rules text (HTML, or blank for vanilla)",
            default="",
            show_default=False,
        )

        card = {
            "id": generate_card_id(name),
            "name": name,
            "color": color,
            "dice": dice,
            "dice_value": dice_value,
            "secondary_dice": secondary_dice,
            "secondary_dice_value": secondary_dice_value,
            "rules_text": rules_text if rules_text else None,
            "rulings_text": None,
        }

        click.echo()
        click.echo("New card entry:")
        click.echo(yaml.safe_dump([card], sort_keys=False, allow_unicode=True))

        if not click.confirm("Add this card?", default=True):
            click.echo("Cancelled.")
            return

        new_cards.append(card)

    if not new_cards:
        click.echo("No new cards to add.", err=True)
        return

    # Append and write
    cards.extend(new_cards)
    yaml_output = yaml.safe_dump(
        cards,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    cards_yaml.write_text(yaml_output, encoding="utf-8")
    click.echo(f"Added {len(new_cards)} card(s) to {cards_yaml}", err=True)

    if not from_path:
        click.echo()
        click.echo(
            "Reminder: create a printing of this card (via `ms add-printing`) "
            "for it to appear in a set."
        )
