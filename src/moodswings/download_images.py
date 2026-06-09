"""Download card images from URLs in the printings YAML file."""

import json
from pathlib import Path

import click
import httpx
import yaml


IMAGE_MAP_FILENAME = "image_map.json"


@click.command("download-images")
@click.argument("cards_yaml", type=click.Path(exists=True, path_type=Path))
@click.argument("printings_yaml", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    required=True,
    help="Directory to save card images.",
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

    # Load existing image map if present
    map_path = output_dir / IMAGE_MAP_FILENAME
    if map_path.exists():
        with open(map_path, "r", encoding="utf-8") as f:
            image_map: dict[str, str] = json.load(f)
    else:
        image_map = {}

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
                # Ensure map is up to date even for existing files
                image_map[url] = filename
                skipped += 1
                continue

            click.echo(f"  Downloading: {filename}", err=True)
            try:
                resp = client.get(url, follow_redirects=True)
                resp.raise_for_status()
                filepath.write_bytes(resp.content)
                image_map[url] = filename
                downloaded += 1
            except httpx.HTTPError as e:
                click.echo(f"  Error downloading {card_name}: {e}", err=True)
                skipped += 1

    # Write the image map
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(image_map, f, indent=2, sort_keys=True)
        f.write("\n")

    click.echo(f"Done: {downloaded} downloaded, {skipped} skipped", err=True)
