"""Lint edition, card, and printing YAML files for common issues."""

from pathlib import Path

import click
import yaml


def lint_editions(data: list[dict], path: str, errors: list[str]) -> None:
    """Check edition YAML for issues."""
    seen_ids: dict[str, int] = {}
    seen_names: dict[str, int] = {}
    seen_set_codes: dict[str, int] = {}

    for idx, entry in enumerate(data, 1):
        entry_id = entry.get("id")
        name = entry.get("edition_name") or entry.get("name")
        set_code = entry.get("set_code")

        if entry_id:
            if entry_id in seen_ids:
                errors.append(f"{path}: duplicate edition id '{entry_id}' at entries {seen_ids[entry_id]} and {idx}")
            else:
                seen_ids[entry_id] = idx

        if name:
            key = name.lower()
            if key in seen_names:
                errors.append(f"{path}: duplicate edition name '{name}' at entries {seen_names[key]} and {idx}")
            else:
                seen_names[key] = idx

        if set_code:
            key = set_code.lower()
            if key in seen_set_codes:
                errors.append(f"{path}: duplicate set_code '{set_code}' at entries {seen_set_codes[key]} and {idx}")
            else:
                seen_set_codes[key] = idx


def lint_cards(data: list[dict], path: str, errors: list[str]) -> None:
    """Check cards YAML for issues."""
    seen_ids: dict[str, int] = {}
    seen_names: dict[str, int] = {}
    prev_name: str | None = None

    for idx, entry in enumerate(data, 1):
        entry_id = entry.get("id")
        name = entry.get("name")

        if entry_id:
            if entry_id in seen_ids:
                errors.append(f"{path}: duplicate card id '{entry_id}' at entries {seen_ids[entry_id]} and {idx}")
            else:
                seen_ids[entry_id] = idx

        if name:
            key = name.lower()
            if key in seen_names:
                errors.append(f"{path}: duplicate card name '{name}' at entries {seen_names[key]} and {idx}")
            else:
                seen_names[key] = idx

            if prev_name is not None and key < prev_name:
                errors.append(f"{path}: cards not sorted by name: '{name}' (entry {idx}) comes after '{data[idx-2]['name']}' (entry {idx-1})")
            prev_name = key


def lint_printings(data: list[dict], path: str, errors: list[str]) -> None:
    """Check printings YAML for issues."""
    seen_ids: dict[str, int] = {}
    prev_sort_key: tuple[int, str] | None = None

    for idx, entry in enumerate(data, 1):
        entry_id = entry.get("id")

        if entry_id:
            if entry_id in seen_ids:
                errors.append(f"{path}: duplicate printing id '{entry_id}' at entries {seen_ids[entry_id]} and {idx}")
            else:
                seen_ids[entry_id] = idx

        collector_number = entry.get("collector_number") or 9999
        card_id = entry.get("card_id", "")
        sort_key = (collector_number, card_id)

        if prev_sort_key is not None and sort_key < prev_sort_key:
            errors.append(
                f"{path}: printings not sorted by collector_number: "
                f"entry {idx} (#{collector_number}) comes after entry {idx-1} (#{prev_sort_key[0]})"
            )
        prev_sort_key = sort_key


@click.command("lint")
@click.option(
    "--editions",
    "editions_files",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    help="Edition YAML file(s) to lint.",
)
@click.option(
    "--cards",
    "cards_files",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    help="Cards YAML file(s) to lint.",
)
@click.option(
    "--printings",
    "printings_files",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    help="Printings YAML file(s) to lint.",
)
def lint(editions_files: tuple[Path, ...], cards_files: tuple[Path, ...], printings_files: tuple[Path, ...]):
    """Lint YAML output files for common issues.

    Checks for duplicate IDs, duplicate names, and sort order.
    """
    errors: list[str] = []

    for path in editions_files:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        if not isinstance(data, list):
            errors.append(f"{path}: expected a list of editions")
            continue
        lint_editions(data, str(path), errors)

    for path in cards_files:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        if not isinstance(data, list):
            errors.append(f"{path}: expected a list of cards")
            continue
        lint_cards(data, str(path), errors)

    for path in printings_files:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        if not isinstance(data, list):
            errors.append(f"{path}: expected a list of printings")
            continue
        lint_printings(data, str(path), errors)

    if errors:
        for err in errors:
            click.echo(f"ERROR: {err}", err=True)
        raise SystemExit(1)
    else:
        total = len(editions_files) + len(cards_files) + len(printings_files)
        click.echo(f"OK: {total} file(s) checked, no issues found.", err=True)
