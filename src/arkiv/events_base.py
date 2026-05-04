"""Base class for event filters with shared logic."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from .contract import ENTITY_OPERATION_EVENT, EVENTS
from .types import (
    CreateEvent,
    DeleteEvent,
    EventType,
    ExtendEvent,
    UpdateEvent,
)

if TYPE_CHECKING:
    from web3._utils.filters import AsyncLogFilter, LogFilter
    from web3.contract import Contract
    from web3.contract.contract import ContractEvent

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
        self._poll_interval: float = 1.0  # seconds

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

        All event types map to the unified EntityOperation event.

        Raises:
            NotImplementedError: If event type is not supported
        """
        if self.event_type not in EVENTS:
            raise NotImplementedError(
                f"Event type {self.event_type} not yet implemented"
            )
        return ENTITY_OPERATION_EVENT

    def _get_op_type(self) -> int:
        """Return the EntityRegistry operation type constant for this event type."""
        return EVENTS[self.event_type]

    def _create_filter(self) -> LogFilter | AsyncLogFilter:
        """
        Create a Web3 contract event filter for HTTP polling.

        Filters by contract address and operationType so only the relevant
        operation variant of EntityOperation is received.
        """
        contract_event: ContractEvent = self.contract.events[ENTITY_OPERATION_EVENT]
        op_type = self._get_op_type()

        filter: LogFilter | AsyncLogFilter = contract_event.create_filter(
            from_block=self.from_block,
            address=self.contract.address,
            argument_filters={"operationType": op_type},
        )

        logger.info(
            f"Created filter for op_type={op_type} from block {self.from_block} "
            f"at address {self.contract.address}: {filter}"
        )
        return filter

    # Abstract methods that subclasses must implement
    @abstractmethod
    def start(self) -> Any:
        """
        Start monitoring for events.

        Subclasses implement this as either:
        - Sync method that starts a polling thread (EventFilter) -> None
        - Async method that starts an asyncio task (AsyncEventFilter) -> Awaitable[None]
        """
        ...

    @abstractmethod
    def stop(self) -> Any:
        """
        Stop monitoring for events.

        Subclasses implement this as either:
        - Sync method that stops the polling thread (EventFilter) -> None
        - Async method that cancels the asyncio task (AsyncEventFilter) -> Awaitable[None]
        """
        ...

    @abstractmethod
    def uninstall(self) -> Any:
        """
        Uninstall the filter and cleanup resources.

        Subclasses implement this as either:
        - Sync method that cleans up thread and filter (EventFilter) -> None
        - Async method that cleans up task and filter (AsyncEventFilter) -> Awaitable[None]
        """
        ...
