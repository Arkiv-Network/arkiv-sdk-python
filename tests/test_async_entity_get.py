"""Tests for async entity retrieval functionality in AsyncArkivModule."""

import logging

import pytest

from arkiv import AsyncArkiv
from arkiv.types import (
    ALL,
    CONTENT_TYPE,
    PAYLOAD,
    Attributes,
    EntityKey,
)

logger = logging.getLogger(__name__)


class TestAsyncEntityGet:
    """Test cases for async get_entity function."""

    @pytest.mark.asyncio
    async def test_async_get_entity_basic(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test retrieving an entity with async client."""

        # Create entity
        entity_key, payload, content_type, attributes = await create_entity(
            async_arkiv_client_http
        )

        # Retrieve entity with async client (all fields by default)
        entity = await async_arkiv_client_http.arkiv.get_entity(entity_key)

        # Verify all fields
        assert entity.key == entity_key, "Entity key should match"
        assert entity.payload == payload, "Payload should match"
        assert entity.content_type == content_type, "Content type should match"
        assert entity.attributes == attributes, "Attributes should match"
        assert entity.owner is not None, "Owner should be populated"
        assert entity.owner == async_arkiv_client_http.eth.default_account, (
            "Owner should match default account"
        )
        assert entity.expires_at_block is not None, "Expiration block should be set"
        assert entity.expires_at_block > 0, "Expiration block should be positive"

        logger.info(f"Retrieved async entity: {entity_key}")

    @pytest.mark.asyncio
    async def test_async_get_entity_field_flags(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test retrieving entity with different field flags."""

        # Create entity
        entity_key, payload, content_type, attributes = await create_entity(
            async_arkiv_client_http
        )

        # Test PAYLOAD only
        entity = await async_arkiv_client_http.arkiv.get_entity(
            entity_key, fields=PAYLOAD
        )
        assert entity.payload == payload, "Payload should be retrieved"
        assert entity.content_type is None, "Content type should not be retrieved"
        assert entity.owner is None, "Owner should not be retrieved"
        assert entity.attributes is None, "Attributes should not be retrieved"

        # Test CONTENT_TYPE only
        entity = await async_arkiv_client_http.arkiv.get_entity(
            entity_key, fields=CONTENT_TYPE
        )
        assert entity.payload is None, "Payload should not be retrieved"
        assert entity.content_type == content_type, "Content type should be retrieved"
        assert entity.owner is None, "Owner should not be retrieved"
        assert entity.expires_at_block is None, "Expiration should not be retrieved"
        assert entity.attributes is None, "Attributes should not be retrieved"

        # TODO investigate error: web3.exceptions.Web3RPCError: {'code': -32603, 'message': 'method handler crashed'}
        # Test ATTRIBUTES only
        # entity = await async_arkiv_client_http.arkiv.get_entity(
        #    entity_key, fields=ATTRIBUTES
        # )
        # assert entity.payload is None, "Payload should not be retrieved"
        # assert entity.content_type is None, "Content type should not be retrieved"
        # assert entity.owner is None, "Owner should not be retrieved"
        # assert entity.expires_at_block is None, "Expiration should not be retrieved"
        # assert entity.attributes == attributes, "Attributes should be retrieved"

        # Test ALL fields
        entity = await async_arkiv_client_http.arkiv.get_entity(entity_key, fields=ALL)
        assert entity.key == entity_key, "All: Entity key should be retrieved"
        assert entity.payload == payload, "All: Payload should be retrieved"
        assert entity.content_type == content_type, (
            "All: Content type should be retrieved"
        )
        assert entity.owner is not None, "All: Owner should be retrieved"
        assert entity.attributes == attributes, "All: Attributes should be retrieved"
        assert entity.expires_at_block is not None, (
            "All: Expiration should be retrieved"
        )

        logger.info("Field flags work correctly for async get_entity")

    @pytest.mark.asyncio
    async def test_async_get_entities_concurrently(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test retrieving multiple entities concurrently using asyncio.gather."""
        import asyncio

        # Create multiple entities
        entity_keys = []
        for i in range(5):
            payload = f"Concurrent read test entity {i}".encode()
            attributes = Attributes({"index": i, "batch": "concurrent_read"})
            entity_key, _tx_hash = await async_arkiv_client_http.arkiv.create_entity(
                payload=payload, attributes=attributes, btl=100
            )
            entity_keys.append(entity_key)
            logger.info(f"Created entity {i + 1}/5: {entity_key}")

        # Retrieve all entities concurrently
        tasks = [async_arkiv_client_http.arkiv.get_entity(key) for key in entity_keys]
        entities = await asyncio.gather(*tasks)

        # Verify all entities were retrieved correctly
        assert len(entities) == 5, "Should retrieve all 5 entities"
        for i, entity in enumerate(entities):
            assert entity.key == entity_keys[i], f"Entity {i} key should match"
            assert entity.payload == f"Concurrent read test entity {i}".encode(), (
                f"Entity {i} payload should match"
            )
            assert entity.attributes == Attributes(
                {"index": i, "batch": "concurrent_read"}
            ), f"Entity {i} attributes should match"

        logger.info("Successfully retrieved 5 entities concurrently")

    @pytest.mark.asyncio
    async def test_async_entity_exists(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test checking if entities exist with async client."""
        # Create an entity
        payload = b"Entity existence check"
        entity_key, _tx_hash = await async_arkiv_client_http.arkiv.create_entity(
            payload=payload
        )

        # Check that created entity exists
        exists = await async_arkiv_client_http.arkiv.entity_exists(entity_key)
        assert exists is True, "Created entity should exist"

        # Check that non-existent entity doesn't exist
        fake_key = "0x0000000000000000000000000000000000000000000000000000000000000000"
        not_exists = await async_arkiv_client_http.arkiv.entity_exists(fake_key)
        assert not_exists is False, "Non-existent entity should not exist"

        logger.info("Entity existence check works correctly")


async def create_entity(
    arkiv_client_http: AsyncArkiv,
) -> tuple[EntityKey, bytes, str, Attributes]:
    # Create an entity with all data
    payload = b"Test entity data"
    content_type = "text/plain"
    attributes = Attributes({"type": "test", "version": 1})
    btl = 100

    entity_key, _ = await arkiv_client_http.arkiv.create_entity(
        payload=payload,
        content_type=content_type,
        attributes=attributes,
        btl=btl,
    )

    return entity_key, payload, content_type, attributes
