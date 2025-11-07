"""Tests for query entity iterator (auto-pagination)."""

import uuid

from arkiv import Arkiv
from arkiv.types import Attributes, CreateOp, Operations, QueryOptions

BTL = 100
CONTENT_TYPE = "text/plain"


def create_test_entities(client: Arkiv, n: int) -> tuple[str, list[str]]:
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
            btl=BTL,
        )
        create_ops.append(create_op)

    # Execute all creates in a single transaction
    operations = Operations(creates=create_ops)
    receipt = client.arkiv.execute(operations)

    # Extract entity keys from receipt
    entity_keys = [create.key for create in receipt.creates]

    return batch_id, entity_keys


class TestQueryIterator:
    """Test auto-paginating query iterator."""

    def test_iterate_entities_basic(self, arkiv_client_http: Arkiv) -> None:
        """Test basic iteration over multiple pages of entities."""
        # Create 25 entities
        batch_id, expected_keys = create_test_entities(arkiv_client_http, 25)

        # Iterate with page size of 10 (should auto-fetch 3 pages: 10, 10, 5)
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(max_results_per_page=10)

        # Collect all entities using iterator
        entities = list(
            arkiv_client_http.arkiv.iterate_entities(query=query, options=options)
        )

        # Should get all 25 entities
        assert len(entities) == 25

        # Verify all entities have the correct batch_id
        for entity in entities:
            assert entity.attributes is not None
            assert entity.attributes["batch_id"] == batch_id

        # Verify all entity keys are present and unique
        result_keys = [entity.key for entity in entities]
        assert len(result_keys) == len(set(result_keys))
        assert set(result_keys) == set(expected_keys)
