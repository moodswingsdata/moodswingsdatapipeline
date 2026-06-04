"""Prepare editions YAML for pipeline output."""

import uuid
from pathlib import Path

import click
import yaml

# Same namespace used for card IDs
MSDATA_NAMESPACE = uuid.UUID("f47ac10b-58cc-4372-a567-0d02b2c3d479")


def generate_edition_id(set_code: str) -> str:
    """Generate a stable edition ID (UUID5) from set_code (lowercased)."""
    return str(uuid.uuid5(MSDATA_NAMESPACE, set_code.lower()))


@click.command("prepare-editions")
@click.argument("editions_yaml", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output YAML file for editions.",
)
def prepare_editions(editions_yaml: Path, output: Path):
    """Read raw editions YAML, generate IDs, and write output (stripping data_sources)."""
    with open(editions_yaml, "r", encoding="utf-8") as f:
        raw_editions = yaml.safe_load(f)

    if not isinstance(raw_editions, list):
        raise click.ClickException(f"Expected a list in {editions_yaml}, got {type(raw_editions).__name__}")

    editions = []
    for entry in raw_editions:
        set_code = entry.get("set_code")
        if not set_code:
            raise click.ClickException(f"Edition entry missing 'set_code': {entry}")

        edition = {
            "id": generate_edition_id(set_code),
            "set_code": set_code,
            "edition_name": entry["name"],
            "release_date": entry["release_date"],
            "language": entry["language"],
        }
        editions.append(edition)

    output.parent.mkdir(parents=True, exist_ok=True)
    yaml_output = yaml.safe_dump(
        editions,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    output.write_text(yaml_output, encoding="utf-8")
    click.echo(f"Wrote {len(editions)} edition(s) to {output}", err=True)
