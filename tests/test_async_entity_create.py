"""Tests for async entity creation functionality in AsyncArkivModule."""

import logging

import pytest

from arkiv import AsyncArkiv
from arkiv.types import Attributes

from .utils import check_entity_key, check_tx_hash

logger = logging.getLogger(__name__)


class TestAsyncEntityCreate:
    """Test cases for async create_entity function."""

    @pytest.mark.asyncio
    async def test_async_create_entity_simple(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test creating a simple entity with async client."""
        # Create entity with simple payload
        payload = b"Test async entity"
        entity_key, receipt = await async_arkiv_client_http.arkiv.create_entity(
            payload=payload
        )

        # Verify entity_key and tx_hash formats
        check_entity_key("test_async_create_entity_simple", entity_key)
        check_tx_hash("test_async_create_entity_simple", receipt)

        logger.info(f"Created async entity: {entity_key} (tx: {receipt.tx_hash})")

    @pytest.mark.asyncio
    async def test_async_create_entities_multiple(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test creating multiple entities sequentially with async/await."""
        # Create multiple entities using async/await
        entity_keys = []
        for i in range(3):
            entity_key, receipt = await async_arkiv_client_http.arkiv.create_entity(
                payload=f"Async entity {i}".encode(),
                attributes=Attributes({"index": i}),
            )

            # Verify individual entity_key and tx_hash formats
            check_entity_key(f"test_async_create_entities_multiple_{i}", entity_key)
            check_tx_hash(f"test_async_create_entities_multiple_{i}", receipt)

            entity_keys.append(entity_key)
            logger.info(f"Created async entity {i + 1}/3: {entity_key}")

        # Verify all succeeded and are unique
        assert len(entity_keys) == 3
        assert len(set(entity_keys)) == 3, "All entity keys should be unique"
