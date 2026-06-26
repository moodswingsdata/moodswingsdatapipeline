"""Create a card entry interactively and write it to a YAML file."""

from pathlib import Path

import click
import yaml

from moodswings.extract import generate_card_id, dice_to_int, extract_timing


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


def parse_dice_input(raw: str) -> tuple[str | None, int]:
    """Parse and validate a dice string like '[3]' or '[6][1]'.

    Returns (dice_str, dice_value). Returns (None, 0) if blank.
    """
    raw = raw.strip()
    if not raw:
        return None, 0
    value = dice_to_int(raw)
    return raw, value


@click.command("create-card")
@click.argument("output", type=click.Path(path_type=Path))
def create_card(output: Path):
    """Create a card interactively and write it to OUTPUT.

    If OUTPUT exists, the new card is appended (keeping cards sorted by name).
    If OUTPUT does not exist, it is created.
    """
    # Load existing cards if file exists
    existing_cards: list[dict] = []
    if output.exists():
        with open(output, "r", encoding="utf-8") as f:
            existing_cards = yaml.safe_load(f) or []

    existing_names = {c["name"].lower() for c in existing_cards}

    # Interactive prompts
    name = click.prompt("Card name")
    if name.lower() in existing_names:
        raise click.ClickException(f"Card '{name}' already exists in {output}.")

    color_raw = click.prompt(
        "Color(s) (comma-separated, e.g. 'White' or 'Blue,Black'; blank for colorless)",
        default="",
        show_default=False,
    )
    color = parse_color_input(color_raw)

    dice_raw = click.prompt("Dice (e.g. '[3]' or '[6][1]', or blank for none)", default="", show_default=False)
    dice, dice_value = parse_dice_input(dice_raw)

    secondary_raw = click.prompt(
        "Secondary dice (e.g. '[6][1]', or blank for none)",
        default="",
        show_default=False,
    )
    secondary_dice: str | None = None
    secondary_dice_value: int = 0
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
        "timing": extract_timing(rules_text if rules_text else None),
        "notes": None,
        "errata": None,
    }

    click.echo()
    click.echo("New card entry:")
    click.echo(yaml.safe_dump([card], sort_keys=False, allow_unicode=True))

    if not click.confirm("Add this card?", default=True):
        click.echo("Cancelled.")
        return

    existing_cards.append(card)
    existing_cards.sort(key=lambda c: c["name"].lower())

    output.parent.mkdir(parents=True, exist_ok=True)
    yaml_output = yaml.safe_dump(
        existing_cards,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    output.write_text(yaml_output, encoding="utf-8")
    click.echo(f"Wrote card '{name}' to {output}", err=True)
    click.echo()
    click.echo(
        "Reminder: create a printing of this card (via `ms create-printing`) "
        "for it to appear in a set."
    )
