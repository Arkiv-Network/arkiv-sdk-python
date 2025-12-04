"""Fluent query builder for Arkiv entity queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar, Union

from .types import (
    ALL,
    ASC,
    DESC,
    OrderByAttribute,
    QueryOptions,
)

if TYPE_CHECKING:
    from .client import Arkiv, AsyncArkiv
    from .query_iterator import AsyncQueryIterator, QueryIterator


# =============================================================================
# Expression Builder Classes (for type-safe WHERE clauses)
# =============================================================================


class Expr:
    """
    A composable SQL expression for WHERE clauses.

    Expr objects are created by comparison operators on IntAttr/StrAttr
    and can be combined using logical operators:
    - `&` (AND)
    - `|` (OR)
    - `~` (NOT)

    Operator precedence (tightest to loosest): ~ > & > |

    Examples:
        >>> age = IntAttr("age")
        >>> status = StrAttr("status")

        >>> expr = (age >= 18) & (status == "active")
        >>> expr.to_sql()
        'age >= 18 AND status = "active"'

        >>> expr = ~(status == "banned")
        >>> expr.to_sql()
        'NOT (status = "banned")'
    """

    def __init__(self, sql: str) -> None:
        """
        Initialize an expression with its SQL representation.

        Args:
            sql: The SQL string for this expression.
        """
        self._sql = sql

    def to_sql(self) -> str:
        """
        Return the SQL string representation of this expression.

        Returns:
            The SQL WHERE clause string.
        """
        return self._sql

    def __and__(self, other: Expr) -> Expr:
        """
        Combine with another expression using AND.

        Args:
            other: The expression to AND with.

        Returns:
            A new Expr representing (self AND other).
        """
        return Expr(f"{self._sql} AND {other._sql}")

    def __or__(self, other: Expr) -> Expr:
        """
        Combine with another expression using OR.

        Args:
            other: The expression to OR with.

        Returns:
            A new Expr representing (self OR other), wrapped in parentheses.
        """
        # Wrap in parentheses since OR has lower precedence
        return Expr(f"({self._sql} OR {other._sql})")

    def __invert__(self) -> Expr:
        """
        Negate this expression using NOT.

        Returns:
            A new Expr representing NOT (self).
        """
        return Expr(f"NOT ({self._sql})")

    def __repr__(self) -> str:
        """Return a string representation for debugging."""
        return f"Expr({self._sql!r})"


class IntAttr:
    """
    Integer attribute for building type-safe WHERE expressions.

    Provides comparison operators that return Expr objects and
    perform runtime type checking to ensure values are integers.

    Args:
        name: The attribute name.

    Examples:
        >>> age = IntAttr("age")
        >>> expr = age >= 18
        >>> expr.to_sql()
        'age >= 18'

        >>> # Type checking
        >>> age == "18"  # Raises TypeError
    """

    def __init__(self, name: str) -> None:
        """
        Initialize an integer attribute.

        Args:
            name: The attribute name.
        """
        self.name = name

    def _check_type(self, value: object) -> int:
        """Check that value is an int and return it."""
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(
                f"IntAttr '{self.name}' requires int, got {type(value).__name__}"
            )
        return value

    def __eq__(self, value: object) -> Expr:  # type: ignore[override]
        """Return an equality expression."""
        v = self._check_type(value)
        return Expr(f"{self.name} = {v}")

    def __ne__(self, value: object) -> Expr:  # type: ignore[override]
        """Return an inequality expression."""
        v = self._check_type(value)
        return Expr(f"{self.name} != {v}")

    def __gt__(self, value: object) -> Expr:
        """Return a greater-than expression."""
        v = self._check_type(value)
        return Expr(f"{self.name} > {v}")

    def __ge__(self, value: object) -> Expr:
        """Return a greater-than-or-equal expression."""
        v = self._check_type(value)
        return Expr(f"{self.name} >= {v}")

    def __lt__(self, value: object) -> Expr:
        """Return a less-than expression."""
        v = self._check_type(value)
        return Expr(f"{self.name} < {v}")

    def __le__(self, value: object) -> Expr:
        """Return a less-than-or-equal expression."""
        v = self._check_type(value)
        return Expr(f"{self.name} <= {v}")

    def __repr__(self) -> str:
        """Return a string representation for debugging."""
        return f"IntAttr({self.name!r})"


class StrAttr:
    """
    String attribute for building type-safe WHERE expressions.

    Provides comparison operators that return Expr objects and
    perform runtime type checking to ensure values are strings.

    Args:
        name: The attribute name.

    Examples:
        >>> status = StrAttr("status")
        >>> expr = status == "active"
        >>> expr.to_sql()
        'status = "active"'

        >>> # Type checking
        >>> status == 1  # Raises TypeError
    """

    def __init__(self, name: str) -> None:
        """
        Initialize a string attribute.

        Args:
            name: The attribute name.
        """
        self.name = name

    def _check_type(self, value: object) -> str:
        """Check that value is a str and return it."""
        if not isinstance(value, str):
            raise TypeError(
                f"StrAttr '{self.name}' requires str, got {type(value).__name__}"
            )
        return value

    def __eq__(self, value: object) -> Expr:  # type: ignore[override]
        """Return an equality expression."""
        v = self._check_type(value)
        return Expr(f'{self.name} = "{v}"')

    def __ne__(self, value: object) -> Expr:  # type: ignore[override]
        """Return an inequality expression."""
        v = self._check_type(value)
        return Expr(f'{self.name} != "{v}"')

    def __gt__(self, value: object) -> Expr:
        """Return a greater-than expression."""
        v = self._check_type(value)
        return Expr(f'{self.name} > "{v}"')

    def __ge__(self, value: object) -> Expr:
        """Return a greater-than-or-equal expression."""
        v = self._check_type(value)
        return Expr(f'{self.name} >= "{v}"')

    def __lt__(self, value: object) -> Expr:
        """Return a less-than expression."""
        v = self._check_type(value)
        return Expr(f'{self.name} < "{v}"')

    def __le__(self, value: object) -> Expr:
        """Return a less-than-or-equal expression."""
        v = self._check_type(value)
        return Expr(f'{self.name} <= "{v}"')

    def __repr__(self) -> str:
        """Return a string representation for debugging."""
        return f"StrAttr({self.name!r})"


# =============================================================================
# Sort Classes (for ORDER BY)
# =============================================================================


@dataclass(frozen=True)
class IntSort:
    """
    Integer attribute for ORDER BY clauses.

    Specifies that an attribute should be treated as a numeric value
    when sorting query results.

    Args:
        name: The attribute name to sort by
        direction: Sort direction - "asc" (default) or "desc"

    Examples:
        >>> # Sort by age descending
        >>> IntSort("age", DESC)

        >>> # Sort by priority ascending (default)
        >>> IntSort("priority")

        >>> # Using method chaining for direction
        >>> IntSort("age").desc()
    """

    name: str
    direction: str = ASC

    def asc(self) -> IntSort:
        """Return a copy with ascending direction."""
        return IntSort(self.name, ASC)

    def desc(self) -> IntSort:
        """Return a copy with descending direction."""
        return IntSort(self.name, DESC)

    def to_order_by_attribute(self) -> OrderByAttribute:
        """Convert to internal OrderByAttribute."""
        return OrderByAttribute(
            attribute=self.name,
            type="int",
            direction=self.direction,  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class StrSort:
    """
    String attribute for ORDER BY clauses.

    Specifies that an attribute should be treated as a string value
    when sorting query results.

    Args:
        name: The attribute name to sort by
        direction: Sort direction - "asc" (default) or "desc"

    Examples:
        >>> # Sort by name ascending (default)
        >>> StrSort("name")

        >>> # Sort by status descending
        >>> StrSort("status", DESC)

        >>> # Using method chaining for direction
        >>> StrSort("name").asc()
    """

    name: str
    direction: str = ASC

    def asc(self) -> StrSort:
        """Return a copy with ascending direction."""
        return StrSort(self.name, ASC)

    def desc(self) -> StrSort:
        """Return a copy with descending direction."""
        return StrSort(self.name, DESC)

    def to_order_by_attribute(self) -> OrderByAttribute:
        """Convert to internal OrderByAttribute."""
        return OrderByAttribute(
            attribute=self.name,
            type="str",
            direction=self.direction,  # type: ignore[arg-type]
        )


# Type variable for the client type
ClientT = TypeVar("ClientT", bound=Union["Arkiv", "AsyncArkiv"])

# Type variable for self-return in method chaining
SelfT = TypeVar("SelfT", bound="QueryBuilderBase[Any]")


class QueryBuilderBase(Generic[ClientT]):
    """
    Abstract base class for fluent query builders.

    Provides shared state and method implementations for building
    Arkiv queries using a fluent interface. Subclasses implement
    the terminal operations (fetch, count) for sync/async clients.

    The builder follows SQL query patterns:
    - select() - specify which fields to return
    - where() - filter condition (SQL-like string)
    - order_by() - sort results
    - at_block() - pin query to specific block
    - fetch() / count() - execute query
    """

    def __init__(self, client: ClientT, *fields: int) -> None:
        """
        Initialize the query builder.

        Args:
            client: The Arkiv client to execute queries with
            *fields: Field bitmask values to select (KEY, ATTRIBUTES, etc.)
                     If no fields provided, ALL fields are selected.
        """
        self._client: ClientT = client
        self._fields: int = self._combine_fields(fields) if fields else ALL
        self._query: str | None = None
        self._order_by: list[OrderByAttribute] = []
        self._at_block: int | None = None

    @staticmethod
    def _combine_fields(fields: tuple[int, ...]) -> int:
        """Combine multiple field bitmask values using OR."""
        result = 0
        for field in fields:
            result |= field
        return result

    def where(self: SelfT, condition: str | Expr) -> SelfT:
        """
        Set the WHERE clause for the query.

        Args:
            condition: SQL-like filter condition. Can be either:
                       - A string passed directly to the Arkiv node
                       - An Expr object built with IntAttr/StrAttr

        Returns:
            Self for method chaining.

        Examples:
            >>> # String condition
            >>> builder.where('type = "user"')
            >>> builder.where('age >= 18 AND status = "active"')

            >>> # Expression condition
            >>> builder.where(IntAttr("age") >= 18)
            >>> builder.where((IntAttr("age") >= 18) & (StrAttr("status") == "active"))
        """
        if isinstance(condition, Expr):
            self._query = condition.to_sql()
        else:
            self._query = condition
        return self

    def order_by(self: SelfT, *attributes: IntSort | StrSort) -> SelfT:
        """
        Set the ORDER BY clause for the query.

        Args:
            *attributes: One or more IntSort or StrSort instances
                         specifying the sort order.

        Returns:
            Self for method chaining.

        Examples:
            >>> # Single field
            >>> builder.order_by(IntSort("age", DESC))

            >>> # Multiple fields
            >>> builder.order_by(
            ...     StrSort("status"),
            ...     IntSort("age", DESC)
            ... )
        """
        self._order_by = [attr.to_order_by_attribute() for attr in attributes]
        return self

    def at_block(self: SelfT, block_number: int) -> SelfT:
        """
        Pin the query to a specific block number.

        Args:
            block_number: The block number to query at.

        Returns:
            Self for method chaining.

        Examples:
            >>> builder.at_block(12345)
        """
        self._at_block = block_number
        return self

    def _build_options(self) -> QueryOptions:
        """Build QueryOptions from the builder state."""
        return QueryOptions(
            attributes=self._fields,
            order_by=self._order_by if self._order_by else None,
            at_block=self._at_block,
        )

    def _get_query(self) -> str:
        """Get the query string, defaulting to match all if not set."""
        # If no WHERE clause provided, use a query that matches all entities
        # The Arkiv node requires a query string, so we use "1 = 1" as a match-all
        return self._query if self._query else "1 = 1"


class QueryBuilder(QueryBuilderBase["Arkiv"]):
    """
    Synchronous fluent query builder for Arkiv.

    Provides a fluent interface for building and executing entity queries
    with the synchronous Arkiv client.

    Examples:
        >>> from arkiv import Arkiv
        >>> from arkiv.query_builder import IntSort, StrSort
        >>> from arkiv.types import KEY, ATTRIBUTES

        >>> client = Arkiv("http://localhost:8545")

        >>> # Simple query
        >>> results = client.arkiv.select(KEY, ATTRIBUTES) \\
        ...     .where('type = "user"') \\
        ...     .fetch()
        >>> for entity in results:
        ...     print(entity.key)

        >>> # With sorting
        >>> results = client.arkiv.select() \\
        ...     .where('status = "active"') \\
        ...     .order_by(IntSort("priority", DESC)) \\
        ...     .fetch()

        >>> # Count entities
        >>> count = client.arkiv.select() \\
        ...     .where('type = "user"') \\
        ...     .count()
    """

    def fetch(self) -> QueryIterator:
        """
        Execute the query and return an iterator over results.

        Returns:
            QueryIterator that yields Entity objects across all pages.
        """
        from .query_iterator import QueryIterator

        return QueryIterator(
            client=self._client,
            query=self._get_query(),
            options=self._build_options(),
        )

    def count(self) -> int:
        """
        Execute the query and return the count of matching entities.

        This is optimized to only fetch entity keys for counting.

        Returns:
            Number of entities matching the query.
        """
        from .types import KEY

        # Use KEY-only fields for efficient counting
        options = QueryOptions(
            attributes=KEY,
            order_by=self._order_by if self._order_by else None,
            at_block=self._at_block,
        )

        from .query_iterator import QueryIterator

        iterator = QueryIterator(
            client=self._client,
            query=self._get_query(),
            options=options,
        )

        return sum(1 for _ in iterator)


class AsyncQueryBuilder(QueryBuilderBase["AsyncArkiv"]):
    """
    Asynchronous fluent query builder for Arkiv.

    Provides a fluent interface for building and executing entity queries
    with the asynchronous AsyncArkiv client.

    Examples:
        >>> from arkiv import AsyncArkiv
        >>> from arkiv.query_builder import IntSort, StrSort
        >>> from arkiv.types import KEY, ATTRIBUTES

        >>> async with AsyncArkiv("http://localhost:8545") as client:
        ...     # Simple query
        ...     results = client.arkiv.select(KEY, ATTRIBUTES) \\
        ...         .where('type = "user"') \\
        ...         .fetch()
        ...     async for entity in results:
        ...         print(entity.key)
        ...
        ...     # Count entities
        ...     count = await client.arkiv.select() \\
        ...         .where('type = "user"') \\
        ...         .count()
    """

    def fetch(self) -> AsyncQueryIterator:
        """
        Execute the query and return an async iterator over results.

        Returns:
            AsyncQueryIterator that yields Entity objects across all pages.
        """
        from .query_iterator import AsyncQueryIterator

        return AsyncQueryIterator(
            client=self._client,
            query=self._get_query(),
            options=self._build_options(),
        )

    async def count(self) -> int:
        """
        Execute the query and return the count of matching entities.

        This is optimized to only fetch entity keys for counting.

        Returns:
            Number of entities matching the query.
        """
        from .types import KEY

        # Use KEY-only fields for efficient counting
        options = QueryOptions(
            attributes=KEY,
            order_by=self._order_by if self._order_by else None,
            at_block=self._at_block,
        )

        from .query_iterator import AsyncQueryIterator

        iterator = AsyncQueryIterator(
            client=self._client,
            query=self._get_query(),
            options=options,
        )

        count = 0
        async for _ in iterator:
            count += 1
        return count
