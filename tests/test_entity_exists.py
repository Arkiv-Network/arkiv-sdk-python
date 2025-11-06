"""Tests for entity_exists functionality."""

import logging

from arkiv import Arkiv
from arkiv.types import Attributes, EntityKey
from arkiv.utils import is_entity_key

from .utils import bulk_create_entities

logger = logging.getLogger(__name__)


class TestEntityExists:
    """Test entity existence checking."""

    def test_entity_exists_for_non_existent_entity(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test entity_exists with malformed entity key."""
        fake_key = EntityKey(
            "0x0000000000000000000000000000000000000000000000000000000000000999"
        )
        assert is_entity_key(fake_key) is True
        assert arkiv_client_http.arkiv.entity_exists(fake_key) is False

    def test_entity_exists_with_invalid_entity_key_format(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test entity_exists with malformed entity key."""
        invalid_key = EntityKey("0xinvalid")
        assert is_entity_key(invalid_key) is False
        assert not arkiv_client_http.arkiv.entity_exists(invalid_key)

    def test_entity_exists_returns_true_for_created_entity(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test that entity_exists returns True for a created entity."""
        # Create an entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"test data", btl=1000
        )

        # Check it exists
        assert arkiv_client_http.arkiv.entity_exists(entity_key) is True

    def test_entity_exists_multiple_entities(self, arkiv_client_http: Arkiv) -> None:
        """Test entity_exists works correctly with multiple entities."""
        # Create multiple entities
        entity_keys = []
        for i in range(5):
            payload = f"entity {i}".encode()
            entity_key, _ = arkiv_client_http.arkiv.create_entity(
                payload=payload, btl=1000
            )
            entity_keys.append(entity_key)

        # Verify all exist
        for entity_key in entity_keys:
            assert arkiv_client_http.arkiv.entity_exists(entity_key) is True

        # Verify a non-existent one doesn't exist

    def test_entity_exists_is_idempotent(self, arkiv_client_http: Arkiv) -> None:
        """Test that calling entity_exists multiple times gives same result."""
        payload = b"test idempotency"
        entity_key, receipt = arkiv_client_http.arkiv.create_entity(
            payload=payload, btl=1000
        )

        # Call multiple times
        result1 = arkiv_client_http.arkiv.entity_exists(
            entity_key, at_block=receipt.block_number
        )
        result2 = arkiv_client_http.arkiv.entity_exists(
            entity_key, at_block=receipt.block_number
        )
        result3 = arkiv_client_http.arkiv.entity_exists(
            entity_key, at_block=receipt.block_number
        )

        assert result1 is True
        assert result2 is True
        assert result3 is True

    def test_entity_exists_after_creation_of_next_entity(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test entity_exists transitions from False to True on creation."""
        # Generate a unique entity key by creating and noting it
        payload = b"transition test"
        entity_key, _ = arkiv_client_http.arkiv.create_entity(payload=payload, btl=1000)

        # Now it should exist
        assert arkiv_client_http.arkiv.entity_exists(entity_key) is True

        # Create a different one to verify the first is still there
        entity_key2, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"second entity", btl=1000
        )
        assert arkiv_client_http.arkiv.entity_exists(entity_key) is True
        assert arkiv_client_http.arkiv.entity_exists(entity_key2) is True

    def test_entity_exists_consistency_with_get_entity(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test that entity_exists and get_entity are consistent."""
        # Create entity
        payload = b"consistency test"
        attributes = Attributes({"test": "consistency"})
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=payload, attributes=attributes, btl=1000
        )

        # Both methods should agree it exists
        exists = arkiv_client_http.arkiv.entity_exists(entity_key)
        entity = arkiv_client_http.arkiv.get_entity(entity_key)

        assert exists is True
        assert entity.key == entity_key
        assert entity.payload == payload
        assert entity.attributes == attributes

    def test_entity_exists_with_bulk_created_entities(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test entity_exists works with entities created via create_entities."""
        from arkiv.types import CreateOp

        # Create multiple entities in one transaction
        create_ops = [
            CreateOp(
                payload=f"bulk entity {i}".encode(),
                content_type="text/plain",
                attributes=Attributes({}),
                btl=1000,
            )
            for i in range(5)
        ]
        entity_keys = bulk_create_entities(
            arkiv_client_http, create_ops, label="test_bulk_exists"
        )

        # Verify all exist
        for entity_key in entity_keys:
            assert arkiv_client_http.arkiv.entity_exists(entity_key) is True
