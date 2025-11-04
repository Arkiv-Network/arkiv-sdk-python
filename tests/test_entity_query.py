"""Tests for entity query functionality."""

import uuid

import pytest

from arkiv import Arkiv
from arkiv.types import ALL, Attributes, Cursor
from arkiv.utils import to_query_options


class TestQueryEntitiesParameterValidation:
    """Test parameter validation for query_entities method."""

    def test_query_entities_requires_query_or_cursor(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test that query_entities raises ValueError when neither query nor cursor is provided."""
        with pytest.raises(ValueError, match="Must provide either query or cursor"):
            arkiv_client_http.arkiv.query_entities()

    def test_query_entities_validates_none_for_both(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test that explicitly passing None for both query and cursor raises ValueError."""
        query_options = to_query_options()
        with pytest.raises(ValueError, match="Must provide either query or cursor"):
            arkiv_client_http.arkiv.query_entities(options=query_options)

    def test_query_entities_accepts_query_only(self, arkiv_client_http: Arkiv) -> None:
        """Test that query_entities accepts query without cursor."""
        # Should not raise ValueError for missing cursor
        # Query will execute (returns empty result since no matching entities exist)
        result = arkiv_client_http.arkiv.query_entities(
            query='owner = "0x0000000000000000000000000000000000000000"'
        )
        assert not result  # check for falsy result
        assert len(result) == 0  # No entities match this owner

    @pytest.mark.skip(
        reason="TODO: Revisit once cursor-based queries are properly tested. Currently fails with invalid cursor error."
    )
    def test_query_entities_accepts_cursor_only(self, arkiv_client_http: Arkiv) -> None:
        """Test that query_entities accepts cursor without query."""
        # Create a dummy cursor (opaque string)
        cursor = Cursor("dummy_cursor_value")
        query_options = to_query_options(cursor=cursor)

        # Should not raise ValueError for missing query
        # Will raise NotImplementedError since cursor-based pagination is not yet implemented
        arkiv_client_http.arkiv.query_entities(options=query_options)

    def test_query_entities_both_query_and_cursor_not_allowed(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test that query_entities rejects both query and cursor (mutually exclusive)."""
        query = '$owner = "0x0000000000000000000000000000000000000000"'
        cursor = Cursor("dummy_cursor_value")
        query_options = to_query_options(cursor=cursor)

        # Should raise ValueError when both query and cursor are provided
        with pytest.raises(ValueError, match="Cannot provide both query and cursor"):
            arkiv_client_http.arkiv.query_entities(
                query=query,
                options=query_options,
            )

    def test_query_entities_with_all_parameters(self, arkiv_client_http: Arkiv) -> None:
        """Test that query_entities accepts all parameters."""
        # Should not raise ValueError
        arkiv_client_http.arkiv.create_entity(
            payload=b"Some payload",
            content_type="text/plain",
        )
        # Query will execute (returns empty result since no matching entities exist)
        query = '$owner = "0x0000000000000000000000000000000000000000"'

        # TODO at_block > latest block has the effect of runnint into a timeout
        query_options = to_query_options(
            fields=ALL, max_results_per_page=50, at_block=None, cursor=None
        )
        result = arkiv_client_http.arkiv.query_entities(
            query=query, options=query_options
        )
        assert len(result) == 0  # No entities match this owner


class TestQueryEntitiesBasic:
    """Test basic entity querying functionality."""

    def test_query_entities_by_attribute(self, arkiv_client_http: Arkiv) -> None:
        """Test querying entities by attribute value."""
        # Generate a unique ID without special characters (UUID without hyphens)
        shared_id = str(uuid.uuid4()).replace("-", "")

        # Create 3 entities with the same 'id' attribute
        entity_keys = []
        for i in range(3):
            entity_key, _ = arkiv_client_http.arkiv.create_entity(
                payload=f"Entity {i}".encode(),
                content_type="text/plain",
                attributes=Attributes({"id": shared_id}),
                btl=100,  # Set blocks to live (required by Arkiv node)
            )
            entity_keys.append(entity_key)

        # Query for entities with the shared ID
        # Note: Using Arkiv query syntax with double quotes for string values
        query = f'id = "{shared_id}"'
        result = arkiv_client_http.arkiv.query_entities(query=query)

        # Verify result basics
        assert result  # Check __bool__()
        assert result.block_number > 0
        assert result.has_more() is False
        assert result.cursor is None  # only 3 results, no pagination needed

        # Verify we got back all 3 entities
        assert len(result.entities) == 3

        # Verify the entity keys match (order may differ)
        result_keys = {entity.entity_key for entity in result.entities}
        expected_keys = set(entity_keys)
        assert result_keys == expected_keys
