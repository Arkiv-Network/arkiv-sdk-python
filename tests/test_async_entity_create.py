"""Tests for async entity creation functionality in AsyncArkivModule."""

import logging

import pytest

from arkiv import AsyncArkiv
from arkiv.types import Annotations

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
        entity_key, tx_hash = await async_arkiv_client_http.arkiv.create_entity(
            payload=payload
        )

        # Verify entity_key
        assert entity_key is not None, "Entity key should not be None"
        assert isinstance(entity_key, str), "Entity key should be a string"
        assert len(entity_key) == 66, (
            "Entity key should be 66 characters (0x + 64 hex)"
        )
        assert entity_key.startswith("0x"), "Entity key should start with 0x"

        # Verify tx_hash
        assert tx_hash is not None, "Transaction hash should not be None"
        assert isinstance(tx_hash, str), "Transaction hash should be a string"
        assert len(tx_hash) == 66, "Transaction hash should be 66 characters"
        assert tx_hash.startswith("0x"), "Transaction hash should start with 0x"

        logger.info(f"Created async entity: {entity_key} (tx: {tx_hash})")

    @pytest.mark.asyncio
    async def test_async_create_entity_with_annotations(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test creating an entity with annotations."""
        # Create entity with payload and annotations
        payload = b"Entity with annotations"
        annotations = Annotations({"type": "test", "version": 1, "priority": 5})
        entity_key, tx_hash = await async_arkiv_client_http.arkiv.create_entity(
            payload=payload, annotations=annotations
        )

        # Verify entity was created
        assert entity_key is not None
        assert tx_hash is not None
        assert isinstance(entity_key, str)
        assert isinstance(tx_hash, str)

        logger.info(
            f"Created async entity with annotations: {entity_key} (tx: {tx_hash})"
        )

    @pytest.mark.asyncio
    async def test_async_create_entity_custom_btl(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test creating an entity with custom BTL (blocks to live)."""
        # Create entity with custom BTL
        payload = b"Entity with custom TTL"
        btl = 150  # 150 blocks to live
        entity_key, tx_hash = await async_arkiv_client_http.arkiv.create_entity(
            payload=payload, btl=btl
        )

        # Verify entity was created
        assert entity_key is not None
        assert tx_hash is not None

        logger.info(
            f"Created async entity with custom BTL: {entity_key} (tx: {tx_hash})"
        )

    @pytest.mark.asyncio
    async def test_async_create_entity_empty_payload(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test creating an entity with empty payload."""
        # Create entity with empty payload
        entity_key, tx_hash = await async_arkiv_client_http.arkiv.create_entity()

        # Verify entity was created
        assert entity_key is not None
        assert tx_hash is not None
        assert isinstance(entity_key, str)
        assert isinstance(tx_hash, str)

        logger.info(f"Created async entity with empty payload: {entity_key}")

    @pytest.mark.asyncio
    async def test_async_create_multiple_entities_sequentially(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test creating multiple entities sequentially."""
        # Create multiple entities
        entity_keys = []
        for i in range(3):
            payload = f"Async entity {i}".encode()
            annotations = Annotations({"index": i, "batch": "sequential"})
            entity_key, _tx_hash = await async_arkiv_client_http.arkiv.create_entity(
                payload=payload, annotations=annotations
            )
            entity_keys.append(entity_key)
            logger.info(f"Created entity {i + 1}/3: {entity_key}")

        # Verify all entities were created
        assert len(entity_keys) == 3
        assert len(set(entity_keys)) == 3, "All entity keys should be unique"

        logger.info(f"Created {len(entity_keys)} entities sequentially")
