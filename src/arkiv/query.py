"""Query utilities for Arkiv entity queries."""

from collections.abc import Iterator
from typing import TYPE_CHECKING

from .types import Entity, QueryResult

if TYPE_CHECKING:
    from .client import Arkiv


class QueryIterator:
    """
    Auto-paginating iterator for entity query results.

    This iterator automatically fetches subsequent pages as you iterate,
    providing a seamless way to process all matching entities without
    manual pagination.

    Warning:
        This iterator may make multiple network requests. Use appropriate
        limit values to avoid excessive API calls.

    Examples:
        >>> # Iterate over all matching entities
        >>> iterator = QueryIterator(client, "SELECT * WHERE owner = '0x...'", limit=100)
        >>> for entity in iterator:
        ...     process(entity)

        >>> # Process in batches
        >>> iterator = QueryIterator(client, "SELECT * ORDER BY created_at", limit=50)
        >>> batch = list(iterator)  # Fetches all pages
        >>> print(f"Total entities: {len(batch)}")

    Note:
        - The iterator maintains consistency by pinning to a specific block
        - Once exhausted, the iterator cannot be reused (create a new one)
        - All pages are fetched from the same blockchain state (block_number)
    """

    def __init__(
        self,
        client: "Arkiv",
        query: str,
        *,
        limit: int = 100,
        at_block: int | str = "latest",
    ):
        """
        Initialize the query iterator.

        Args:
            client: Arkiv client instance for making queries
            query: SQL-like query string
            limit: Number of entities to fetch per page (default: 100)
            at_block: Block number or "latest" to pin query to
        """
        self._client = client
        self._query = query
        self._limit = limit
        self._at_block = at_block
        self._current_result: QueryResult | None = None
        self._current_index = 0
        self._exhausted = False

    def __iter__(self) -> Iterator[Entity]:
        """Return the iterator instance."""
        return self

    def __next__(self) -> Entity:
        """
        Get the next entity, automatically fetching new pages as needed.

        Returns:
            Next Entity in the result set

        Raises:
            StopIteration: When all entities have been consumed
        """
        # Lazy initialization - fetch first page on first next()
        if self._current_result is None:
            self._current_result = self._client.arkiv.query_entities(
                self._query, limit=self._limit, at_block=self._at_block
            )

        # Yield from current page
        while self._current_index < len(self._current_result.entities):
            entity = self._current_result.entities[self._current_index]
            self._current_index += 1
            return entity

        # Fetch next page if available
        if self._current_result.has_more() and not self._exhausted:
            self._current_result = self._client.arkiv.query_entities(
                cursor=self._current_result.next_cursor
            )
            self._current_index = 0

            # Check if next page has entities
            if len(self._current_result.entities) == 0:
                self._exhausted = True
                raise StopIteration

            # Recurse to get first entity from new page
            return self.__next__()

        # No more entities
        raise StopIteration

    @property
    def block_number(self) -> int | None:
        """
        Get the block number at which this query is pinned.

        Returns:
            Block number if first page has been fetched, None otherwise
        """
        if self._current_result is not None:
            return self._current_result.block_number
        return None
