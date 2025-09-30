"""Arkiv SDK Types."""

from collections.abc import Sequence
from dataclasses import dataclass

from eth_typing import ChecksumAddress, HexStr
from hexbytes import HexBytes


# Unique key for all entities
@dataclass(frozen=True)
class EntityKey:
    """EntityKey dataclass that wraps HexStr for entity identification."""

    value: HexStr

    def __init__(self, value: str | int | HexBytes | HexStr) -> None:
        """Create an EntityKey from various input types."""
        if isinstance(value, str) and value.startswith("0x"):
            # Already a hex string - validate length
            if len(value) != 66:  # 0x + 64 hex chars
                raise ValueError(
                    f"EntityKey hex string must be 66 characters (0x + 64 hex), got {len(value)}"
                )
            object.__setattr__(self, "value", HexStr(value.lower()))
        elif isinstance(value, int):
            # Convert integer to hex string with 0x prefix
            if value < 0:
                raise ValueError("EntityKey cannot be negative")
            hex_str = f"0x{value:064x}"  # 64 chars = 32 bytes = 256 bits
            object.__setattr__(self, "value", HexStr(hex_str))
        elif isinstance(value, (HexBytes, bytes)):
            # Convert bytes to hex string
            if len(value) != 32:  # 32 bytes = 256 bits
                raise ValueError(
                    f"EntityKey bytes must be exactly 32 bytes, got {len(value)}"
                )
            object.__setattr__(self, "value", HexStr(f"0x{value.hex()}"))
        elif isinstance(value, str):
            # Plain string, assume it needs 0x prefix
            if len(value) % 2 != 0:
                value = "0" + value  # Pad with leading zero if odd length
            if len(value) != 64:  # Should be 64 hex characters
                raise ValueError(
                    f"EntityKey hex string (without 0x) must be 64 characters, got {len(value)}"
                )
            object.__setattr__(self, "value", HexStr(f"0x{value.lower()}"))
        else:
            # Try to convert via HexBytes first, then to hex string
            try:
                hex_bytes = HexBytes(value)
                if len(hex_bytes) != 32:
                    raise ValueError(
                        f"EntityKey must represent exactly 32 bytes, got {len(hex_bytes)}"
                    )
                object.__setattr__(self, "value", HexStr(f"0x{hex_bytes.hex()}"))
            except Exception as e:
                raise ValueError(
                    f"Cannot convert {type(value)} to EntityKey: {e}"
                ) from e

    def __str__(self) -> str:
        """String representation."""
        return self.value

    def __repr__(self) -> str:
        """Repr representation."""
        return f"EntityKey('{self.value}')"

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if isinstance(other, EntityKey):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash(self.value)

    @property
    def hex(self) -> str:
        """Get hex string without 0x prefix."""
        return self.value[2:]

    def to_bytes(self) -> bytes:
        """Convert to bytes."""
        return bytes.fromhex(self.hex)


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
