"""Tests for the lint command."""

import pytest
import yaml
from pathlib import Path

from moodswings.lint import lint_editions, lint_cards, lint_printings


class TestLintEditions:
    def test_no_issues(self):
        data = [
            {"id": "aaa", "edition_name": "Edition 1", "set_code": "msw"},
            {"id": "bbb", "edition_name": "Edition 2", "set_code": "msw2"},
        ]
        errors = []
        lint_editions(data, "test.yaml", errors)
        assert errors == []

    def test_duplicate_id(self):
        data = [
            {"id": "aaa", "edition_name": "Edition 1", "set_code": "msw"},
            {"id": "aaa", "edition_name": "Edition 2", "set_code": "msw2"},
        ]
        errors = []
        lint_editions(data, "test.yaml", errors)
        assert len(errors) == 1
        assert "duplicate edition id" in errors[0]

    def test_duplicate_name(self):
        data = [
            {"id": "aaa", "edition_name": "Edition 1", "set_code": "msw"},
            {"id": "bbb", "edition_name": "Edition 1", "set_code": "msw2"},
        ]
        errors = []
        lint_editions(data, "test.yaml", errors)
        assert len(errors) == 1
        assert "duplicate edition name" in errors[0]


class TestLintCards:
    def test_no_issues(self):
        data = [
            {"id": "aaa", "name": "Altruism"},
            {"id": "bbb", "name": "Bravado"},
            {"id": "ccc", "name": "Courage"},
        ]
        errors = []
        lint_cards(data, "test.yaml", errors)
        assert errors == []

    def test_duplicate_id(self):
        data = [
            {"id": "aaa", "name": "Altruism"},
            {"id": "aaa", "name": "Bravado"},
        ]
        errors = []
        lint_cards(data, "test.yaml", errors)
        assert len(errors) == 1
        assert "duplicate card id" in errors[0]

    def test_duplicate_name(self):
        data = [
            {"id": "aaa", "name": "Altruism"},
            {"id": "bbb", "name": "Altruism"},
        ]
        errors = []
        lint_cards(data, "test.yaml", errors)
        assert len(errors) == 1
        assert "duplicate card name" in errors[0]

    def test_sort_order_correct(self):
        data = [
            {"id": "aaa", "name": "Ambition"},
            {"id": "bbb", "name": "Bravado"},
            {"id": "ccc", "name": "Zeal"},
        ]
        errors = []
        lint_cards(data, "test.yaml", errors)
        assert errors == []

    def test_sort_order_violation(self):
        data = [
            {"id": "bbb", "name": "Bravado"},
            {"id": "aaa", "name": "Altruism"},
        ]
        errors = []
        lint_cards(data, "test.yaml", errors)
        assert len(errors) == 1
        assert "not sorted by name" in errors[0]


class TestLintPrintings:
    def test_no_issues(self):
        data = [
            {"id": "aaa", "card_id": "c1", "edition_id": "ed1", "collector_number": 1},
            {"id": "bbb", "card_id": "c2", "edition_id": "ed1", "collector_number": 2},
            {"id": "ccc", "card_id": "c3", "edition_id": "ed1", "collector_number": 3},
        ]
        errors = []
        lint_printings(data, "test.yaml", errors)
        assert errors == []

    def test_duplicate_id(self):
        data = [
            {"id": "aaa", "card_id": "c1", "edition_id": "ed1", "collector_number": 1},
            {"id": "aaa", "card_id": "c2", "edition_id": "ed1", "collector_number": 2},
        ]
        errors = []
        lint_printings(data, "test.yaml", errors)
        assert len(errors) == 1
        assert "duplicate printing id" in errors[0]

    def test_sort_order_correct_same_edition(self):
        data = [
            {"id": "aaa", "card_id": "c1", "edition_id": "ed1", "collector_number": 10},
            {"id": "bbb", "card_id": "c2", "edition_id": "ed1", "collector_number": 20},
            {"id": "ccc", "card_id": "c3", "edition_id": "ed1", "collector_number": 9999},
        ]
        errors = []
        lint_printings(data, "test.yaml", errors)
        assert errors == []

    def test_sort_order_correct_across_editions(self):
        """edition_id 'ed1' < 'ed2' lexicographically, so ed1 first is correct."""
        data = [
            {"id": "aaa", "card_id": "c1", "edition_id": "ed1", "collector_number": 50},
            {"id": "bbb", "card_id": "c2", "edition_id": "ed2", "collector_number": 1},
        ]
        errors = []
        lint_printings(data, "test.yaml", errors)
        assert errors == []

    def test_sort_order_violation_within_edition(self):
        data = [
            {"id": "bbb", "card_id": "c2", "edition_id": "ed1", "collector_number": 5},
            {"id": "aaa", "card_id": "c1", "edition_id": "ed1", "collector_number": 2},
        ]
        errors = []
        lint_printings(data, "test.yaml", errors)
        assert len(errors) == 1
        assert "not sorted correctly" in errors[0]

    def test_sort_order_violation_wrong_edition_order(self):
        """edition_id 'ed2' > 'ed1' lexicographically, so ed2 first is wrong."""
        data = [
            {"id": "bbb", "card_id": "c2", "edition_id": "ed2", "collector_number": 1},
            {"id": "aaa", "card_id": "c1", "edition_id": "ed1", "collector_number": 50},
        ]
        errors = []
        lint_printings(data, "test.yaml", errors)
        assert len(errors) == 1
        assert "not sorted correctly" in errors[0]

    def test_null_collector_number_treated_as_9999(self):
        data = [
            {"id": "aaa", "card_id": "c1", "edition_id": "ed1", "collector_number": 50},
            {"id": "bbb", "card_id": "c2", "edition_id": "ed1", "collector_number": None},
        ]
        errors = []
        lint_printings(data, "test.yaml", errors)
        assert errors == []

    def test_valid_rarities_no_issues(self):
        data = [
            {"id": "aaa", "card_id": "c1", "edition_id": "ed1", "collector_number": 1, "rarity": "Common"},
            {"id": "bbb", "card_id": "c2", "edition_id": "ed1", "collector_number": 2, "rarity": "Uncommon"},
            {"id": "ccc", "card_id": "c3", "edition_id": "ed1", "collector_number": 3, "rarity": "Rare"},
            {"id": "ddd", "card_id": "c4", "edition_id": "ed1", "collector_number": 4, "rarity": "Mythic Rare"},
        ]
        errors = []
        lint_printings(data, "test.yaml", errors)
        assert errors == []

    def test_invalid_rarity(self):
        data = [
            {"id": "aaa", "card_id": "c1", "edition_id": "ed1", "collector_number": 1, "rarity": "Mythic"},
        ]
        errors = []
        lint_printings(data, "test.yaml", errors)
        assert len(errors) == 1
        assert "invalid rarity 'Mythic'" in errors[0]

    def test_null_rarity_allowed(self):
        data = [
            {"id": "aaa", "card_id": "c1", "edition_id": "ed1", "collector_number": 1, "rarity": None},
        ]
        errors = []
        lint_printings(data, "test.yaml", errors)
        assert errors == []
