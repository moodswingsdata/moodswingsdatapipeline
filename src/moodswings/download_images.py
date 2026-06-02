"""Download card images from URLs in the printings YAML file."""

from pathlib import Path

import click
import httpx
import yaml


@click.command("download-images")
@click.argument("cards_yaml", type=click.Path(exists=True, path_type=Path))
@click.argument("printings_yaml", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("raw_data/card_images"),
    help="Directory to save card images. Default: raw_data/card_images",
)
def download_images(cards_yaml: Path, printings_yaml: Path, output_dir: Path):
    """Download card images referenced in the printings YAML file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(cards_yaml, "r", encoding="utf-8") as f:
        cards = yaml.safe_load(f)
    with open(printings_yaml, "r", encoding="utf-8") as f:
        printings = yaml.safe_load(f)

    if not cards or not printings:
        click.echo("No data found in YAML files.", err=True)
        return

    # Build id-to-name lookup
    id_to_name = {card["id"]: card["name"] for card in cards}

    downloaded = 0
    skipped = 0

    with httpx.Client(timeout=30.0) as client:
        for idx, printing in enumerate(printings, 1):
            url = printing.get("card_image_url")
            card_name = id_to_name.get(printing["card_id"], "unknown")
            if not url:
                click.echo(f"  Skipping {card_name}: no image URL", err=True)
                skipped += 1
                continue

            safe_name = card_name.lower().replace(" ", "_").replace("'", "")
            ext = Path(url).suffix or ".webp"
            filename = f"{idx:03d}_{safe_name}{ext}"
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
                click.echo(f"  Error downloading {card_name}: {e}", err=True)
                skipped += 1

    click.echo(f"Done: {downloaded} downloaded, {skipped} skipped", err=True)
