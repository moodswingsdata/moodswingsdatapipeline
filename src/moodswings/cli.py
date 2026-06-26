import click

from moodswings.apply_fix import apply_fix
from moodswings.apply_errata import apply_errata
from moodswings.create_card import create_card
from moodswings.create_printing import create_printing
from moodswings.extract import extract_cards
from moodswings.extract_from_images import extract_from_images
from moodswings.download_images import download_images
from moodswings.lint import lint
from moodswings.merge_cards import merge_cards
from moodswings.merge_printings import merge_printings
from moodswings.prepare_editions import prepare_editions
from moodswings.review_html import review_html
from moodswings.to_json import to_json
from moodswings.write_meta import write_meta


@click.group()
def main():
    """Mood Swings data pipeline tools."""
    pass


main.add_command(apply_fix)
main.add_command(apply_errata)
main.add_command(prepare_editions)
main.add_command(extract_cards)
main.add_command(extract_from_images)
main.add_command(download_images)
main.add_command(lint)
main.add_command(review_html)
main.add_command(create_card)
main.add_command(merge_cards)
main.add_command(create_printing)
main.add_command(merge_printings)
main.add_command(to_json)
main.add_command(write_meta)
