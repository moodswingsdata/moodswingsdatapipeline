import click

from moodswings.add_card import add_card
from moodswings.add_printing import add_printing
from moodswings.extract import extract_cards
from moodswings.extract_from_images import extract_from_images
from moodswings.download_images import download_images
from moodswings.prepare_editions import prepare_editions
from moodswings.review_html import review_html
from moodswings.to_json import to_json


@click.group()
def main():
    """Mood Swings data pipeline tools."""
    pass


main.add_command(prepare_editions)
main.add_command(extract_cards)
main.add_command(extract_from_images)
main.add_command(download_images)
main.add_command(review_html)
main.add_command(add_card)
main.add_command(add_printing)
main.add_command(to_json)
