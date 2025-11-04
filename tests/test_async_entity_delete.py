"""Tests for async entity delete functionality in AsyncArkivModule."""

import logging

import pytest

from arkiv import AsyncArkiv
from arkiv.types import Attributes
from arkiv.utils import check_entity_key

from .utils import check_tx_hash

logger = logging.getLogger(__name__)


class TestAsyncEntityDelete:
    """Test cases for async delete_entity function."""

    @pytest.mark.asyncio
    async def test_async_delete_entity_basic(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test deleting a single entity asynchronously."""
        # Create an entity to delete
        entity_key, create_tx_hash = await async_arkiv_client_http.arkiv.create_entity(
            payload=b"Test entity for async deletion",
            attributes=Attributes({"type": "test"}),
            btl=100,
        )

        check_entity_key(entity_key, "test_async_delete_entity_basic")
        check_tx_hash("test_async_delete_entity_basic_create", create_tx_hash)

        # Verify the entity exists
        assert await async_arkiv_client_http.arkiv.entity_exists(entity_key), (
            "Entity should exist after creation"
        )

        # Delete the entity
        receipt = await async_arkiv_client_http.arkiv.delete_entity(entity_key)

        check_tx_hash("test_async_delete_entity_basic_delete", receipt)
        logger.info(f"Deleted entity {entity_key}")

        # Verify the entity no longer exists
        assert not await async_arkiv_client_http.arkiv.entity_exists(entity_key), (
            "Entity should not exist after deletion"
        )

    @pytest.mark.asyncio
    async def test_async_delete_entities_sequentially(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test deleting multiple entities sequentially."""
        # Create multiple entities
        entity_keys = []
        for i in range(3):
            entity_key, _tx_hash = await async_arkiv_client_http.arkiv.create_entity(
                payload=f"Entity {i}".encode(),
                attributes=Attributes({"index": i}),
                btl=100,
            )
            entity_keys.append(entity_key)

        # Verify all entities exist
        for entity_key in entity_keys:
            assert await async_arkiv_client_http.arkiv.entity_exists(entity_key), (
                f"Entity {entity_key} should exist after creation"
            )

        # Delete all entities sequentially
        last_block = 0
        for i, entity_key in enumerate(entity_keys):
            receipt = await async_arkiv_client_http.arkiv.delete_entity(entity_key)
            check_entity_key(entity_key, f"test_async_delete_entities_sequentially_{i}")
            check_tx_hash(f"test_async_delete_entities_sequentially_{i}", receipt)
            last_block = receipt.block_number

            logger.info(f"Deleted entity {i + 1}/3: {entity_key} in block ")

        # Verify all entities are deleted
        for entity_key in entity_keys:
            assert not await async_arkiv_client_http.arkiv.entity_exists(
                entity_key, at_block=last_block
            ), f"Entity {entity_key} should not exist after deletion"
