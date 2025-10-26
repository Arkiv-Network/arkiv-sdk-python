"""Tests for async entity query functionality in AsyncArkivModule."""

import logging
import uuid

import pytest

from arkiv import AsyncArkiv
from arkiv.types import Annotations, Cursor

logger = logging.getLogger(__name__)


class TestAsyncQueryEntitiesParameterValidation:
    """Test parameter validation for async query_entities method."""

    @pytest.mark.asyncio
    async def test_async_query_entities_requires_query_or_cursor(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test that query_entities raises ValueError when neither query nor cursor is provided."""
        with pytest.raises(ValueError, match="Must provide either query or cursor"):
            await async_arkiv_client_http.arkiv.query_entities()

    @pytest.mark.asyncio
    async def test_async_query_entities_validates_none_for_both(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test that explicitly passing None for both query and cursor raises ValueError."""
        with pytest.raises(ValueError, match="Must provide either query or cursor"):
            await async_arkiv_client_http.arkiv.query_entities(query=None, cursor=None)

    @pytest.mark.asyncio
    async def test_async_query_entities_accepts_query_only(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test that query_entities accepts query without cursor."""
        # Should not raise ValueError for missing cursor
        result = await async_arkiv_client_http.arkiv.query_entities(
            query='owner = "0x0000000000000000000000000000000000000000"'
        )
        assert not result  # check for falsy result
        assert len(result) == 0  # No entities match this owner

    @pytest.mark.asyncio
    async def test_async_query_entities_both_query_and_cursor_not_allowed(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test that query_entities rejects both query and cursor (mutually exclusive)."""
        cursor = Cursor("dummy_cursor_value")

        # Should raise ValueError when both are provided
        with pytest.raises(ValueError, match="Cannot provide both query and cursor"):
            await async_arkiv_client_http.arkiv.query_entities(
                query='owner = "0x0000000000000000000000000000000000000000"',
                cursor=cursor,
            )


class TestAsyncQueryEntitiesBasic:
    """Test basic async entity querying functionality."""

    @pytest.mark.asyncio
    async def test_async_query_entities_by_annotation(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test querying entities by annotation value asynchronously."""
        # Generate a unique ID without special characters
        shared_id = str(uuid.uuid4()).replace("-", "")

        # Create 3 entities with the same 'id' annotation
        entity_keys = []
        for i in range(3):
            entity_key, _tx_hash = await async_arkiv_client_http.arkiv.create_entity(
                payload=f"Entity {i}".encode(),
                annotations=Annotations({"id": shared_id}),
                btl=100,
            )
            entity_keys.append(entity_key)

        # Query for entities with the shared ID
        query = f'id = "{shared_id}"'
        result = await async_arkiv_client_http.arkiv.query_entities(query=query)

        # Verify result basics
        assert result  # Check __bool__()
        assert result.block_number > 0
        assert result.has_more() is False
        assert result.cursor is None

        # Verify we got back all 3 entities
        assert len(result.entities) == 3

        # Verify the entity keys match (order may differ)
        result_keys = {entity.entity_key for entity in result.entities}
        expected_keys = set(entity_keys)
        assert result_keys == expected_keys

        logger.info(f"Query returned {len(result)} entities with id={shared_id}")

    @pytest.mark.asyncio
    async def test_async_query_entities_concurrently(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test running multiple queries concurrently with different result sets."""
        # Generate unique IDs for our test
        shared_id = str(uuid.uuid4()).replace("-", "")
        unique_id = str(uuid.uuid4()).replace("-", "")
        nonexistent_id = str(uuid.uuid4()).replace("-", "")

        # Create 3 entities:
        # - All 3 entities with shared "category" annotation
        # - Only 1 entity with unique "special" annotation
        entity_keys = []
        unique_entity_key = None

        for i in range(3):
            # All entities get the shared category
            annotations = {"category": shared_id}

            # Only the second entity (i==1) gets the special annotation
            if i == 1:
                annotations["special"] = unique_id
                unique_entity_key = None  # Will be set below

            entity_key, _tx_hash = await async_arkiv_client_http.arkiv.create_entity(
                payload=f"Entity {i}".encode(),
                annotations=Annotations(annotations),
                btl=100,
            )
            entity_keys.append(entity_key)

            if i == 1:
                unique_entity_key = entity_key

        # Run 3 queries concurrently:
        # 1. Query that returns all 3 entities (shared category)
        # 2. Query that returns only 1 entity (the one with special annotation)
        # 3. Query that returns 0 entities (nonexistent ID)
        import asyncio

        query_all = f'category = "{shared_id}"'
        query_single = f'special = "{unique_id}"'
        query_none = f'category = "{nonexistent_id}"'

        # Execute all queries concurrently
        results = await asyncio.gather(
            async_arkiv_client_http.arkiv.query_entities(query=query_all),
            async_arkiv_client_http.arkiv.query_entities(query=query_single),
            async_arkiv_client_http.arkiv.query_entities(query=query_none),
        )

        result_all, result_single, result_none = results

        # Verify first query returns all 3 entities
        assert len(result_all) == 3, "Query 1 should return all 3 entities"
        assert result_all.block_number > 0
        result_all_keys = {entity.entity_key for entity in result_all.entities}
        assert result_all_keys == set(entity_keys)

        # Verify second query returns only 1 entity
        assert len(result_single) == 1, "Query 2 should return 1 entity"
        assert result_single.block_number > 0
        assert result_single.entities[0].entity_key == unique_entity_key

        # Verify third query returns no entities
        assert len(result_none) == 0, "Query 3 should return 0 entities"
        assert not result_none  # Check __bool__() returns False
        assert result_none.block_number > 0

        logger.info(
            f"Concurrent queries completed: {len(result_all)} all, "
            f"{len(result_single)} single, {len(result_none)} none"
        )
