"""Arkiv SDK Types."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import NewType

from eth_typing import ChecksumAddress, HexStr
from hexbytes import HexBytes

# Unique key for all entities
EntityKey = NewType("EntityKey", HexStr)


type AnnotationValue = str | int  # Only str or non-negative int allowed


@dataclass(frozen=True)
class Annotation:
    """Class to represent annotations with string or non-negative integer values."""

    key: str
    value: AnnotationValue

    def __post_init__(self) -> None:
        """Validate that integer values are non-negative."""
        if isinstance(self.value, int) and self.value < 0:
            raise ValueError(
                f"Integer annotation values must be non-negative, got: {self.value}"
            )

    # @override
    def __repr__(self) -> str:
        """Encode annotation as a string."""
        return f"{type(self).__name__}({self.key} -> {self.value})"


@dataclass(frozen=True)
class Metadata:
    """A class representing entity metadata."""

    owner: ChecksumAddress
    expires_at_block: int


@dataclass(frozen=True)
class Entity:
    """A class representing an entity."""

    entity_key: EntityKey
    metadata: Metadata | None
    payload: bytes | None
    annotations: dict[str, AnnotationValue] | None


@dataclass(frozen=True)
class CreateOp:
    """Class to represent a create operation."""

    data: bytes
    btl: int
    string_annotations: Sequence[Annotation]
    numeric_annotations: Sequence[Annotation]


@dataclass(frozen=True)
class UpdateOp:
    """Class to represent an update operation."""

    entity_key: EntityKey
    data: bytes
    btl: int
    string_annotations: Sequence[Annotation]
    numeric_annotations: Sequence[Annotation]


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

    tx_hash: HexBytes
    creates: Sequence[CreateReceipt]
    updates: Sequence[UpdateReceipt]
    extensions: Sequence[ExtendReceipt]
    deletes: Sequence[DeleteReceipt]
