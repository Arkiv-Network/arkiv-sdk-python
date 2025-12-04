"""Tests for query entity iterator (auto-pagination)."""

import uuid

import pytest

from arkiv import AsyncArkiv
from arkiv.types import ATTRIBUTES, KEY, Attributes, CreateOp, Operations, QueryOptions

EXPIRES_IN = 100
CONTENT_TYPE = "text/plain"


async def create_test_entities(client: AsyncArkiv, n: int) -> tuple[str, list[str]]:
    """
    Create n test entities with sequential numeric attributes for iterator testing.

    All entities are created in a single transaction using client.arkiv.execute().

    Each entity has:
    - A 'batch_id' attribute (UUID) that is shared across all entities
    - A 'sequence' attribute with values from 1 to n

    Returns:
        Tuple of (batch_id, list of entity keys)
    """
    batch_id = str(uuid.uuid4())

    # Build list of CreateOp operations
    create_ops: list[CreateOp] = []
    for i in range(1, n + 1):
        payload = f"Entity {i}".encode()
        attributes = Attributes({"batch_id": batch_id, "sequence": i})

        create_op = CreateOp(
            payload=payload,
            content_type=CONTENT_TYPE,
            attributes=attributes,
            expires_in=EXPIRES_IN,
        )
        create_ops.append(create_op)

    # Execute all creates in a single transaction
    operations = Operations(creates=create_ops)
    receipt = await client.arkiv.execute(operations)

    # Extract entity keys from receipt
    entity_keys = [create.key for create in receipt.creates]

    return batch_id, entity_keys


class TestAsyncQueryIterator:
    """Test auto-paginating query iterator."""

    @pytest.mark.asyncio
    async def test_async_iterate_entities_basic(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test basic iteration over multiple pages of entities."""
        # Create test entities
        num_entities = 10
        batch_id, expected_keys = await create_test_entities(
            async_arkiv_client_http, num_entities
        )

        assert len(expected_keys) == num_entities

        # Define query and options
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(attributes=KEY | ATTRIBUTES, max_results_per_page=4)

        # Collect all entities using async iterator
        # Iterate with page size of 4 (should auto-fetch 3 pages: 4, 4, 2)
        entities = []
        async for entity in async_arkiv_client_http.arkiv.query_entities(
            query=query, options=options
        ):
            entities.append(entity)

        # Should get all 10 entities
        assert len(entities) == num_entities

        # Verify all entities have the correct batch_id
        for entity in entities:
            assert entity.attributes is not None
            assert entity.attributes["batch_id"] == batch_id

        # Verify all entity keys are present and unique
        result_keys = [entity.key for entity in entities]
        assert set(result_keys) == set(expected_keys)

    @pytest.mark.asyncio
    async def test_async_iterate_entities_empty(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test iteration over empty result set."""
        # Create some entities (to ensure the query mechanism works)
        num_entities = 5
        await create_test_entities(async_arkiv_client_http, num_entities)

        # Query for non-existent batch_id
        query = 'batch_id = "does-not-exist"'
        options = QueryOptions(attributes=KEY | ATTRIBUTES, max_results_per_page=10)

        # Collect results - should be empty
        entities = []
        async for entity in async_arkiv_client_http.arkiv.query_entities(
            query=query, options=options
        ):
            entities.append(entity)

        assert len(entities) == 0

    @pytest.mark.asyncio
    async def test_async_iterate_entities_max_results_across_pages(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test max_results limits iteration across multiple pages."""
        # Create 10 entities
        num_entities = 10
        batch_id, _ = await create_test_entities(async_arkiv_client_http, num_entities)

        # Query with max_results=7 and page size of 3
        # Should iterate across 3 pages (3+3+1) and stop at 7
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(
            attributes=KEY | ATTRIBUTES,
            max_results=7,
            max_results_per_page=3,
        )

        entities = []
        async for entity in async_arkiv_client_http.arkiv.query_entities(
            query=query, options=options
        ):
            entities.append(entity)

        assert len(entities) == 7
        for entity in entities:
            assert entity.attributes is not None
            assert entity.attributes["batch_id"] == batch_id
