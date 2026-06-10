"""Merge two or more printings YAML files into a single output."""

from pathlib import Path

import click
import yaml

from moodswings.extract import generate_printing_id


def resolve_printing(entry: dict, cards: list[dict], editions: list[dict]) -> dict:
    """Resolve a printing entry that uses name/set_code into one with IDs.

    If the entry already has card_id and edition_id, those are kept as-is.
    If it has name/set_code, those are resolved to IDs.
    """
    # If already resolved (has card_id), pass through
    if "card_id" in entry and "edition_id" in entry and entry.get("id"):
        return entry

    card_name = entry.get("name")
    if card_name:
        card = None
        for c in cards:
            if c["name"].lower() == card_name.lower():
                card = c
                break
        if card is None:
            raise click.ClickException(f"Card '{card_name}' not found in cards YAML.")
        entry["card_id"] = card["id"]

    set_code = entry.get("set_code")
    if set_code and "edition_id" not in entry:
        edition = None
        for ed in editions:
            if ed["set_code"].lower() == set_code.lower():
                edition = ed
                break
        if edition is None:
            raise click.ClickException(
                f"Set code '{set_code}' not found in editions. "
                f"Available: {', '.join(e['set_code'] for e in editions)}"
            )
        entry["edition_id"] = edition["id"]

    # Generate ID if missing
    if not entry.get("id") and entry.get("collector_number") is not None and set_code:
        name = card_name or next(
            (c["name"] for c in cards if c["id"] == entry.get("card_id")), None
        )
        if name:
            entry["id"] = generate_printing_id(name, set_code, entry["collector_number"])

    # Handle artist splitting
    artist = entry.get("artist")
    if isinstance(artist, str) and "&" in artist:
        entry["artist"] = [a.strip() for a in artist.split("&") if a.strip()]

    # Clean up input-only fields that don't belong in output
    entry.pop("set_code", None)

    return entry


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


@click.command("merge-printings")
@click.argument("printings_files", nargs=-1, required=True, type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output YAML file for merged printings.",
)
@click.option(
    "--cards",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Cards YAML file (for resolving name references).",
)
@click.option(
    "--editions",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Editions YAML file (for resolving set_code references).",
)
def merge_printings(printings_files: tuple[Path, ...], output: Path, cards: Path, editions: Path):
    """Merge two or more printings YAML files into OUTPUT.

    Input files may contain either resolved printings (with card_id/edition_id)
    or unresolved entries (with name/set_code that get resolved).

    Printings are deduplicated by ID (first occurrence wins) and sorted by
    edition ID then collector number. Requires at least two input files.
    """
    if len(printings_files) < 2:
        raise click.ClickException("At least two input files are required.")

    with open(cards, "r", encoding="utf-8") as f:
        cards_data = yaml.safe_load(f)

    with open(editions, "r", encoding="utf-8") as f:
        editions_data = yaml.safe_load(f)

    seen_ids: dict[str, dict] = {}
    for path in printings_files:
        entries = load_printings_from_path(path)
        for entry in entries:
            printing = resolve_printing(entry, cards_data, editions_data)
            printing_id = printing.get("id")
            if printing_id and printing_id not in seen_ids:
                seen_ids[printing_id] = printing
            elif printing_id in seen_ids:
                click.echo(
                    f"  Skipping duplicate printing '{printing_id}' from {path}",
                    err=True,
                )
            else:
                # No ID — append anyway (shouldn't normally happen)
                seen_ids[id(printing)] = printing

    merged = sorted(
        seen_ids.values(),
        key=lambda p: (p.get("edition_id", ""), p.get("collector_number") or 9999, p.get("card_id", "")),
    )

    yaml_output = yaml.safe_dump(
        merged,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml_output, encoding="utf-8")
    click.echo(f"Merged {len(merged)} printing(s) into {output}", err=True)
