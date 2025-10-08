"""Type definitions for the Arkiv SDK."""

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Literal, NewType

from eth_typing import ChecksumAddress, HexStr
from web3.datastructures import AttributeDict

# Field bitmask values to specify which entity fields are populated
PAYLOAD = 1
ANNOTATIONS = 2
METADATA = 4
NONE = 0
ALL = PAYLOAD | ANNOTATIONS | METADATA

# Transaction hash type
TxHash = NewType("TxHash", HexStr)

# Unique key for all entities
EntityKey = NewType("EntityKey", HexStr)

# Entity annotations
Annotations = NewType("Annotations", dict[str, str | int])


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

        # Create a copy with modified annotations (creates new dict)
        new_entity = replace(
            entity,
            annotations=Annotations({**entity.annotations, "version": 2})
        )

    Note:
        The annotations field is a dict. When using replace(), always
        create a new dict if you want to modify annotations to avoid
        sharing the same dict instance between entities.

        Use dict unpacking {**dict} to create a new dict while merging
        existing values with new ones.
    """

    entity_key: EntityKey  # Unique identifier for the entity
    fields: int  # Bitmask representing which fields are populated

    # Populated when fields | METADATA returns true
    owner: ChecksumAddress | None
    expires_at_block: int | None

    # Populated when fields | PAYLOAD returns true
    payload: bytes | None

    # Populated when fields | ANNOTATIONS returns true
    annotations: Annotations | None


# Cursor type for entity set pagination for query results
Cursor = NewType("Cursor", str)


@dataclass(frozen=True)
class QueryResult:
    """
    Result of an entity query operation.

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
        >>> result = arkiv.query_entities("SELECT * WHERE owner = '0x...' LIMIT 50")
        >>> print(f"Found {len(result)} at block {result.block_number}")
        >>>
        >>> # Pagination (automatically uses same block_number)
        >>> while result.has_more():
        ...     result = arkiv.query_entities(cursor=result.next_cursor)
        ...     print(f"Page entities: {result.entities}")
    """

    entities: list[Entity]
    block_number: int
    next_cursor: Cursor | None = None

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
        return self.next_cursor is not None


@dataclass(frozen=True)
class CreateOp:
    """Class to represent a create operation."""

    payload: bytes
    annotations: Annotations
    btl: int


@dataclass(frozen=True)
class UpdateOp:
    """Class to represent an update operation."""

    entity_key: EntityKey
    payload: bytes
    annotations: Annotations
    btl: int


@dataclass(frozen=True)
class DeleteOp:
    """Class to represent a delete operation."""

    entity_key: EntityKey


@dataclass(frozen=True)
class ExtendOp:
    """Class to represent a entity lifetime extend operation."""

    entity_key: EntityKey
    number_of_blocks: int


@dataclass(frozen=True)
class Operations:
    """
    Class to represent a transaction operations.

    A transaction consist of one or more lists of
    - `EntityCreate`
    - `EntityUpdate`
    - `EntityDelete`
    - `EntityExtend`
    operations.
    """

    def __init__(
        self,
        *,
        creates: Sequence[CreateOp] | None = None,
        updates: Sequence[UpdateOp] | None = None,
        deletes: Sequence[DeleteOp] | None = None,
        extensions: Sequence[ExtendOp] | None = None,
    ):
        """Initialise the GolemBaseTransaction instance."""
        object.__setattr__(self, "creates", creates or [])
        object.__setattr__(self, "updates", updates or [])
        object.__setattr__(self, "deletes", deletes or [])
        object.__setattr__(self, "extensions", extensions or [])
        if not (self.creates or self.updates or self.deletes or self.extensions):
            raise ValueError("At least one operation must be provided")

    creates: Sequence[CreateOp]
    updates: Sequence[UpdateOp]
    deletes: Sequence[DeleteOp]
    extensions: Sequence[ExtendOp]


@dataclass(frozen=True)
class CreateEvent:
    """Event emitted when an entity is created."""

    entity_key: EntityKey
    expiration_block: int


@dataclass(frozen=True)
class UpdateEvent:
    """Event emitted when an entity is updated."""

    entity_key: EntityKey
    expiration_block: int


@dataclass(frozen=True)
class ExtendEvent:
    """Event emitted when an entity's lifetime is extended."""

    entity_key: EntityKey
    old_expiration_block: int
    new_expiration_block: int


@dataclass(frozen=True)
class DeleteEvent:
    """Event emitted when an entity is deleted."""

    entity_key: EntityKey


@dataclass(frozen=True)
class TransactionReceipt:
    """Receipt of a transaction containing all emitted events."""

    tx_hash: TxHash
    creates: Sequence[CreateEvent]
    updates: Sequence[UpdateEvent]
    extensions: Sequence[ExtendEvent]
    deletes: Sequence[DeleteEvent]


# Event callback types
CreateCallback = Callable[[CreateEvent, TxHash], None]
UpdateCallback = Callable[[UpdateEvent, TxHash], None]
DeleteCallback = Callable[[DeleteEvent, TxHash], None]
ExtendCallback = Callable[[ExtendEvent, TxHash], None]

# Event type literal
EventType = Literal["created", "updated", "deleted", "extended"]

# Low level annotations for RLP encoding
StringAnnotationsRlp = NewType("StringAnnotationsRlp", list[tuple[str, str]])
NumericAnnotationsRlp = NewType("NumericAnnotationsRlp", list[tuple[str, int]])

# Low level annotations for entity decoding
StringAnnotations = NewType("StringAnnotations", AttributeDict[str, str])
NumericAnnotations = NewType("NumericAnnotations", AttributeDict[str, int])


# Low level query result for entity query
@dataclass(frozen=True)
class QueryEntitiesResult:
    """A class representing the return value of a Golem Base query."""

    entity_key: EntityKey
    storage_value: bytes
