import click

from moodswings.extract import extract_cards
from moodswings.download_images import download_images


@click.group()
def main():
    """Mood Swings data pipeline tools."""
    pass


main.add_command(extract_cards)
main.add_command(download_images)
