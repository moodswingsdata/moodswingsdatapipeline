"""Tests for prepare_editions command."""

import uuid

from moodswings.prepare_editions import generate_edition_id, MSDATA_NAMESPACE


class TestGenerateEditionId:
    def test_deterministic(self):
        id1 = generate_edition_id("MSW")
        id2 = generate_edition_id("MSW")
        assert id1 == id2

    def test_uses_lowercase(self):
        id1 = generate_edition_id("MSW")
        id2 = generate_edition_id("msw")
        assert id1 == id2

    def test_differs_by_set_code(self):
        id1 = generate_edition_id("MSW")
        id2 = generate_edition_id("MS2")
        assert id1 != id2

    def test_is_valid_uuid(self):
        edition_id = generate_edition_id("MSW")
        parsed = uuid.UUID(edition_id)
        assert parsed.version == 5

    def test_uses_shared_namespace(self):
        expected = str(uuid.uuid5(MSDATA_NAMESPACE, "msw"))
        assert generate_edition_id("MSW") == expected
