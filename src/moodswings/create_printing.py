"""Create a printing entry interactively and write it to a YAML file."""

from pathlib import Path

import click
import yaml

from moodswings.extract import generate_printing_id, dice_to_int
from moodswings.prepare_editions import generate_edition_id


PRINTING_FIELDS = [
    ("frame", "Frame (e.g., White, Blue, Black, Red, Green)"),
    ("reminder_icon", "Reminder icon (e.g., '!' or leave blank for none)"),
    ("rarity", "Rarity (Common, Uncommon, Rare, Mythic)"),
    ("dice_color", "Dice color (white, black, or leave blank)"),
    ("collector_number", "Collector number (integer)"),
    ("set_code", "Set code"),
    ("treatment", "Treatment (e.g., Standard, Foil)"),
    ("artist", "Artist name (use '&' to separate multiple artists)"),
    ("card_image_url", "Card image URL (or leave blank)"),
]


@click.command("create-printing")
@click.argument("output", type=click.Path(path_type=Path))
@click.option(
    "--cards",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Cards YAML file (to look up card by name).",
)
@click.option(
    "--editions",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Editions YAML file (output of prepare-editions).",
)
@click.option(
    "--card-name",
    required=True,
    help="Card name to create a printing for.",
)
@click.option(
    "--is-headliner",
    is_flag=True,
    default=False,
    help="Mark this printing as the edition's headliner (editorial designation).",
)
def create_printing(output: Path, cards: Path, editions: Path, card_name: str, is_headliner: bool):
    """Create a printing interactively and write it to OUTPUT.

    If OUTPUT exists, the new printing is appended (keeping printings sorted by
    collector number). If OUTPUT does not exist, it is created.
    """
    with open(cards, "r", encoding="utf-8") as f:
        cards_data = yaml.safe_load(f)

    with open(editions, "r", encoding="utf-8") as f:
        editions_data = yaml.safe_load(f)

    # Find the card
    card = None
    for c in cards_data:
        if c["name"].lower() == card_name.lower():
            card = c
            break

    if card is None:
        raise click.ClickException(
            f"Card '{card_name}' not found in {cards}. "
            f"Available: {', '.join(c['name'] for c in cards_data[:10])}..."
        )

    click.echo(f"Adding printing for: {card['name']} (id: {card['id']})")
    click.echo()

    printing = {"id": None, "card_id": card["id"], "edition_id": None}

    set_code_value = None
    for field, prompt_text in PRINTING_FIELDS:
        value = click.prompt(prompt_text, default="", show_default=False)

        if field == "set_code":
            set_code_value = value if value else None
            if set_code_value:
                edition = None
                for ed in editions_data:
                    if ed["set_code"].lower() == set_code_value.lower():
                        edition = ed
                        break
                if edition is None:
                    raise click.ClickException(
                        f"Set code '{set_code_value}' not found in editions. "
                        f"Available: {', '.join(e['set_code'] for e in editions_data)}"
                    )
                printing["edition_id"] = edition["id"]
        elif field == "collector_number":
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

    printing["is_headliner"] = is_headliner
    printing["printed_rules_text"] = None
    printing["errata"] = None

    if printing["collector_number"] is not None and set_code_value:
        printing["id"] = generate_printing_id(
            card["name"], set_code_value, printing["collector_number"]
        )

    click.echo()
    click.echo("New printing entry:")
    click.echo(yaml.safe_dump([printing], sort_keys=False, allow_unicode=True))

    if not click.confirm("Add this printing?", default=True):
        click.echo("Cancelled.")
        return

    # Load existing printings if file exists
    existing_printings: list[dict] = []
    if output.exists():
        with open(output, "r", encoding="utf-8") as f:
            existing_printings = yaml.safe_load(f) or []

    existing_printings.append(printing)
    existing_printings.sort(
        key=lambda p: (p.get("edition_id", ""), p.get("collector_number") or 9999, p.get("card_id", ""))
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    yaml_output = yaml.safe_dump(
        existing_printings,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    output.write_text(yaml_output, encoding="utf-8")
    click.echo(f"Wrote printing to {output}", err=True)
