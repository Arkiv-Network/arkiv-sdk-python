"""Base class for event filters with shared logic."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from eth_typing import HexStr
from web3.types import EventData

from .contract import EVENTS
from .types import (
    CreateEvent,
    DeleteEvent,
    EventType,
    ExtendEvent,
    TxHash,
    UpdateEvent,
)
from .utils import to_entity_key

if TYPE_CHECKING:
    from web3.contract import Contract

logger = logging.getLogger(__name__)

# Type variable for callback types
# This allows subclasses to specify their own callback type (sync or async)
CallbackT = TypeVar("CallbackT")

# Union type for all event objects
EventObject = CreateEvent | UpdateEvent | ExtendEvent | DeleteEvent


class EventFilterBase(ABC, Generic[CallbackT]):
    """
    Abstract base class for event filters.

    Provides shared logic for parsing events and extracting data.
    Subclasses implement sync or async execution strategies.

    Type Parameters:
        CallbackT: The callback type (sync callbacks for EventFilter,
                   async callbacks for AsyncEventFilter)
    """

    def __init__(
        self,
        contract: Contract,
        event_type: EventType,
        callback: CallbackT,
        from_block: str | int = "latest",
        auto_start: bool = True,
    ) -> None:
        """
        Initialize event filter base.

        Args:
            contract: Web3 contract instance
            event_type: Type of event to watch ("created", "updated", "extended", "deleted")
            callback: Callback function (sync or async depending on subclass)
            from_block: Starting block for the filter ("latest" or block number)
            auto_start: If True, starts monitoring immediately (handled by subclass)
        """
        self.contract: Contract = contract
        self.event_type: EventType = event_type
        self.callback: CallbackT = callback
        self.from_block: str | int = from_block
        self._running: bool = False
        self._poll_interval: float = 2.0  # seconds

    @property
    def is_running(self) -> bool:
        """
        Check if the filter is currently running.

        Returns:
            True if the filter's monitoring is active, False otherwise
        """
        return self._running

    def _get_contract_event_name(self) -> str:
        """
        Get the Web3 contract event name for this event type.

        Returns:
            Contract event name (e.g., "GolemBaseStorageEntityCreated")

        Raises:
            NotImplementedError: If event type is not supported
        """
        if self.event_type not in EVENTS:
            raise NotImplementedError(
                f"Event type {self.event_type} not yet implemented"
            )
        return EVENTS[self.event_type]

    def _extract_tx_hash(self, event_data: EventData) -> TxHash:
        """
        Extract and normalize transaction hash from event data.

        Args:
            event_data: Event data from Web3 filter

        Returns:
            Transaction hash with 0x prefix
        """
        tx_hash_hex = event_data["transactionHash"].hex()
        if not tx_hash_hex.startswith("0x"):
            tx_hash_hex = f"0x{tx_hash_hex}"
        return TxHash(HexStr(tx_hash_hex))

    def _parse_event_data(self, event_data: EventData) -> tuple[EventObject, TxHash]:
        """
        Parse event data and create appropriate event object.

        This method contains the shared logic for parsing events from Web3.
        It does NOT trigger the callback - that's done by subclasses to allow
        for sync vs async callback invocation.

        Args:
            event_data: Event data from Web3 filter

        Returns:
            Tuple of (event_object, tx_hash)

        Raises:
            ValueError: If event_type is unknown
        """
        logger.info(f"Parsing event: {event_data}")

        # Extract common data
        entity_key = to_entity_key(event_data["args"]["entityKey"])
        tx_hash = self._extract_tx_hash(event_data)

        # Create event object based on type
        event: EventObject
        if self.event_type == "created":
            event = CreateEvent(
                entity_key=entity_key,
                expiration_block=event_data["args"]["expirationBlock"],
            )
        elif self.event_type == "updated":
            event = UpdateEvent(
                entity_key=entity_key,
                expiration_block=event_data["args"]["expirationBlock"],
            )
        elif self.event_type == "extended":
            event = ExtendEvent(
                entity_key=entity_key,
                old_expiration_block=event_data["args"]["oldExpirationBlock"],
                new_expiration_block=event_data["args"]["newExpirationBlock"],
            )
        elif self.event_type == "deleted":
            event = DeleteEvent(entity_key=entity_key)
        else:
            raise ValueError(f"Unknown event type: {self.event_type}")

        return event, tx_hash

    # Abstract methods that subclasses must implement
    @abstractmethod
    def start(self) -> None:
        """
        Start monitoring for events.

        Subclasses implement this as either:
        - Sync method that starts a polling thread (EventFilter)
        - Async method that starts an asyncio task (AsyncEventFilter)
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """
        Stop monitoring for events.

        Subclasses implement this as either:
        - Sync method that stops the polling thread (EventFilter)
        - Async method that cancels the asyncio task (AsyncEventFilter)
        """
        ...

    @abstractmethod
    def uninstall(self) -> None:
        """
        Uninstall the filter and cleanup resources.

        Subclasses implement this as either:
        - Sync method that cleans up thread and filter (EventFilter)
        - Async method that cleans up task and filter (AsyncEventFilter)
        """
        ...
