"""Tests for query result pagination."""

import logging
import uuid

from arkiv import Arkiv
from arkiv.types import (
    ATTRIBUTES,
    KEY,
    Attributes,
    CreateOp,
    EntityKey,
    Operations,
    QueryOptions,
)

EXPIRES_IN = 100
CONTENT_TYPE = "text/plain"

logger = logging.getLogger(__name__)


def create_test_entities(client: Arkiv, n: int) -> tuple[str, list[EntityKey]]:
    """
    Create n test entities with sequential numeric attributes for pagination testing.

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


class TestQueryPaging:
    """Test pagination of query results using cursors."""

    def test_query_paging_1_page(self, arkiv_client_http: Arkiv) -> None:
        """Test querying with max_results_per_page greater than total entities (single page)."""
        # Create 10 entities
        batch_id, entity_keys = create_test_entities(arkiv_client_http, 10)

        # Query with max_results_per_page > num entities (should get all in one page)
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(attributes=KEY | ATTRIBUTES, max_results_per_page=20)
        result = arkiv_client_http.arkiv.query_entities_page(
            query=query, options=options
        )

        # Should get all 10 entities in one page
        assert len(result.entities) == 10
        assert result.has_more() is False
        assert result.cursor is None

        # Verify all entities have the correct batch_id
        for entity in result.entities:
            assert entity.key in entity_keys
            assert entity.attributes is not None
            assert entity.attributes["batch_id"] == batch_id

    def test_query_paging_3_pages(self, arkiv_client_http: Arkiv) -> None:
        """Test pagination with 3 pages, last page not fully filled."""
        # Create 10 entities
        num_entities = 10
        batch_id, entity_keys = create_test_entities(arkiv_client_http, num_entities)

        # Query with max_results_per_page=10 (should need 3 pages: 10, 10, 5)
        query = f'batch_id = "{batch_id}"'
        max_results = 4
        options = QueryOptions(max_results_per_page=max_results)

        # Page 1: Should get 10 entities
        page1 = arkiv_client_http.arkiv.query_entities_page(
            query=query, options=options
        )
        logger.info(f"Page 1 cursor: {page1.cursor}")
        assert len(page1.entities) == max_results
        assert page1.has_more() is True
        assert page1.cursor is not None

        # Page 2: Should get 10 more entities
        options_page2 = QueryOptions(
            cursor=page1.cursor,
            max_results_per_page=max_results,
        )
        page2 = arkiv_client_http.arkiv.query_entities_page(
            query=query, options=options_page2
        )
        assert len(page2.entities) == max_results
        assert page2.has_more() is True
        assert page2.cursor is not None

        # Page 3: Should get remaining 5 entities
        options_page3 = QueryOptions(
            cursor=page2.cursor,
            max_results_per_page=max_results,
        )
        page3 = arkiv_client_http.arkiv.query_entities_page(
            query=query, options=options_page3
        )
        assert len(page3.entities) == 2
        assert page3.has_more() is False
        assert page3.cursor is None

        # Verify all entities across all pages have the correct batch_id
        all_entities = page1.entities + page2.entities + page3.entities
        assert len(all_entities) == num_entities

        for entity in all_entities:
            assert entity.key in entity_keys
            assert entity.attributes is not None
            assert entity.attributes["batch_id"] == batch_id

        # Verify all entities are unique
        all_keys = [entity.key for entity in all_entities]
        assert len(all_keys) == len(set(all_keys))

    def test_query_paging_empty_result(self, arkiv_client_http: Arkiv) -> None:
        """Test pagination with no matching entities."""
        # Query for a non-existent batch_id
        query = 'batch_id = "non-existent-batch-id-12345"'
        options = QueryOptions(attributes=KEY | ATTRIBUTES, max_results_per_page=10)
        result = arkiv_client_http.arkiv.query_entities_page(
            query=query, options=options
        )

        # Should get empty result with no more pages
        assert len(result.entities) == 0
        assert result.has_more() is False
        assert result.cursor is None

    def test_query_paging_exactly_one_page(self, arkiv_client_http: Arkiv) -> None:
        """Test pagination when entities exactly fill one page."""
        # Create exactly 5 entities
        num_entities = 5
        batch_id, entity_keys = create_test_entities(arkiv_client_http, num_entities)

        # Query with max_results_per_page = num_entities (exactly one full page)
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(
            attributes=KEY | ATTRIBUTES, max_results_per_page=num_entities
        )
        result = arkiv_client_http.arkiv.query_entities_page(
            query=query, options=options
        )

        # Should get all 5 entities in the first page
        assert len(result.entities) == num_entities

        # Verify all entities are from our batch
        for entity in result.entities:
            assert entity.key in entity_keys

        # Note: When the page is exactly full, the node may return has_more=True
        # and a cursor since it doesn't know if there are more entities until
        # the next page is fetched. If has_more is True, fetch the next page
        # to confirm it's empty.
        if result.has_more():
            assert result.cursor is not None
            options_page2 = QueryOptions(
                cursor=result.cursor,
                max_results_per_page=5,
            )
            page2 = arkiv_client_http.arkiv.query_entities_page(
                query=query, options=options_page2
            )
            # Second page should be empty
            assert len(page2.entities) == 0
            assert page2.has_more() is False

    def test_query_paging_max_results_smaller_than_page_size(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test that max_results limits total results when smaller than page size."""
        # Create 10 entities
        num_entities = 10
        batch_id, _ = create_test_entities(arkiv_client_http, num_entities)

        # Query with max_results=3 but max_results_per_page=100
        # Should only get 3 entities (max_results caps it)
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(
            attributes=KEY | ATTRIBUTES,
            max_results=3,
            max_results_per_page=100,
        )

        # Use iterator to verify max_results is respected
        iterator = arkiv_client_http.arkiv.query_entities(query=query, options=options)
        entities = list(iterator)

        assert len(entities) == 3

    def test_query_paging_max_results_spans_multiple_pages(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test that max_results limits total results across multiple pages."""
        # Create 10 entities
        num_entities = 10
        batch_id, _ = create_test_entities(arkiv_client_http, num_entities)

        # Query with max_results=7 and max_results_per_page=3
        # Should get 7 entities across 3 pages (3+3+1)
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(
            attributes=KEY | ATTRIBUTES,
            max_results=7,
            max_results_per_page=3,
        )

        # Use iterator to verify max_results is respected
        iterator = arkiv_client_http.arkiv.query_entities(query=query, options=options)
        entities = list(iterator)

        assert len(entities) == 7

    def test_query_paging_max_results_equals_total_entities(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test when max_results equals the total number of matching entities."""
        # Create 5 entities
        num_entities = 5
        batch_id, entity_keys = create_test_entities(arkiv_client_http, num_entities)

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
        for entity in entities:
            assert entity.key in entity_keys

    def test_query_paging_max_results_greater_than_total_entities(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test when max_results exceeds the total number of matching entities."""
        # Create 25 entities
        num_entities = 25
        batch_id, entity_keys = create_test_entities(arkiv_client_http, num_entities)

        # Query with max_results=100 (more than total)
        query = f'batch_id = "{batch_id}"'
        options = QueryOptions(
            attributes=KEY | ATTRIBUTES,
            max_results=100,
            max_results_per_page=10,
        )

        iterator = arkiv_client_http.arkiv.query_entities(query=query, options=options)
        entities = list(iterator)

        # Should get all available entities (max_results doesn't artificially limit)
        assert len(entities) == num_entities
        for entity in entities:
            assert entity.key in entity_keys
