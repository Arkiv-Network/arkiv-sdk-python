"""Arkiv SDK Types."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import NewType

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
class CreateReceipt:
    """The return type of a create operation."""

    entity_key: EntityKey
    expiration_block: int


@dataclass(frozen=True)
class UpdateReceipt:
    """The return type of an update operation."""

    entity_key: EntityKey
    expiration_block: int


@dataclass(frozen=True)
class ExtendReceipt:
    """The return type of an extend operation."""

    entity_key: EntityKey
    old_expiration_block: int
    new_expiration_block: int


@dataclass(frozen=True)
class DeleteReceipt:
    """The return type of a delete operation."""

    entity_key: EntityKey


@dataclass(frozen=True)
class TransactionReceipt:
    """The return type of a transaction."""

    tx_hash: TxHash
    creates: Sequence[CreateReceipt]
    updates: Sequence[UpdateReceipt]
    extensions: Sequence[ExtendReceipt]
    deletes: Sequence[DeleteReceipt]


# Low level annotations for RLP encoding
StringAnnotationsRlp = NewType("StringAnnotationsRlp", list[tuple[str, str]])
NumericAnnotationsRlp = NewType("NumericAnnotationsRlp", list[tuple[str, int]])

# Low level annotations for entity decoding
StringAnnotations = NewType("StringAnnotations", AttributeDict[str, str])
NumericAnnotations = NewType("NumericAnnotations", AttributeDict[str, int])
