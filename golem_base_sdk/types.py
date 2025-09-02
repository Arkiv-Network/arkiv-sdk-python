"""Golem Base SDK Types."""

from collections.abc import Callable, Coroutine, Sequence
from dataclasses import dataclass
from typing import (
    Any,
    Generic,
    NewType,
    TypeVar,
)

from eth_typing import ChecksumAddress, HexStr
from web3 import AsyncWeb3
from web3.types import Wei


@dataclass(frozen=True)
class GenericBytes:
    """Class to represent bytes that can be converted to more meaningful types."""

    generic_bytes: bytes

    def as_hex_string(self) -> HexStr:
        """Convert this instance to a hexadecimal string."""
        return HexStr("0x" + self.generic_bytes.hex())

    def as_address(self) -> ChecksumAddress:
        """Convert this instance to a `eth_typing.ChecksumAddress`."""
        return AsyncWeb3.to_checksum_address(self.as_hex_string())

    # @override
    def __repr__(self) -> str:
        """Encode bytes as a string."""
        return f"{type(self).__name__}({self.as_hex_string()})"

    @staticmethod
    def from_hex_string(hexstr: str) -> "GenericBytes":
        """Create a `GenericBytes` instance from a hexadecimal string."""
        assert hexstr.startswith("0x")
        assert len(hexstr) % 2 == 0

        return GenericBytes(bytes.fromhex(hexstr[2:]))


EntityKey = NewType("EntityKey", GenericBytes)
Address = NewType("Address", GenericBytes)


# TODO: use new generic syntax once we can bump to python 3.12 or higher
V = TypeVar("V")


@dataclass(frozen=True)
class Annotation(Generic[V]):
    """Class to represent generic annotations."""

    key: str
    value: V

    # @override
    def __repr__(self) -> str:
        """Encode annotation as a string."""
        return f"{type(self).__name__}({self.key} -> {self.value})"


@dataclass(frozen=True)
class GolemBaseCreate:
    """Class to represent a create operation in Golem Base."""

    data: bytes
    btl: int
    string_annotations: Sequence[Annotation[str]]
    numeric_annotations: Sequence[Annotation[int]]


@dataclass(frozen=True)
class GolemBaseUpdate:
    """Class to represent an update operation in Golem Base."""

    entity_key: EntityKey
    data: bytes
    btl: int
    string_annotations: Sequence[Annotation[str]]
    numeric_annotations: Sequence[Annotation[int]]


@dataclass(frozen=True)
class GolemBaseDelete:
    """Class to represent a delete operation in Golem Base."""

    entity_key: EntityKey


@dataclass(frozen=True)
class GolemBaseExtend:
    """Class to represent a BTL extend operation in Golem Base."""

    entity_key: EntityKey
    number_of_blocks: int


@dataclass(frozen=True)
class GolemBaseTransaction:
    """
    Class to represent a transaction in Golem Base.

    A transaction consist of one or more
    `GolemBaseCreate`,
    `GolemBaseUpdate`,
    `GolemBaseDelete` and
    `GolemBaseExtend`
    operations.
    """

    def __init__(
        self,
        *,
        creates: Sequence[GolemBaseCreate] | None = None,
        updates: Sequence[GolemBaseUpdate] | None = None,
        deletes: Sequence[GolemBaseDelete] | None = None,
        extensions: Sequence[GolemBaseExtend] | None = None,
        gas: int | None = None,
        maxFeePerGas: Wei | None = None,
        maxPriorityFeePerGas: Wei | None = None,
    ):
        """Initialise the GolemBaseTransaction instance."""
        object.__setattr__(self, "creates", creates or [])
        object.__setattr__(self, "updates", updates or [])
        object.__setattr__(self, "deletes", deletes or [])
        object.__setattr__(self, "extensions", extensions or [])
        object.__setattr__(self, "gas", gas)
        object.__setattr__(self, "maxFeePerGas", maxFeePerGas)
        object.__setattr__(self, "maxPriorityFeePerGas", maxPriorityFeePerGas)

    creates: Sequence[GolemBaseCreate]
    updates: Sequence[GolemBaseUpdate]
    deletes: Sequence[GolemBaseDelete]
    extensions: Sequence[GolemBaseExtend]
    gas: int | None
    maxFeePerGas: Wei | None
    maxPriorityFeePerGas: Wei | None


@dataclass(frozen=True)
class CreateEntityReturnType:
    """The return type of a Golem Base create operation."""

    expiration_block: int
    entity_key: EntityKey


@dataclass(frozen=True)
class UpdateEntityReturnType:
    """The return type of a Golem Base update operation."""

    expiration_block: int
    entity_key: EntityKey


@dataclass(frozen=True)
class ExtendEntityReturnType:
    """The return type of a Golem Base extend operation."""

    old_expiration_block: int
    new_expiration_block: int
    entity_key: EntityKey


@dataclass(frozen=True)
class GolemBaseTransactionReceipt:
    """The return type of a Golem Base transaction."""

    creates: Sequence[CreateEntityReturnType]
    updates: Sequence[UpdateEntityReturnType]
    extensions: Sequence[ExtendEntityReturnType]
    deletes: Sequence[EntityKey]


@dataclass(frozen=True)
class EntityMetadata:
    """A class representing entity metadata."""

    entity_key: EntityKey
    owner: Address
    expires_at_block: int
    string_annotations: Sequence[Annotation[str]]
    numeric_annotations: Sequence[Annotation[int]]


@dataclass(frozen=True)
class QueryEntitiesResult:
    """A class representing the return value of a Golem Base query."""

    entity_key: EntityKey
    storage_value: bytes


@dataclass(frozen=True)
class WatchLogsHandle:
    """
    Class returned by `GolemBaseClient.watch_logs`.

    Allows you to unsubscribe from the associated subscription.
    """

    _unsubscribe: Callable[[], Coroutine[Any, Any, None]]

    async def unsubscribe(self) -> None:
        """Unsubscribe from this subscription."""
        await self._unsubscribe()
