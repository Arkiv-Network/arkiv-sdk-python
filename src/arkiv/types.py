"""Type definitions for the Arkiv SDK."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Literal, NewType

from eth_typing import BlockNumber, ChecksumAddress, HexStr
from web3.datastructures import AttributeDict

# Field bitmask values to specify which entity fields are populated
KEY = 1
ATTRIBUTES = 2
PAYLOAD = 4
CONTENT_TYPE = 8
EXPIRATION = 16
OWNER = 32
LAST_MODIFIED_AT = 64
CREATED_AT = 128
TX_INDEX_IN_BLOCK = 256
OP_INDEX_IN_TX = 512

NONE = 0
ALL = (
    KEY
    | ATTRIBUTES
    | PAYLOAD
    | CONTENT_TYPE
    | EXPIRATION
    | OWNER
    | CREATED_AT
    | LAST_MODIFIED_AT
    | TX_INDEX_IN_BLOCK
    | OP_INDEX_IN_TX
)

MAX_RESULTS_PER_PAGE_DEFAULT = 20

# Cursor type for entity set pagination for query results
Cursor = NewType("Cursor", str)


@dataclass(frozen=True)
class QueryOptions:
    """Options for querying entities."""

    fields: int = ALL  # Bitmask of fields to populate
    at_block: int | None = (
        None  # Block number to pin query to specific block, or None to use latest block available
    )
    max_results_per_page: int = (
        MAX_RESULTS_PER_PAGE_DEFAULT  # Max number of entities to fetch per page
    )
    cursor: Cursor | None = None  # Cursor for pagination

    def validate(self, query: str | None) -> None:
        # Validates fields
        if self.fields is not None:
            if self.fields < 0:
                raise ValueError(f"Fields cannot be negative: {self.fields}")

            if self.fields > ALL:
                raise ValueError(f"Fields contains unknown field flags: {self.fields}")

        # Validate that at least one of query or cursor is provided
        if query is None:
            raise ValueError("Must provide query")

        if query is not None and len(query.strip()) == 0:
            raise ValueError("Query string cannot be empty")


QUERY_OPTIONS_DEFAULT: QueryOptions = QueryOptions()

# Transaction hash type
TxHash = NewType("TxHash", HexStr)

# Unique key for all entities
EntityKey = NewType("EntityKey", HexStr)

# Entity attributes
Attributes = NewType("Attributes", dict[str, str | int])


@dataclass(frozen=True)
class Entity:
    """A class representing an entity.

    Entities are immutable snapshots of data at a point in time.
    To create modified copies, use dataclasses.replace().

    Examples:
        from dataclasses import replace

        # Get an entity
        entity = client.arkiv.get_entity(entity_key)

        # Create a copy with modified payload
        new_entity = replace(entity, payload=b"new data")

        # Create a copy with modified attributes (creates new dict)
        new_entity = replace(
            entity,
            attributes=Attributes({**entity.attributes, "version": 2})
        )

    Note:
        The attributes field is a dict. When using replace(), always
        create a new dict if you want to modify attributes to avoid
        sharing the same dict instance between entities.

        Use dict unpacking {**dict} to create a new dict while merging
        existing values with new ones.
    """

    key: EntityKey | None = None  # Unique identifier for the entity
    fields: int = ALL  # Bitmask representing which fields are populated
    owner: ChecksumAddress | None = None
    created_at_block: int | None = None
    last_modified_at_block: int | None = None
    expires_at_block: int | None = None
    transaction_index: int | None = None
    operation_index: int | None = None

    # Populated when fields | PAYLOAD returns true
    payload: bytes | None = None
    content_type: str | None = None

    # Populated when fields | ATTRIBUTES returns true
    attributes: Attributes | None = None


@dataclass(frozen=True)
class QueryPage:
    """
    Single page result of an entity query operation.

    Attributes:
        entities: List of entities matching the query.
            Empty list if no entities match the query criteria.
        block_number: Block number at which the query was executed.
            All pages of a query result set MUST use the same block_number
            to ensure consistency across pagination.
        next_cursor: Cursor for fetching the next page of results.
            None if this is the last page or all results fit in one page.
            The cursor implicitly carries the block_number for consistency.

    Example:
        >>> page = arkiv.query_entities("SELECT * WHERE owner = '0x...' LIMIT 50")
        >>> print(f"Found {len(page)} at block {page.block_number}")
        >>>
        >>> # Pagination (automatically uses same block_number)
        >>> while page.has_more():
        ...     page = arkiv.query_entities(cursor=page.next_cursor)
        ...     print(f"Page entities: {page.entities}")
    """

    entities: list[Entity]
    block_number: int
    cursor: Cursor | None = None

    def __len__(self) -> int:
        """len(result) -> number of entities"""
        return len(self.entities)

    def __bool__(self) -> bool:
        """bool(result) -> True if has entities"""
        return len(self.entities) > 0

    def __iter__(self) -> Iterator[Entity]:
        """for entity in result: ... -> iterate entities"""
        return iter(self.entities)

    def __getitem__(self, index: int) -> Entity:
        """result[0] -> first entity"""
        return self.entities[index]

    def has_more(self) -> bool:
        """Check if more results available"""
        return self.cursor is not None


@dataclass(frozen=True)
class CreateOp:
    """Class to represent a create operation."""

    payload: bytes
    content_type: str
    attributes: Attributes
    btl: int


@dataclass(frozen=True)
class UpdateOp:
    """Class to represent an update operation."""

    key: EntityKey
    payload: bytes
    content_type: str
    attributes: Attributes
    btl: int


@dataclass(frozen=True)
class DeleteOp:
    """Class to represent a delete operation."""

    key: EntityKey


@dataclass(frozen=True)
class ExtendOp:
    """Class to represent a entity lifetime extend operation."""

    key: EntityKey
    number_of_blocks: int


@dataclass(frozen=True)
class ChangeOwnerOp:
    """Class to represent a change owner operation."""

    key: EntityKey
    new_owner: ChecksumAddress


@dataclass(frozen=True)
class Operations:
    """
    Class to represent a transaction operations.

    A transaction consist of one or more lists of
    - `EntityCreate`
    - `EntityUpdate`
    - `EntityDelete`
    - `EntityExtend`
    - `ChangeOwner`
    operations.
    """

    def __init__(
        self,
        *,
        creates: Sequence[CreateOp] | None = None,
        updates: Sequence[UpdateOp] | None = None,
        deletes: Sequence[DeleteOp] | None = None,
        extensions: Sequence[ExtendOp] | None = None,
        change_owners: Sequence[ChangeOwnerOp] | None = None,
    ):
        """Initialise the GolemBaseTransaction instance."""
        object.__setattr__(self, "creates", creates or [])
        object.__setattr__(self, "updates", updates or [])
        object.__setattr__(self, "deletes", deletes or [])
        object.__setattr__(self, "extensions", extensions or [])
        object.__setattr__(self, "change_owners", change_owners or [])
        if not (
            self.creates
            or self.updates
            or self.deletes
            or self.extensions
            or self.change_owners
        ):
            raise ValueError("At least one operation must be provided")

    creates: Sequence[CreateOp]
    updates: Sequence[UpdateOp]
    deletes: Sequence[DeleteOp]
    extensions: Sequence[ExtendOp]
    change_owners: Sequence[ChangeOwnerOp]


@dataclass(frozen=True)
class EntityEvent:
    """Base class for events emitted when an entity is modified."""

    key: EntityKey


@dataclass(frozen=True)
class EntityOwnerEvent(EntityEvent):
    """Base class for events emitted when an entity is modified."""

    owner_address: ChecksumAddress


@dataclass(frozen=True)
class CreateEvent(EntityOwnerEvent):
    """Event emitted when an entity is created."""

    expiration_block: int
    cost: int


@dataclass(frozen=True)
class UpdateEvent(EntityOwnerEvent):
    """Event emitted when an entity is updated."""

    old_expiration_block: int
    new_expiration_block: int
    cost: int


@dataclass(frozen=True)
class ExpiryEvent(EntityOwnerEvent):
    """Event emitted when an entity is expired."""

    pass


@dataclass(frozen=True)
class DeleteEvent(EntityOwnerEvent):
    """Event emitted when an entity is deleted."""

    pass


@dataclass(frozen=True)
class ExtendEvent(EntityOwnerEvent):
    """Event emitted when an entity's lifetime is extended."""

    old_expiration_block: int
    new_expiration_block: int
    cost: int


@dataclass(frozen=True)
class ChangeOwnerEvent(EntityEvent):
    """Event emitted when an entity's owner is changed."""

    old_owner_address: ChecksumAddress
    new_owner_address: ChecksumAddress


@dataclass(frozen=True)
class CreateEventLegacy(EntityEvent):
    """Event emitted when an entity is created (legacy)."""

    expiration_block: int
    cost: int


@dataclass(frozen=True)
class TransactionReceipt:
    """Receipt of a transaction containing all emitted events."""

    block_number: BlockNumber
    tx_hash: TxHash
    creates: Sequence[CreateEvent]
    updates: Sequence[UpdateEvent]
    extensions: Sequence[ExtendEvent]
    deletes: Sequence[DeleteEvent]
    change_owners: Sequence[ChangeOwnerEvent]


# Event callback types
CreateCallback = Callable[[CreateEvent, TxHash], None]
UpdateCallback = Callable[[UpdateEvent, TxHash], None]
DeleteCallback = Callable[[DeleteEvent, TxHash], None]
ExtendCallback = Callable[[ExtendEvent, TxHash], None]
ChangeOwnerCallback = Callable[[ChangeOwnerEvent, TxHash], None]

# Async event callback types
AsyncCreateCallback = Callable[[CreateEvent, TxHash], Awaitable[None]]
AsyncUpdateCallback = Callable[[UpdateEvent, TxHash], Awaitable[None]]
AsyncDeleteCallback = Callable[[DeleteEvent, TxHash], Awaitable[None]]
AsyncExtendCallback = Callable[[ExtendEvent, TxHash], Awaitable[None]]
AsyncChangeOwnerCallback = Callable[[ChangeOwnerEvent, TxHash], Awaitable[None]]

# Event type literal
EventType = Literal["created", "updated", "deleted", "extended", "owner_changed"]

# Low level attributes for RLP encoding
StringAttributesRlp = NewType("StringAttributesRlp", list[tuple[str, str]])
NumericAttributesRlp = NewType("NumericAttributesRlp", list[tuple[str, int]])

# Low level attributes for entity decoding
StringAttributes = NewType("StringAttributes", AttributeDict[str, str])
NumericAttributes = NewType("NumericAttributes", AttributeDict[str, int])


# Low level query result for entity query
@dataclass(frozen=True)
class QueryEntitiesResult:
    """A class representing the return value of a Golem Base query."""

    entity_key: EntityKey
    storage_value: bytes
