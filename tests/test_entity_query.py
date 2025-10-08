"""Tests for entity query functionality."""

import pytest

from arkiv import Arkiv
from arkiv.types import Cursor


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
        with pytest.raises(ValueError, match="Must provide either query or cursor"):
            arkiv_client_http.arkiv.query_entities(query=None, cursor=None)

    def test_query_entities_accepts_query_only(self, arkiv_client_http: Arkiv) -> None:
        """Test that query_entities accepts query without cursor."""
        # Should not raise ValueError for missing cursor
        # Will raise NotImplementedError since method is not implemented yet
        with pytest.raises(NotImplementedError, match="not implemented yet"):
            arkiv_client_http.arkiv.query_entities(query="SELECT *")

    def test_query_entities_accepts_cursor_only(self, arkiv_client_http: Arkiv) -> None:
        """Test that query_entities accepts cursor without query."""
        # Create a dummy cursor (opaque string)
        cursor = Cursor("dummy_cursor_value")

        # Should not raise ValueError for missing query
        # Will raise NotImplementedError since method is not implemented yet
        with pytest.raises(NotImplementedError, match="not implemented yet"):
            arkiv_client_http.arkiv.query_entities(cursor=cursor)

    def test_query_entities_both_query_and_cursor_not_allowed(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test that query_entities rejects both query and cursor (mutually exclusive)."""
        cursor = Cursor("dummy_cursor_value")

        # Should raise ValueError when both are provided
        with pytest.raises(ValueError, match="Cannot provide both query and cursor"):
            arkiv_client_http.arkiv.query_entities(query="SELECT *", cursor=cursor)

    def test_query_entities_with_all_parameters(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test that query_entities accepts all parameters."""
        # Should not raise ValueError
        # Will raise NotImplementedError since method is not implemented yet
        with pytest.raises(NotImplementedError, match="not implemented yet"):
            arkiv_client_http.arkiv.query_entities(
                query="SELECT * WHERE owner = '0x1234'",
                limit=50,
                at_block=1000,
            )

    def test_query_entities_with_cursor_and_parameters(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test that query_entities accepts cursor with other parameters (which are ignored)."""
        cursor = Cursor("dummy_cursor_value")

        # Should not raise ValueError
        # Will raise NotImplementedError since method is not implemented yet
        with pytest.raises(NotImplementedError, match="not implemented yet"):
            arkiv_client_http.arkiv.query_entities(
                cursor=cursor,
                limit=100,  # Ignored when cursor is provided
                at_block=1000,  # Ignored when cursor is provided
            )
