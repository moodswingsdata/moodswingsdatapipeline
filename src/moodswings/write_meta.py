"""Write a meta file recording the schema version and output file hashes."""

import hashlib
from pathlib import Path

import click
import yaml

from moodswings.models import SCHEMA_VERSION


def _sha256(path: Path) -> str:
    """Return the hex SHA256 digest of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@click.command("write-meta")
@click.argument(
    "files",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output meta YAML file.",
)
def write_meta(files: tuple[Path, ...], output: Path):
    """Record the schema version and SHA256 hashes of output FILES.

    Produces a meta file capturing the current schema version and a SHA256
    digest for each input file, keyed by file name.
    """
    schema_version = ".".join(str(part) for part in SCHEMA_VERSION)

    file_hashes: dict[str, str] = {}
    for path in files:
        name = path.name
        if name in file_hashes:
            raise click.ClickException(f"Duplicate file name: {name}")
        file_hashes[name] = _sha256(path)

    meta = {
        "schema_version": schema_version,
        "files": file_hashes,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        yaml.dump(
            meta,
            f,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
    click.echo(f"Written to {output}", err=True)
