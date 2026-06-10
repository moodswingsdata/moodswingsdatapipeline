"""Merge two or more cards YAML files into a single output."""

from pathlib import Path

import click
import yaml


@click.command("merge-cards")
@click.argument("cards_files", nargs=-1, required=True, type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output YAML file for merged cards.",
)
def merge_cards(cards_files: tuple[Path, ...], output: Path):
    """Merge two or more cards YAML files into OUTPUT.

    Cards are deduplicated by ID (first occurrence wins) and sorted by name.
    Requires at least two input files.
    """
    if len(cards_files) < 2:
        raise click.ClickException("At least two input files are required.")

    seen_ids: dict[str, dict] = {}
    for path in cards_files:
        with open(path, "r", encoding="utf-8") as f:
            cards = yaml.safe_load(f) or []
        for card in cards:
            card_id = card.get("id")
            if card_id and card_id not in seen_ids:
                seen_ids[card_id] = card
            elif card_id in seen_ids:
                click.echo(
                    f"  Skipping duplicate '{card.get('name', card_id)}' from {path}",
                    err=True,
                )

    merged = sorted(seen_ids.values(), key=lambda c: c.get("name", "").lower())

    yaml_output = yaml.safe_dump(
        merged,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml_output, encoding="utf-8")
    click.echo(f"Merged {len(merged)} card(s) into {output}", err=True)
