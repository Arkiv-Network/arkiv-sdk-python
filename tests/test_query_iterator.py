"""Tests for query entity iterator (auto-pagination)."""

import uuid

from arkiv import Arkiv
from arkiv.types import ATTRIBUTES, KEY, Attributes, CreateOp, Operations, QueryOptions

EXPIRES_IN = 100
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
            expires_in=EXPIRES_IN,
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
        # Create test entities
        num_entities = 10
        batch_id, expected_keys = create_test_entities(arkiv_client_http, num_entities)

        assert len(expected_keys) == num_entities

        # Define query and options
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(attributes=KEY | ATTRIBUTES, max_results_per_page=4)

        # Classical for loop
        # Should get all 10 entities
        iterator = arkiv_client_http.arkiv.query_entities(query=query, options=options)
        entities = []
        for entity in iterator:
            entities.append(entity)

        assert len(entities) == num_entities

        # Verify all entities have the correct batch_id
        for entity in entities:
            assert entity.attributes is not None
            assert entity.attributes["batch_id"] == batch_id

        # Verify all entity keys are present and unique
        result_keys = [entity.key for entity in entities]
        assert set(result_keys) == set(expected_keys)

    def test_iterate_entities_with_list(self, arkiv_client_http: Arkiv) -> None:
        """Test basic iteration over multiple pages of entities."""
        # Create test entities
        num_entities = 10
        batch_id, expected_keys = create_test_entities(arkiv_client_http, num_entities)

        assert len(expected_keys) == num_entities

        # Define query and options
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(attributes=KEY | ATTRIBUTES, max_results_per_page=4)

        # Collect all entities using iterator
        # Iterate with page size of 4 (should auto-fetch 3 pages: 4, 4, 2)
        entities = list(
            arkiv_client_http.arkiv.query_entities(query=query, options=options)
        )

        # Should get all 10 entities
        assert len(entities) == num_entities

        # Verify all entities have the correct batch_id
        for entity in entities:
            assert entity.attributes is not None
            assert entity.attributes["batch_id"] == batch_id

        # Verify all entity keys are present and unique
        result_keys = [entity.key for entity in entities]
        assert set(result_keys) == set(expected_keys)

    def test_iterate_entities_empty(self, arkiv_client_http: Arkiv) -> None:
        """Test basic iteration over multiple pages of entities."""
        # Create test entities
        num_entities = 10
        _, expected_keys = create_test_entities(arkiv_client_http, num_entities)

        assert len(expected_keys) == num_entities

        # Define query and options
        query = 'batch_id = "does not exist"'
        options = QueryOptions(attributes=KEY | ATTRIBUTES, max_results_per_page=4)

        # Classical for loop
        # Should get all 10 entities
        iterator = arkiv_client_http.arkiv.query_entities(query=query, options=options)
        entities = []
        for entity in iterator:
            entities.append(entity)

        assert len(entities) == 0

    def test_iterate_entities_less_than_page(self, arkiv_client_http: Arkiv) -> None:
        """Test basic iteration over multiple pages of entities."""
        # Create test entities
        num_entities = 10
        batch_id, expected_keys = create_test_entities(arkiv_client_http, num_entities)

        assert len(expected_keys) == num_entities

        # Define query and options
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(
            attributes=KEY | ATTRIBUTES, max_results_per_page=2 * num_entities
        )

        # Classical for loop
        # Should get all 10 entities
        iterator = arkiv_client_http.arkiv.query_entities(query=query, options=options)
        entities = []
        for entity in iterator:
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

    def test_iterate_entities_exactly_page(self, arkiv_client_http: Arkiv) -> None:
        """Test basic iteration over multiple pages of entities."""
        # Create test entities
        num_entities = 10
        batch_id, expected_keys = create_test_entities(arkiv_client_http, num_entities)

        assert len(expected_keys) == num_entities

        # Define query and options
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(
            attributes=KEY | ATTRIBUTES, max_results_per_page=num_entities
        )

        # Classical for loop
        # Should get all 10 entities
        iterator = arkiv_client_http.arkiv.query_entities(query=query, options=options)
        entities = []
        for entity in iterator:
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

    def test_iterate_entities_max_results_within_single_page(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test max_results limits iteration within a single page."""
        # Create 10 entities
        num_entities = 10
        batch_id, _ = create_test_entities(arkiv_client_http, num_entities)

        # Query with max_results=3 and large page size
        # Should stop after 3 entities without fetching more
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(
            attributes=KEY | ATTRIBUTES,
            max_results=3,
            max_results_per_page=100,
        )

        iterator = arkiv_client_http.arkiv.query_entities(query=query, options=options)
        entities = list(iterator)

        assert len(entities) == 3
        for entity in entities:
            assert entity.attributes is not None
            assert entity.attributes["batch_id"] == batch_id

    def test_iterate_entities_max_results_across_pages(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test max_results limits iteration across multiple pages."""
        # Create 10 entities
        num_entities = 10
        batch_id, _ = create_test_entities(arkiv_client_http, num_entities)

        # Query with max_results=7 and page size of 3
        # Should iterate across 3 pages (3+3+1) and stop at 7
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(
            attributes=KEY | ATTRIBUTES,
            max_results=7,
            max_results_per_page=3,
        )

        iterator = arkiv_client_http.arkiv.query_entities(query=query, options=options)
        entities = list(iterator)

        assert len(entities) == 7
        for entity in entities:
            assert entity.attributes is not None
            assert entity.attributes["batch_id"] == batch_id

    def test_iterate_entities_max_results_equals_total(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test max_results equal to total matching entities."""
        # Create 5 entities
        num_entities = 5
        batch_id, expected_keys = create_test_entities(arkiv_client_http, num_entities)

        # Query with max_results=5 (exactly matching total)
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(
            attributes=KEY | ATTRIBUTES,
            max_results=5,
            max_results_per_page=10,
        )

        iterator = arkiv_client_http.arkiv.query_entities(query=query, options=options)
        entities = list(iterator)

        assert len(entities) == 5
        result_keys = [entity.key for entity in entities]
        assert set(result_keys) == set(expected_keys)

    def test_iterate_entities_max_results_exceeds_total(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test max_results greater than total matching entities."""
        # Create 5 entities
        num_entities = 5
        batch_id, expected_keys = create_test_entities(arkiv_client_http, num_entities)

        # Query with max_results=100 (more than available)
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(
            attributes=KEY | ATTRIBUTES,
            max_results=100,
            max_results_per_page=10,
        )

        iterator = arkiv_client_http.arkiv.query_entities(query=query, options=options)
        entities = list(iterator)

        # Should get all 5 entities (not artificially limited)
        assert len(entities) == 5
        result_keys = [entity.key for entity in entities]
        assert set(result_keys) == set(expected_keys)

    def test_iterate_entities_max_results_zero(self, arkiv_client_http: Arkiv) -> None:
        """Test max_results=0 returns no entities."""
        # Create 5 entities
        num_entities = 5
        batch_id, _ = create_test_entities(arkiv_client_http, num_entities)

        # Query with max_results=0
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(
            attributes=KEY | ATTRIBUTES,
            max_results=0,
            max_results_per_page=10,
        )

        iterator = arkiv_client_http.arkiv.query_entities(query=query, options=options)
        entities = list(iterator)

        # Should return no entities
        assert len(entities) == 0
