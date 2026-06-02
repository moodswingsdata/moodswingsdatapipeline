"""Generate a static HTML review page for card data."""

from pathlib import Path

import click
import yaml


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mood Swings Card Review</title>
<style>
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 0;
    padding: 20px;
    background: #1a1a2e;
    color: #eee;
}}
h1 {{
    text-align: center;
    color: #fff;
}}
.card-grid {{
    max-width: 1200px;
    margin: 0 auto;
}}
.card-entry {{
    display: flex;
    gap: 24px;
    margin-bottom: 32px;
    padding: 20px;
    background: #16213e;
    border-radius: 12px;
    border: 1px solid #0f3460;
}}
.card-image {{
    flex-shrink: 0;
}}
.card-image img {{
    width: 265px;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}}
.card-data {{
    flex: 1;
    min-width: 0;
}}
.card-data h2 {{
    margin: 0 0 12px;
    color: #e94560;
}}
.card-data table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}}
.card-data td {{
    padding: 4px 8px;
    vertical-align: top;
    border-bottom: 1px solid #0f3460;
}}
.card-data td:first-child {{
    font-weight: 600;
    white-space: nowrap;
    width: 160px;
    color: #a8d8ea;
}}
.card-data td:last-child {{
    word-break: break-word;
}}
.rules-text {{
    font-family: Georgia, serif;
    font-style: italic;
    line-height: 1.4;
}}
.rulings li {{
    margin-bottom: 4px;
    font-size: 13px;
    color: #ccc;
}}
</style>
</head>
<body>
<h1>Mood Swings Card Review ({card_count} cards)</h1>
<div class="card-grid">
{cards_html}
</div>
</body>
</html>
"""

CARD_TEMPLATE = """\
<div class="card-entry" id="card-{collector_number}">
<div class="card-image">
<img src="{image_src}" alt="{name}" loading="lazy">
</div>
<div class="card-data">
<h2>#{collector_number} &mdash; {name}</h2>
<table>
{rows}
</table>
</div>
</div>
"""


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def format_value(key: str, value) -> str:
    """Format a card field value for HTML display."""
    if value is None:
        return '<span style="color:#666">null</span>'
    if key == "rules_text":
        # Show the raw HTML markup as-is (it's meant to include markup)
        return f'<span class="rules-text">{value}</span>'
    if key == "rulings_text" and isinstance(value, list):
        items = "".join(f"<li>{escape_html(item)}</li>" for item in value)
        return f'<ul class="rulings">{items}</ul>'
    if key == "card_image_url":
        escaped = escape_html(str(value))
        return f'<a href="{escaped}" style="color:#a8d8ea">{escaped}</a>'
    return escape_html(str(value))


def render_card(card: dict, image_dir: Path | None) -> str:
    """Render a single card entry as HTML."""
    collector_number = card.get("collector_number", 0)
    name = escape_html(card.get("name", "Unknown"))

    # Determine image source
    if image_dir:
        safe_name = card["name"].lower().replace(" ", "_").replace("'", "")
        for ext in [".webp", ".png", ".jpg"]:
            img_path = image_dir / f"{collector_number:03d}_{safe_name}{ext}"
            if img_path.exists():
                image_src = str(img_path)
                break
        else:
            image_src = card.get("card_image_url", "")
    else:
        image_src = card.get("card_image_url", "")

    # Build table rows for all fields
    skip_fields = {"name", "collector_number"}
    rows = ""
    for key, value in card.items():
        if key in skip_fields:
            continue
        rows += f"<tr><td>{escape_html(key)}</td><td>{format_value(key, value)}</td></tr>\n"

    return CARD_TEMPLATE.format(
        collector_number=collector_number,
        name=name,
        image_src=image_src,
        rows=rows,
    )


@click.command("review-html")
@click.argument("yaml_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output HTML file path.",
)
@click.option(
    "--image-dir",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Local image directory. If provided, images are referenced locally.",
)
def review_html(yaml_file: Path, output: Path, image_dir: Path | None):
    """Generate a static HTML page for reviewing card data."""
    with open(yaml_file, "r", encoding="utf-8") as f:
        cards = yaml.safe_load(f)

    if not cards:
        raise click.ClickException("No cards found in YAML file.")

    cards_html = "\n".join(render_card(card, image_dir) for card in cards)

    html = HTML_TEMPLATE.format(card_count=len(cards), cards_html=cards_html)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    click.echo(f"Written {len(cards)} cards to {output}", err=True)
