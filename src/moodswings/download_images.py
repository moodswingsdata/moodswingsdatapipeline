"""Download card images from URLs extracted from the HTML file."""

from pathlib import Path

import click
import httpx
import yaml


@click.command("download-images")
@click.argument("yaml_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("raw_data/card_images"),
    help="Directory to save card images. Default: raw_data/card_images",
)
def download_images(yaml_file: Path, output_dir: Path):
    """Download card images referenced in the extracted YAML file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(yaml_file, "r", encoding="utf-8") as f:
        cards = yaml.safe_load(f)

    if not cards:
        click.echo("No cards found in YAML file.", err=True)
        return

    downloaded = 0
    skipped = 0

    with httpx.Client(timeout=30.0) as client:
        for card in cards:
            url = card.get("card_image_url")
            if not url:
                click.echo(f"  Skipping {card['name']}: no image URL", err=True)
                skipped += 1
                continue

            # Use collector number and name for a safe filename
            collector_num = card["collector_number"]
            safe_name = card["name"].lower().replace(" ", "_").replace("'", "")
            ext = Path(url).suffix or ".webp"
            filename = f"{collector_num:03d}_{safe_name}{ext}"
            filepath = output_dir / filename

            if filepath.exists():
                click.echo(f"  Exists: {filename}", err=True)
                skipped += 1
                continue

            click.echo(f"  Downloading: {filename}", err=True)
            try:
                resp = client.get(url, follow_redirects=True)
                resp.raise_for_status()
                filepath.write_bytes(resp.content)
                downloaded += 1
            except httpx.HTTPError as e:
                click.echo(f"  Error downloading {card['name']}: {e}", err=True)
                skipped += 1

    click.echo(f"Done: {downloaded} downloaded, {skipped} skipped", err=True)
