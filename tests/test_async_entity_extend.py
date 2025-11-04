"""Tests for async entity extend functionality in AsyncArkivModule."""

import logging

import pytest

from arkiv import AsyncArkiv
from arkiv.types import Attributes
from arkiv.utils import check_entity_key

from .utils import check_tx_hash

logger = logging.getLogger(__name__)


class TestAsyncEntityExtend:
    """Test cases for async extend_entity function."""

    @pytest.mark.asyncio
    async def test_async_extend_entity_basic(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test extending a single entity's lifetime asynchronously."""
        # Create an entity to extend
        entity_key, create_tx_hash = await async_arkiv_client_http.arkiv.create_entity(
            payload=b"Test entity for async extension",
            attributes=Attributes({"type": "test"}),
            btl=100,
        )

        check_entity_key(entity_key, "test_async_extend_entity_basic")
        check_tx_hash("test_async_extend_entity_basic_create", create_tx_hash)

        # Get initial expiration block
        entity_before = await async_arkiv_client_http.arkiv.get_entity(entity_key)
        initial_expiration = entity_before.expires_at_block
        assert initial_expiration is not None, "Entity should have expiration block"

        # Extend the entity by 50 blocks
        number_of_blocks = 50
        receipt = await async_arkiv_client_http.arkiv.extend_entity(
            entity_key, number_of_blocks
        )

        check_tx_hash("test_async_extend_entity_basic_extend", receipt)
        logger.info(f"Extended entity {entity_key} by {number_of_blocks} blocks")

        # Verify expiration increased
        entity_after = await async_arkiv_client_http.arkiv.get_entity(entity_key)
        assert entity_after.expires_at_block == initial_expiration + number_of_blocks, (
            f"Expiration should increase by {number_of_blocks} blocks"
        )

    @pytest.mark.asyncio
    async def test_async_extend_entities_sequentially(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test extending multiple entities sequentially."""
        # Create multiple entities
        entity_keys = []
        initial_expirations = []
        for i in range(3):
            entity_key, _tx_hash = await async_arkiv_client_http.arkiv.create_entity(
                payload=f"Entity {i}".encode(),
                attributes=Attributes({"index": i}),
                btl=100,
            )
            entity_keys.append(entity_key)

            # Get initial expiration
            entity = await async_arkiv_client_http.arkiv.get_entity(entity_key)
            initial_expirations.append(entity.expires_at_block)

        # Check that initial expirations are not None
        for i, expiration in enumerate(initial_expirations):
            assert expiration is not None, f"Entity {i} should have an expiration block"

        # Extend all entities sequentially
        number_of_blocks = 50
        for i, entity_key in enumerate(entity_keys):
            receipt = await async_arkiv_client_http.arkiv.extend_entity(
                entity_key, number_of_blocks
            )
            check_entity_key(entity_key, f"test_async_extend_entities_sequentially_{i}")
            check_tx_hash(f"test_async_extend_entities_sequentially_{i}", receipt)
            logger.info(f"Extended entity {i + 1}/3: {entity_key}")

        # Verify all extensions
        for i, entity_key in enumerate(entity_keys):
            entity = await async_arkiv_client_http.arkiv.get_entity(entity_key)
            expected_expiration = initial_expirations[i] + number_of_blocks
            assert entity.expires_at_block == expected_expiration, (
                f"Entity {i} expiration should be {expected_expiration}"
            )
