"""Convert a YAML file to JSON."""

import json
from pathlib import Path

import click
import yaml


@click.command("to-json")
@click.argument("yaml_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output JSON file. Defaults to stdout.",
)
def to_json(yaml_file: Path, output: Path | None):
    """Convert a YAML file to JSON."""
    with open(yaml_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    json_str = json.dumps(data, ensure_ascii=False, default=str)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json_str + "\n", encoding="utf-8")
        click.echo(f"Written to {output}", err=True)
    else:
        click.echo(json_str)
