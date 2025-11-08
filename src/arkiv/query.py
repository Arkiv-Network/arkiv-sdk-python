"""Query utilities for Arkiv entity queries."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING

from .types import Entity, QueryOptions, QueryPage

if TYPE_CHECKING:
    from .client import Arkiv, AsyncArkiv

logger = logging.getLogger(__name__)


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

    def __init__(self, client: Arkiv, query: str, options: QueryOptions):
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
        self._options = options
        self._current_result: QueryPage | None = None
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
            logger.info(
                f"Fetching first page for query: {self._query}, options: {self._options}"
            )
            self._current_result = self._client.arkiv.query_entities_page(
                self._query, options=self._options
            )

        # Yield from current page
        while self._current_index < len(self._current_result.entities):
            entity = self._current_result.entities[self._current_index]
            self._current_index += 1
            return entity

        # Fetch next page if available
        if self._current_result.has_more() and not self._exhausted:
            options = QueryOptions(
                fields=self._options.fields,
                at_block=self._current_result.block_number,
                max_results_per_page=self._options.max_results_per_page,
                cursor=self._current_result.cursor,
            )
            logger.info(
                f"Fetching next page for query: {self._query}, options: {options}"
            )
            self._current_result = self._client.arkiv.query_entities_page(
                query=self._query, options=options
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


# TODO create base class for (Async)QueryIteratirs for shared functionality
class AsyncQueryIterator:
    """
    Auto-paginating async iterator for entity query results.

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

    def __init__(self, client: AsyncArkiv, query: str, options: QueryOptions):
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
        self._options = options
        self._current_result: QueryPage | None = None
        self._current_index = 0
        self._exhausted = False

    def __aiter__(self) -> AsyncQueryIterator:
        """Return the async iterator instance."""
        return self

    async def __anext__(self) -> Entity:
        """
        Get the next entity, automatically fetching new pages as needed.

        Returns:
            Next Entity in the result set

        Raises:
            StopAsyncIteration: When all entities have been consumed
        """
        # Lazy initialization - fetch first page on first next()
        if self._current_result is None:
            logger.info(
                f"Fetching first page for query: {self._query}, options: {self._options}"
            )
            self._current_result = await self._client.arkiv.query_entities_page(
                self._query, options=self._options
            )

        # Yield from current page
        while self._current_index < len(self._current_result.entities):
            entity = self._current_result.entities[self._current_index]
            self._current_index += 1
            return entity

        # Fetch next page if available
        if self._current_result.has_more() and not self._exhausted:
            options = QueryOptions(
                fields=self._options.fields,
                at_block=self._current_result.block_number,
                max_results_per_page=self._options.max_results_per_page,
                cursor=self._current_result.cursor,
            )
            logger.info(
                f"Fetching next page for query: {self._query}, options: {options}"
            )
            self._current_result = await self._client.arkiv.query_entities_page(
                query=self._query, options=options
            )
            self._current_index = 0

            # Check if next page has entities
            if len(self._current_result.entities) == 0:
                self._exhausted = True
                raise StopAsyncIteration

            # Recurse to get first entity from new page
            return await self.__anext__()

        # No more entities
        raise StopAsyncIteration

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
