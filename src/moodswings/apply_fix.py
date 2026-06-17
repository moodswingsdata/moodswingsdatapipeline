"""Apply manual fixes to cards or printings YAML files."""

from pathlib import Path

import click
import yaml


def apply_fixes(data: list[dict], fixes: list[dict], id_field: str) -> tuple[int, int, list[str]]:
    """Apply a list of fixes to data records.

    Returns (applied_count, skipped_count, warnings).
    """
    index = {record[id_field]: record for record in data if id_field in record}

    applied = 0
    skipped = 0
    warnings: list[str] = []

    for fix in fixes:
        record_id = fix[id_field]
        field = fix["field_name"]
        old_value = fix["old"]
        new_value = fix["new"]

        record = index.get(record_id)
        if record is None:
            warnings.append(f"Record '{record_id}' not found in data.")
            continue

        current = record.get(field)
        if current == old_value:
            record[field] = new_value
            applied += 1
        elif current == new_value:
            skipped += 1
        else:
            warnings.append(
                f"Record '{record_id}' field '{field}': "
                f"expected '{old_value}' but found '{current}'."
            )

    return applied, skipped, warnings


@click.command("apply-fix")
@click.argument("data_file", type=click.Path(exists=True, path_type=Path))
@click.argument("fixes_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output YAML file for the fixed data.",
)
def apply_fix(data_file: Path, fixes_file: Path, output: Path):
    """Apply manual fixes from FIXES_FILE to DATA_FILE.

    DATA_FILE is a cards or printings YAML file. FIXES_FILE is a YAML list
    of fix objects. Each fix has a card_id or printing_id, a field_name, an
    old value, and a new value.
    """
    with open(data_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []

    with open(fixes_file, "r", encoding="utf-8") as f:
        fixes = yaml.safe_load(f) or []

    if not isinstance(fixes, list):
        raise click.ClickException("Fixes file must contain a YAML list.")

    # Determine whether fixes target cards or printings
    has_card_ids = any("card_id" in fix for fix in fixes)
    has_printing_ids = any("printing_id" in fix for fix in fixes)

    if has_card_ids and has_printing_ids:
        raise click.ClickException(
            "Fixes file mixes card_id and printing_id. "
            "Use separate fix files for cards and printings."
        )

    if not has_card_ids and not has_printing_ids:
        raise click.ClickException(
            "Each fix must have either a 'card_id' or 'printing_id' field."
        )

    id_field = "card_id" if has_card_ids else "printing_id"
    # In the data file, the id field is just "id"
    # Remap fix id references to match
    for fix in fixes:
        fix["id"] = fix.pop(id_field)

    applied, skipped, warnings = apply_fixes(data, fixes, "id")

    for warning in warnings:
        click.echo(f"WARNING: {warning}", err=True)

    yaml_output = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml_output, encoding="utf-8")
    click.echo(
        f"Applied {applied} fix(es), skipped {skipped} already-applied, "
        f"{len(warnings)} warning(s). Output: {output}",
        err=True,
    )
