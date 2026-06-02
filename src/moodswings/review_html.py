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
<title>Mood Swings Set Review</title>
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
.controls {{
    max-width: 1200px;
    margin: 0 auto 20px;
    padding: 12px 20px;
    background: #16213e;
    border-radius: 8px;
    border: 1px solid #0f3460;
    display: flex;
    align-items: center;
    gap: 12px;
}}
.controls label {{
    color: #a8d8ea;
    font-weight: 600;
}}
.controls select {{
    padding: 6px 12px;
    border-radius: 6px;
    border: 1px solid #0f3460;
    background: #1a1a2e;
    color: #eee;
    font-size: 14px;
    cursor: pointer;
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
<div class="controls">
<label for="sort-select">Sort by:</label>
<select id="sort-select">
<option value="name">Name (A&ndash;Z)</option>
<option value="collector_number">Collector Number</option>
<option value="color">Color</option>
<option value="frame">Frame</option>
<option value="rarity">Rarity</option>
<option value="reminder_icon">Reminder Icon</option>
<option value="dice_value">Dice Value</option>
<option value="secondary_dice_value">Secondary Dice Value</option>
<option value="treatment">Treatment</option>
</select>
</div>
<div class="card-grid" id="card-grid">
{cards_html}
</div>
<script>
(function() {{
    const grid = document.getElementById("card-grid");
    const select = document.getElementById("sort-select");

    const colorOrder = {{"white": 0, "blue": 1, "black": 2, "red": 3, "green": 4}};
    const rarityOrder = {{"common": 0, "uncommon": 1, "rare": 2, "mythic": 3}};

    function sortCards(key) {{
        const entries = Array.from(grid.querySelectorAll(".card-entry"));
        entries.sort(function(a, b) {{
            let av = a.dataset[key] || "";
            let bv = b.dataset[key] || "";
            if (key === "collector_number" || key === "dice_value" || key === "secondary_dice_value") {{
                let an = parseInt(av) || 0;
                let bn = parseInt(bv) || 0;
                if (an === 0 && av === "") an = 9999;
                if (bn === 0 && bv === "") bn = 9999;
                return an - bn;
            }}
            if (key === "color") {{
                return (colorOrder[av.toLowerCase()] ?? 99) - (colorOrder[bv.toLowerCase()] ?? 99);
            }}
            if (key === "rarity") {{
                return (rarityOrder[av.toLowerCase()] ?? 99) - (rarityOrder[bv.toLowerCase()] ?? 99);
            }}
            return av.localeCompare(bv);
        }});
        entries.forEach(function(el) {{ grid.appendChild(el); }});
    }}

    select.addEventListener("change", function() {{ sortCards(this.value); }});
}})();
</script>
</body>
</html>
"""

CARD_TEMPLATE = """\
<div class="card-entry" id="card-{collector_number}" data-name="{name}" data-collector_number="{collector_number}" data-color="{color}" data-frame="{frame}" data-rarity="{rarity}" data-reminder_icon="{reminder_icon}" data-dice_value="{dice_value}" data-secondary_dice_value="{secondary_dice_value}" data-treatment="{treatment}">
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


def render_card(card: dict, printing: dict, image_dir: Path | None) -> str:
    """Render a single card entry as HTML."""
    # Merge card + printing for display
    merged = {**card, **printing}
    collector_number = merged.get("collector_number", 0)
    name = escape_html(merged.get("name", "Unknown"))
    color = escape_html(str(merged.get("color", "")))
    frame = escape_html(str(merged.get("frame", "")))
    rarity = escape_html(str(merged.get("rarity", "")))
    reminder_icon = escape_html(str(merged.get("reminder_icon") or ""))
    dice_value = merged.get("dice_value") if merged.get("dice_value") is not None else ""
    secondary_dice_value = merged.get("secondary_dice_value") if merged.get("secondary_dice_value") is not None else ""
    treatment = escape_html(str(merged.get("treatment") or ""))

    # Determine image source
    if image_dir:
        safe_name = card["name"].lower().replace(" ", "_").replace("'", "")
        found = False
        for f in sorted(image_dir.iterdir()):
            parts = f.stem.split("_", 1)
            if len(parts) == 2 and parts[0].isdigit() and parts[1] == safe_name:
                image_src = str(f)
                found = True
                break
        if not found:
            image_src = merged.get("card_image_url", "")
    else:
        image_src = merged.get("card_image_url", "")

    # Build table rows for all fields
    skip_fields = {"name", "collector_number"}
    rows = ""
    for key, value in merged.items():
        if key in skip_fields:
            continue
        rows += f"<tr><td>{escape_html(key)}</td><td>{format_value(key, value)}</td></tr>\n"

    return CARD_TEMPLATE.format(
        collector_number=collector_number,
        name=name,
        color=color,
        frame=frame,
        rarity=rarity,
        reminder_icon=reminder_icon,
        dice_value=dice_value,
        secondary_dice_value=secondary_dice_value,
        treatment=treatment,
        image_src=image_src,
        rows=rows,
    )


@click.command("review-html")
@click.argument("cards_yaml", type=click.Path(exists=True, path_type=Path))
@click.argument("printings_yaml", type=click.Path(exists=True, path_type=Path))
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
def review_html(cards_yaml: Path, printings_yaml: Path, output: Path, image_dir: Path | None):
    """Generate a static HTML page for reviewing card data."""
    with open(cards_yaml, "r", encoding="utf-8") as f:
        cards = yaml.safe_load(f)
    with open(printings_yaml, "r", encoding="utf-8") as f:
        printings = yaml.safe_load(f)

    if not cards or not printings:
        raise click.ClickException("No data found in YAML files.")

    # Match printings to cards by id
    printing_by_id = {p["card-id"]: p for p in printings}

    cards_html = "\n".join(
        render_card(card, printing_by_id.get(card["id"], {}), image_dir)
        for card in cards
    )

    html = HTML_TEMPLATE.format(card_count=len(cards), cards_html=cards_html)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    click.echo(f"Written {len(cards)} cards to {output}", err=True)
