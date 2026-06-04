"""Generate a static HTML review page for card data."""

import os
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
.errata-section {{
    margin-top: 12px;
}}
.errata-section summary {{
    cursor: pointer;
    color: #e9a345;
    font-weight: 600;
    font-size: 13px;
}}
.errata-section .errata-item {{
    margin: 8px 0;
    padding: 8px 12px;
    background: #1a1a2e;
    border-left: 3px solid #e9a345;
    border-radius: 4px;
    font-size: 13px;
}}
.errata-section .errata-note {{
    color: #e9a345;
    font-style: italic;
}}
.errata-section .errata-printed {{
    color: #aaa;
    margin-top: 4px;
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
{errata_html}
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


def apply_errata(merged: dict, errata: dict | None) -> dict:
    """Apply errata corrections to the merged card/printing data."""
    if not errata:
        return merged
    for field_name, info in errata.items():
        if field_name == "printing_id":
            continue
        if isinstance(info, dict) and "corrected" in info:
            merged[field_name] = info["corrected"]
    return merged


def render_errata(errata: dict | None) -> str:
    """Render errata as a collapsed details/summary section."""
    if not errata:
        return ""

    # Skip the printing_id field, render the rest
    fields = {k: v for k, v in errata.items() if k != "printing_id"}
    if not fields:
        return ""

    items = ""
    for field_name, info in fields.items():
        note = info.get("note", "")
        as_printed = info.get("as_printed", "")
        corrected = info.get("corrected", "")
        items += '<div class="errata-item">'
        items += f'<div class="errata-note">Note ({escape_html(field_name)}): {escape_html(note)}</div>'
        items += f'<div class="errata-printed">As printed: {escape_html(str(as_printed))}</div>'
        items += f'<div class="errata-printed">Corrected: {escape_html(str(corrected))}</div>'
        items += "</div>\n"

    return (
        '<details class="errata-section">\n'
        "<summary>Errata</summary>\n"
        f"{items}"
        "</details>"
    )


def render_card(card: dict, printing: dict, image_dir: Path | None, cardback_path: Path | None, errata: dict | None = None, output_dir: Path | None = None) -> str:
    """Render a single card entry as HTML."""
    # Merge card + printing for display
    merged = {**card, **printing}
    # Apply errata corrections to displayed values
    merged = apply_errata(merged, errata)
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
    image_src = ""
    if image_dir:
        safe_name = card["name"].lower().replace(" ", "_").replace("'", "")
        found = False
        # Only look for a local file if this printing is expected to have an image
        if merged.get("card_image_url"):
            for f in sorted(image_dir.iterdir()):
                parts = f.stem.split("_", 1)
                if len(parts) == 2 and parts[0].isdigit() and parts[1] == safe_name:
                    if output_dir:
                        image_src = str(Path(os.path.relpath(f, output_dir)))
                    else:
                        image_src = str(f)
                    found = True
                    break
        if not found:
            if cardback_path:
                if output_dir:
                    image_src = str(Path(os.path.relpath(cardback_path, output_dir)))
                else:
                    image_src = str(cardback_path)
            else:
                image_src = merged.get("card_image_url") or ""
    else:
        image_src = merged.get("card_image_url") or ""
        if not image_src and cardback_path:
            if output_dir:
                image_src = str(Path(os.path.relpath(cardback_path, output_dir)))
            else:
                image_src = str(cardback_path)

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
        errata_html=render_errata(errata),
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
    "--editions",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Editions YAML file (output of prepare-editions). Used to resolve edition names.",
)
@click.option(
    "--image-dir",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Local image directory. If provided, images are referenced locally.",
)
@click.option(
    "--cardback",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Fallback image for printings without a card image. Defaults to raw_data/cardback.png if it exists.",
)
@click.option(
    "--errata",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Errata YAML file with corrections keyed by printing_id.",
)
def review_html(cards_yaml: Path, printings_yaml: Path, output: Path, editions: Path | None, image_dir: Path | None, cardback: Path | None, errata: Path | None):
    """Generate a static HTML page for reviewing card data."""
    # Resolve cardback fallback
    if cardback is None:
        default_cardback = Path("raw_data/cardback.png")
        if default_cardback.exists():
            cardback = default_cardback

    # Resolve paths so relative path computation works correctly
    if image_dir:
        image_dir = image_dir.resolve()
    if cardback:
        cardback = cardback.resolve()

    with open(cards_yaml, "r", encoding="utf-8") as f:
        cards = yaml.safe_load(f)
    with open(printings_yaml, "r", encoding="utf-8") as f:
        printings = yaml.safe_load(f)

    if not cards or not printings:
        raise click.ClickException("No data found in YAML files.")

    # Load errata if provided
    errata_by_printing: dict[str, dict] = {}
    if errata:
        with open(errata, "r", encoding="utf-8") as f:
            errata_list = yaml.safe_load(f) or []
        for entry in errata_list:
            pid = entry.get("printing_id")
            if pid:
                errata_by_printing[pid] = entry

    # Build card lookup by id
    card_by_id = {card["id"]: card for card in cards}

    # Iterate over printings (one entry per printing, even if same card)
    output_dir = output.parent.resolve()
    cards_html = "\n".join(
        render_card(card_by_id[p["card_id"]], p, image_dir, cardback, errata_by_printing.get(p.get("id")), output_dir)
        for p in printings
        if p["card_id"] in card_by_id
    )

    html = HTML_TEMPLATE.format(card_count=len(printings), cards_html=cards_html)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    click.echo(f"Written {len(printings)} printings to {output}", err=True)
