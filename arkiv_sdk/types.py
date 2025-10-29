"""Arkiv SDK Types."""

import warnings
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
        """Return bytes encoded as a string."""
        return f"{type(self).__name__}({self.as_hex_string()})"

    @staticmethod
    def from_hex_string(hexstr: str) -> "GenericBytes":
        """Create a `GenericBytes` instance from a hexadecimal string."""
        assert hexstr.startswith("0x")
        assert len(hexstr) % 2 == 0

        return GenericBytes(bytes.fromhex(hexstr[2:]))


EntityKey = NewType("EntityKey", GenericBytes)
Address = NewType("Address", GenericBytes)


class ExpirationTime:
    """
    Helper class for creating expiration time values with conversion methods.

    Arkiv uses a block-based expiration system where each block is produced
    every 2 seconds. This class provides type-safe methods to convert various
    time units to block counts.

    Examples:
        >>> # Create from seconds (recommended)
        >>> exp1 = ExpirationTime.from_seconds(3600)  # 1 hour
        >>> print(exp1.blocks)  # 1800

        >>> # Create from hours
        >>> exp2 = ExpirationTime.from_hours(24)  # 1 day
        >>> print(exp2.blocks)  # 43200

        >>> # Create from days
        >>> exp3 = ExpirationTime.from_days(7)  # 1 week
        >>> print(exp3.blocks)  # 302400

        >>> # Create from blocks (legacy)
        >>> exp4 = ExpirationTime.from_blocks(1800)
        >>> print(exp4.to_seconds())  # 3600

    """

    # TODO: derive this from the chain using RPC
    BLOCK_TIME_SECONDS = 2
    """Block time in seconds (Arkiv produces blocks every 2 seconds)"""

    def __init__(self, blocks: int):
        """
        Initialize ExpirationTime with block count.

        Args:
            blocks: Number of blocks representing this expiration time

        Raises:
            ValueError: If blocks is not positive

        """
        if blocks <= 0:
            raise ValueError("Expiration time must be positive")
        self._blocks = int(blocks)

    @property
    def blocks(self) -> int:
        """Get the number of blocks."""
        return self._blocks

    @classmethod
    def from_seconds(cls, seconds: int | float) -> "ExpirationTime":
        """
        Create expiration time from seconds.

        Args:
            seconds: Duration in seconds

        Returns:
            ExpirationTime instance

        """
        return cls(int(seconds / cls.BLOCK_TIME_SECONDS))

    @classmethod
    def from_blocks(cls, blocks: int) -> "ExpirationTime":
        """
        Create expiration time from block count.

        Args:
            blocks: Number of blocks

        Returns:
            ExpirationTime instance

        """
        return cls(blocks)

    @classmethod
    def from_hours(cls, hours: int | float) -> "ExpirationTime":
        """
        Create expiration time from hours.

        Args:
            hours: Duration in hours

        Returns:
            ExpirationTime instance

        """
        return cls.from_seconds(hours * 3600)

    @classmethod
    def from_days(cls, days: int | float) -> "ExpirationTime":
        """
        Create expiration time from days.

        Args:
            days: Duration in days

        Returns:
            ExpirationTime instance

        """
        return cls.from_seconds(days * 86400)

    def to_seconds(self) -> int:
        """
        Convert expiration time to seconds.

        Returns:
            Duration in seconds

        """
        return self._blocks * self.BLOCK_TIME_SECONDS

    def __repr__(self) -> str:
        """Return string representation of ExpirationTime."""
        return f"ExpirationTime(blocks={self._blocks}, seconds={self.to_seconds()})"


def getBTL(duration: int | ExpirationTime | None, blocks: int | None) -> int:
    """Resolve the BTL given either a duration or a number of blocks."""
    if duration is not None:
        if isinstance(duration, int):
            # Treat as seconds and convert to blocks
            return ExpirationTime.from_seconds(duration).blocks
        # It's an ExpirationTime object
        return duration.blocks

    if blocks is not None:
        # Warn about deprecated BTL
        warnings.warn(
            "⚠️  BTL is deprecated and will be removed in a future version. "
            "Please use 'expires_in' instead. "
            "Example: expires_in=3600 (seconds) or "
            "expires_in=ExpirationTime.from_hours(1)",
            DeprecationWarning,
            stacklevel=3,
        )
        return blocks

    raise ValueError("Either 'expires_in' or 'btl' must be specified")


def resolve_expiration_blocks(
    expires_in: int | ExpirationTime | None,
    btl: int | None,
) -> int:
    """
    Resolve expiration time from either new API or legacy BTL.

    Priority: expires_in > btl

    Args:
        expires_in: Duration in seconds (int) or ExpirationTime object
        btl: Legacy block count (deprecated)

    Returns:
        Number of blocks

    Raises:
        ValueError: If neither expires_in nor btl is specified

    """
    return getBTL(expires_in, btl)


def resolve_extension_blocks(
    duration: int | ExpirationTime | None,
    number_of_blocks: int | None,
) -> int:
    """
    Resolve extension duration from either new API or legacy numberOfBlocks.

    Priority: duration > number_of_blocks

    Args:
        duration: Duration in seconds (int) or ExpirationTime object
        number_of_blocks: Legacy block count (deprecated)

    Returns:
        Number of blocks

    Raises:
        ValueError: If neither duration nor number_of_blocks is specified

    """
    return getBTL(duration, number_of_blocks)


# TODO: use new generic syntax once we can bump to python 3.12 or higher
V = TypeVar("V")


@dataclass(frozen=True)
class Annotation(Generic[V]):
    """Class to represent generic annotations."""

    key: str
    value: V

    # @override
    def __repr__(self) -> str:
        """Return annotation encoded as a string."""
        return f"{type(self).__name__}({self.key} -> {self.value})"


@dataclass(frozen=True)
class ArkivCreate:
    """
    Class to represent a create operation in Arkiv.

    Examples:
        >>> # New API - using seconds as int
        >>> create = ArkivCreate(
        ...     data=b"Hello",
        ...     string_annotations=[],
        ...     numeric_annotations=[],
        ...     expires_in=3600  # 1 hour in seconds
        ... )

        >>> # New API - using ExpirationTime
        >>> create = ArkivCreate(
        ...     data=b"Hello",
        ...     string_annotations=[],
        ...     numeric_annotations=[],
        ...     expires_in=ExpirationTime.from_hours(24)
        ... )

        >>> # Legacy API (deprecated but still works)
        >>> create = ArkivCreate(
        ...     data=b"Hello",
        ...     btl=1800,  # blocks
        ...     string_annotations=[],
        ...     numeric_annotations=[]
        ... )

    """

    data: bytes
    btl: int | None = None  # Deprecated: use expires_in instead
    string_annotations: Sequence[Annotation[str]] = ()
    numeric_annotations: Sequence[Annotation[int]] = ()
    # Preferred: seconds or ExpirationTime
    expires_in: int | ExpirationTime | None = None


@dataclass(frozen=True)
class ArkivUpdate:
    """
    Class to represent an update operation in Arkiv.

    Examples:
        >>> # New API - using seconds
        >>> update = ArkivUpdate(
        ...     entity_key=entity_key,
        ...     data=b"Updated",
        ...     string_annotations=[],
        ...     numeric_annotations=[],
        ...     expires_in=86400  # 1 day in seconds
        ... )

        >>> # New API - using ExpirationTime
        >>> update = ArkivUpdate(
        ...     entity_key=entity_key,
        ...     data=b"Updated",
        ...     string_annotations=[],
        ...     numeric_annotations=[],
        ...     expires_in=ExpirationTime.from_days(7)
        ... )

        >>> # Legacy API (deprecated)
        >>> update = ArkivUpdate(
        ...     entity_key=entity_key,
        ...     data=b"Updated",
        ...     btl=2000,  # blocks
        ...     string_annotations=[],
        ...     numeric_annotations=[]
        ... )

    """

    entity_key: EntityKey
    data: bytes
    btl: int | None = None  # Deprecated: use expires_in instead
    string_annotations: Sequence[Annotation[str]] = ()
    numeric_annotations: Sequence[Annotation[int]] = ()
    # Preferred: seconds or ExpirationTime
    expires_in: int | ExpirationTime | None = None


@dataclass(frozen=True)
class ArkivDelete:
    """Class to represent a delete operation in Arkiv."""

    entity_key: EntityKey


@dataclass(frozen=True)
class ArkivExtend:
    """
    Class to represent an extend operation in Arkiv.

    Examples:
        >>> # New API - using seconds
        >>> extend = ArkivExtend(
        ...     entity_key=entity_key,
        ...     duration=86400  # 1 day in seconds
        ... )

        >>> # New API - using ExpirationTime
        >>> extend = ArkivExtend(
        ...     entity_key=entity_key,
        ...     duration=ExpirationTime.from_hours(48)
        ... )

        >>> # Legacy API (deprecated)
        >>> extend = ArkivExtend(
        ...     entity_key=entity_key,
        ...     number_of_blocks=500  # blocks
        ... )

    """

    entity_key: EntityKey
    number_of_blocks: int | None = None  # Deprecated: use duration instead
    # Preferred: seconds or ExpirationTime
    duration: int | ExpirationTime | None = None


@dataclass(frozen=True)
class ArkivTransaction:
    """
    Class to represent a transaction in Arkiv.

    A transaction consist of one or more
    `ArkivCreate`,
    `ArkivUpdate`,
    `ArkivDelete` and
    `ArkivExtend`
    operations.
    """

    def __init__(
        self,
        *,
        creates: Sequence[ArkivCreate] | None = None,
        updates: Sequence[ArkivUpdate] | None = None,
        deletes: Sequence[ArkivDelete] | None = None,
        extensions: Sequence[ArkivExtend] | None = None,
        gas: int | None = None,
        maxFeePerGas: Wei | None = None,
        maxPriorityFeePerGas: Wei | None = None,
    ):
        """Initialise the ArkivTransaction instance."""
        object.__setattr__(self, "creates", creates or [])
        object.__setattr__(self, "updates", updates or [])
        object.__setattr__(self, "deletes", deletes or [])
        object.__setattr__(self, "extensions", extensions or [])
        object.__setattr__(self, "gas", gas)
        object.__setattr__(self, "maxFeePerGas", maxFeePerGas)
        object.__setattr__(self, "maxPriorityFeePerGas", maxPriorityFeePerGas)

    creates: Sequence[ArkivCreate]
    updates: Sequence[ArkivUpdate]
    deletes: Sequence[ArkivDelete]
    extensions: Sequence[ArkivExtend]
    gas: int | None
    maxFeePerGas: Wei | None
    maxPriorityFeePerGas: Wei | None


@dataclass(frozen=True)
class CreateEntityReturnType:
    """The return type of a Arkiv create operation."""

    expiration_block: int
    entity_key: EntityKey


@dataclass(frozen=True)
class UpdateEntityReturnType:
    """The return type of a Arkiv update operation."""

    expiration_block: int
    entity_key: EntityKey


@dataclass(frozen=True)
class ExtendEntityReturnType:
    """The return type of a Arkiv extend operation."""

    old_expiration_block: int
    new_expiration_block: int
    entity_key: EntityKey


@dataclass(frozen=True)
class ArkivTransactionReceipt:
    """The return type of a Arkiv transaction."""

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
    """A class representing the return value of a Arkiv query."""

    entity_key: EntityKey
    storage_value: bytes


@dataclass(frozen=True)
class WatchLogsHandle:
    """
    Class returned by `ArkivClient.watch_logs`.

    Allows you to unsubscribe from the associated subscription.
    """

    _unsubscribe: Callable[[], Coroutine[Any, Any, None]]

    async def unsubscribe(self) -> None:
        """Unsubscribe from this subscription."""
        await self._unsubscribe()
