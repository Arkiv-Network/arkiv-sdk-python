"""Tests for async entity update functionality in AsyncArkivModule."""

import logging

import pytest

from arkiv import AsyncArkiv
from arkiv.types import Attributes
from arkiv.utils import check_entity_key

from .utils import check_tx_hash

logger = logging.getLogger(__name__)


class TestAsyncEntityUpdate:
    """Test cases for async update_entity function."""

    @pytest.mark.asyncio
    async def test_async_update_entity_basic(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test updating an entity with async client."""
        # Create entity
        original_payload = b"Original payload"
        original_attributes = Attributes({"status": "initial", "version": 1})
        entity_key, _tx_hash = await async_arkiv_client_http.arkiv.create_entity(
            payload=original_payload, attributes=original_attributes, btl=100
        )

        # Update entity
        new_payload = b"Updated payload"
        new_attributes = Attributes({"status": "updated", "version": 2})
        update_tx_hash = await async_arkiv_client_http.arkiv.update_entity(
            entity_key=entity_key,
            payload=new_payload,
            attributes=new_attributes,
            btl=150,
        )

        # Verify update transaction hash
        check_tx_hash("test_async_update_entity_basic", update_tx_hash)

        # Verify entity was updated
        entity = await async_arkiv_client_http.arkiv.get_entity(entity_key)
        assert entity.payload == new_payload, "Payload should be updated"
        assert entity.attributes == new_attributes, "Attributes should be updated"

        logger.info(f"Updated async entity: {entity_key} (tx: {update_tx_hash})")

    @pytest.mark.asyncio
    async def test_async_update_entities_sequentially(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test updating multiple entities sequentially."""
        # Create multiple entities
        entity_keys = []
        for i in range(3):
            entity_key, _tx_hash = await async_arkiv_client_http.arkiv.create_entity(
                payload=f"Entity {i}".encode(),
                attributes=Attributes({"index": i, "version": 1}),
            )
            entity_keys.append(entity_key)

        # Update all entities sequentially
        for i, entity_key in enumerate(entity_keys):
            update_tx_hash = await async_arkiv_client_http.arkiv.update_entity(
                entity_key=entity_key,
                payload=f"Updated entity {i}".encode(),
                attributes=Attributes({"index": i, "version": 2}),
            )
            # Verify individual entity_key and tx_hash formats
            check_entity_key(entity_key, f"test_async_update_entities_sequentially_{i}")
            check_tx_hash(
                f"test_async_update_entities_sequentially_{i}", update_tx_hash
            )
            logger.info(f"Updated entity {i + 1}/3: {entity_key}")

        # Verify all updates
        for i, entity_key in enumerate(entity_keys):
            entity = await async_arkiv_client_http.arkiv.get_entity(entity_key)
            assert entity.payload == f"Updated entity {i}".encode()
            assert entity.attributes == Attributes({"index": i, "version": 2})

        logger.info("Successfully updated 3 entities sequentially")
