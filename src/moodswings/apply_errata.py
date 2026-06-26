"""Bake errata corrections into cards and printings YAML files.

Errata is fundamentally a printing-side notion: a physical printing's text can
differ from the card's oracle (canonical) text. Applying an erratum:

* corrects the oracle field (on the Card), and
* preserves the original printed text on the Printing (``printed_rules_text``),
* records a structured ``errata`` marker on the affected record so downstream
  apps can choose how to display the correction.

Errata files come in two flavours, auto-detected by their id key:

* keyed by ``card_id`` — corrects the card's oracle data directly.
* keyed by ``printing_id`` — the printed text differs from the oracle; the
  correction propagates to the card's oracle field while the original printed
  text is kept on the printing.

Each entry maps one or more field names to a correction block. A correction
block uses exactly one of two mutually-exclusive operations, chosen by key name
so the intent is unambiguous in the source file:

* ``corrected`` — **replace** the field's value wholesale (optionally guarded by
  an ``as_printed`` value that must match the current data)::

    - printing_id: 83974c7d-...
      rules_text:
        as_printed: "...gives it to you..."   # original (kept on the printing)
        corrected: "...give it to you..."      # oracle (written to the card)
        note: "Typo in the printed card."

* ``append`` — **add** one or more items to a list field (e.g. a card's
  ``notes``) without disturbing the existing items. Items already present are
  skipped, so re-running is idempotent::

    - card_id: 06f6dc87-...
      notes:
        append:
          - "An extra clarification from the designer."
        note: "Added per the designer; not yet on the publisher's website."

``append`` is only valid for list-valued, non-oracle fields. ``corrected`` and
``append`` may not both appear in the same correction block.
"""

from pathlib import Path

import click
import yaml

# Fields whose canonical value lives on the Card (the "oracle").
ORACLE_FIELDS = {"rules_text"}

# Maps an oracle field to the Printing field holding its as-printed value.
AS_PRINTED_FIELD = {"rules_text": "printed_rules_text"}


def _normalize(value: object) -> object:
    """Collapse runs of whitespace in strings so comparisons ignore wrapping."""
    if isinstance(value, str):
        return " ".join(value.split())
    return value


def _join_notes(notes: list[str | None]) -> str:
    """Join distinct, non-empty notes in order."""
    seen: list[str] = []
    for note in notes:
        if note and note not in seen:
            seen.append(note)
    return " ".join(seen)


def _field_blocks(entry: dict, id_key: str) -> dict:
    """Return the correction blocks of an entry, excluding its id key."""
    return {k: v for k, v in entry.items() if k != id_key}


def _correction_op(correction: object) -> tuple[str | None, str | None]:
    """Determine which operation a correction block requests.

    Returns ``(op, error)`` where ``op`` is ``"corrected"`` (replace) or
    ``"append"`` (extend a list), and ``error`` is a message when the block is
    malformed (the two keys are mutually exclusive and exactly one is required).
    """
    if not isinstance(correction, dict):
        return None, "correction must be a mapping."
    has_corrected = "corrected" in correction
    has_append = "append" in correction
    if has_corrected and has_append:
        return None, "use either 'corrected' (replace) or 'append', not both."
    if has_corrected:
        return "corrected", None
    if has_append:
        return "append", None
    return None, "correction must define 'corrected' or 'append'."


def _append_to_list_field(target: dict, field: str, additions: object) -> tuple[str | None, str | None]:
    """Append new items to a list field, skipping ones already present.

    Returns ``(status, error)`` where ``status`` is ``"applied"`` (items added)
    or ``"skipped"`` (all items already present), and ``error`` is set when the
    operation is invalid for this field.
    """
    if not isinstance(additions, list):
        return None, f"field '{field}': 'append' must be a list of items."
    current = target.get(field)
    if current is None:
        current = []
    if not isinstance(current, list):
        return None, f"field '{field}': cannot append to non-list value."
    existing = {_normalize(item) for item in current}
    new_items = [item for item in additions if _normalize(item) not in existing]
    if not new_items:
        return "skipped", None
    target[field] = current + new_items
    return "applied", None


def apply_card_errata(cards: list[dict], errata: list[dict]) -> tuple[int, int, list[str]]:
    """Apply card-keyed errata to cards in place.

    Returns ``(applied_count, skipped_count, warnings)``.
    """
    index = {c["id"]: c for c in cards if "id" in c}
    applied = skipped = 0
    warnings: list[str] = []

    for entry in errata:
        card = index.get(entry.get("card_id"))
        if card is None:
            warnings.append(f"Card '{entry.get('card_id')}' not found in data.")
            continue

        applied_fields: list[str] = []
        notes: list[str | None] = []

        for field, correction in _field_blocks(entry, "card_id").items():
            op, error = _correction_op(correction)
            if error is not None:
                warnings.append(f"Card '{card['id']}' field '{field}': {error}")
                continue

            if op == "append":
                status, append_error = _append_to_list_field(card, field, correction["append"])
                if append_error is not None:
                    warnings.append(f"Card '{card['id']}' {append_error}")
                    continue
                if status == "applied":
                    applied += 1
                else:
                    skipped += 1
                applied_fields.append(field)
                notes.append(correction.get("note"))
                continue

            corrected = correction["corrected"]
            current = card.get(field)
            if _normalize(current) == _normalize(corrected):
                skipped += 1
            elif "as_printed" in correction and _normalize(current) != _normalize(correction["as_printed"]):
                warnings.append(
                    f"Card '{card['id']}' field '{field}': expected as-printed "
                    f"'{correction['as_printed']}' but found '{current}'."
                )
                continue
            else:
                card[field] = corrected
                applied += 1

            applied_fields.append(field)
            notes.append(correction.get("note"))

        if applied_fields:
            card["errata"] = {"fields": sorted(set(applied_fields)), "note": _join_notes(notes)}

    return applied, skipped, warnings


def apply_printing_errata(
    cards: list[dict], printings: list[dict], errata: list[dict]
) -> tuple[int, int, list[str]]:
    """Apply printing-keyed errata to printings (and oracle fields on cards).

    Returns ``(applied_count, skipped_count, warnings)``.
    """
    cards_by_id = {c["id"]: c for c in cards if "id" in c}
    index = {p["id"]: p for p in printings if p.get("id")}
    applied = skipped = 0
    warnings: list[str] = []

    for entry in errata:
        printing = index.get(entry.get("printing_id"))
        if printing is None:
            warnings.append(f"Printing '{entry.get('printing_id')}' not found in data.")
            continue

        card = cards_by_id.get(printing.get("card_id"))
        applied_fields: list[str] = []
        notes: list[str | None] = []

        for field, correction in _field_blocks(entry, "printing_id").items():
            op, error = _correction_op(correction)
            if error is not None:
                warnings.append(f"Printing '{printing['id']}' field '{field}': {error}")
                continue

            if op == "append":
                if field in ORACLE_FIELDS:
                    warnings.append(
                        f"Printing '{printing['id']}' field '{field}': 'append' is not "
                        f"supported for oracle fields."
                    )
                    continue
                status, append_error = _append_to_list_field(printing, field, correction["append"])
                if append_error is not None:
                    warnings.append(f"Printing '{printing['id']}' {append_error}")
                    continue
                if status == "applied":
                    applied += 1
                else:
                    skipped += 1
                applied_fields.append(field)
                notes.append(correction.get("note"))
                continue

            corrected = correction["corrected"]
            as_printed = correction.get("as_printed")

            if field in ORACLE_FIELDS:
                if card is None:
                    warnings.append(
                        f"Printing '{printing['id']}': card '{printing.get('card_id')}' "
                        f"not found; cannot correct oracle field '{field}'."
                    )
                    continue
                printed_field = AS_PRINTED_FIELD[field]
                card_current = card.get(field)
                printed_value = as_printed if as_printed is not None else card_current

                if as_printed is not None:
                    already = (
                        _normalize(printing.get(printed_field)) == _normalize(as_printed)
                        and _normalize(card_current) == _normalize(corrected)
                    )
                else:
                    already = (
                        printing.get(printed_field) is not None
                        and _normalize(card_current) == _normalize(corrected)
                    )
                if already:
                    skipped += 1
                elif (
                    as_printed is not None
                    and _normalize(card_current) != _normalize(as_printed)
                    and _normalize(card_current) != _normalize(corrected)
                ):
                    warnings.append(
                        f"Printing '{printing['id']}' field '{field}': card oracle is "
                        f"neither the as-printed nor corrected value (found '{card_current}')."
                    )
                    continue
                else:
                    printing[printed_field] = printed_value
                    card[field] = corrected
                    applied += 1
            else:
                current = printing.get(field)
                if _normalize(current) == _normalize(corrected):
                    skipped += 1
                elif as_printed is not None and _normalize(current) != _normalize(as_printed):
                    warnings.append(
                        f"Printing '{printing['id']}' field '{field}': expected as-printed "
                        f"'{as_printed}' but found '{current}'."
                    )
                    continue
                else:
                    printing[field] = corrected
                    applied += 1

            applied_fields.append(field)
            notes.append(correction.get("note"))

        if applied_fields:
            printing["errata"] = {"fields": sorted(set(applied_fields)), "note": _join_notes(notes)}

    return applied, skipped, warnings


def _dump(data: list[dict], path: Path) -> None:
    yaml_output = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml_output, encoding="utf-8")


@click.command("apply-errata")
@click.argument("cards_file", type=click.Path(exists=True, path_type=Path))
@click.argument("printings_file", type=click.Path(exists=True, path_type=Path))
@click.argument("errata_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--cards-out",
    type=click.Path(path_type=Path),
    required=True,
    help="Output YAML file for the corrected cards.",
)
@click.option(
    "--printings-out",
    type=click.Path(path_type=Path),
    required=True,
    help="Output YAML file for the corrected printings.",
)
def apply_errata(cards_file: Path, printings_file: Path, errata_file: Path, cards_out: Path, printings_out: Path):
    """Bake errata from ERRATA_FILE into CARDS_FILE and PRINTINGS_FILE.

    The errata file is a YAML list keyed by ``card_id`` or ``printing_id`` (the
    two keys may not be mixed in one file). Card-keyed errata correct the card's
    oracle data. Printing-keyed errata preserve the printed text on the printing
    while correcting the corresponding oracle field on the card.
    """
    with open(cards_file, "r", encoding="utf-8") as f:
        cards = yaml.safe_load(f) or []
    with open(printings_file, "r", encoding="utf-8") as f:
        printings = yaml.safe_load(f) or []
    with open(errata_file, "r", encoding="utf-8") as f:
        errata = yaml.safe_load(f) or []

    if not isinstance(errata, list):
        raise click.ClickException("Errata file must contain a YAML list.")

    has_card_ids = any("card_id" in entry for entry in errata)
    has_printing_ids = any("printing_id" in entry for entry in errata)

    if has_card_ids and has_printing_ids:
        raise click.ClickException(
            "Errata file mixes card_id and printing_id. "
            "Use separate errata files for cards and printings."
        )
    if errata and not has_card_ids and not has_printing_ids:
        raise click.ClickException(
            "Each errata entry must have either a 'card_id' or 'printing_id' field."
        )

    if has_card_ids:
        applied, skipped, warnings = apply_card_errata(cards, errata)
    else:
        applied, skipped, warnings = apply_printing_errata(cards, printings, errata)

    for warning in warnings:
        click.echo(f"WARNING: {warning}", err=True)

    _dump(cards, cards_out)
    _dump(printings, printings_out)
    click.echo(
        f"Applied {applied} erratum field(s), skipped {skipped} already-corrected, "
        f"{len(warnings)} warning(s). Cards: {cards_out}, printings: {printings_out}",
        err=True,
    )
