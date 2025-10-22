"""Async event filtering and monitoring for Arkiv entities."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, cast

from web3._utils.filters import LogFilter
from web3.contract import Contract
from web3.types import EventData, LogReceipt

from .events_base import EventFilterBase
from .types import (
    AsyncCreateCallback,
    AsyncDeleteCallback,
    AsyncExtendCallback,
    AsyncUpdateCallback,
    EventType,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Union of all async callback types
AsyncCallback = (
    AsyncCreateCallback
    | AsyncUpdateCallback
    | AsyncExtendCallback
    | AsyncDeleteCallback
)


class AsyncEventFilter(EventFilterBase[AsyncCallback]):
    """
    Handle for watching entity events using async HTTP polling.

    Uses async polling-based filter with get_new_entries() for event monitoring.
    WebSocket providers are not supported yet (future enhancement).

    Inherits shared event parsing logic from EventFilterBase.
    """

    def __init__(
        self,
        contract: Contract,
        event_type: EventType,
        callback: AsyncCallback,
        from_block: str | int = "latest",
    ) -> None:
        """
        Initialize async event filter for HTTP polling.

        Args:
            contract: Web3 contract instance
            event_type: Type of event to watch
            callback: Async callback function for the event
            from_block: Starting block for the filter

        Note:
            Unlike the sync EventFilter, AsyncEventFilter does not support auto_start
            since we cannot await in __init__. Caller must explicitly await start().
        """
        # Initialize base class (never auto-start since we need async context)
        super().__init__(contract, event_type, callback, from_block, auto_start=False)

        # Async-specific state for HTTP polling
        self._task: asyncio.Task[None] | None = None
        self._filter: LogFilter | None = None

    async def _create_filter(self) -> Any:
        """
        Create a Web3 contract event filter for async HTTP polling.

        Overrides the base class method to handle async create_filter calls.
        For async providers, contract_event.create_filter() returns a coroutine
        that must be awaited.

        Returns:
            LogFilter for async HTTP providers
        """
        event_name = self._get_contract_event_name()
        contract_event = self.contract.events[event_name]
        return await contract_event.create_filter(from_block=self.from_block)

    async def start(self) -> None:
        """
        Start async HTTP polling for events.
        """
        if self._running:
            logger.warning(f"Filter for {self.event_type} is already running")
            return

        logger.info(f"Starting async event filter for {self.event_type}")

        # Create the Web3 filter using async helper
        self._filter = await self._create_filter()

        # Start async polling task
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())

        logger.info(f"Async event filter for {self.event_type} started")

    async def stop(self) -> None:
        """
        Stop async polling for events.
        """
        if not self._running:
            logger.warning(f"Filter for {self.event_type} is not running")
            return

        logger.info(f"Stopping async event filter for {self.event_type}")
        self._running = False

        # Cancel and wait for task to finish
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info(f"Async event filter for {self.event_type} stopped")

    async def uninstall(self) -> None:
        """Uninstall the filter and cleanup resources."""
        logger.info(f"Uninstalling async event filter for {self.event_type}")

        # Stop polling if running
        if self._running:
            await self.stop()

        # Clear filter reference (Web3 filters don't have uninstall method)
        self._filter = None

        logger.info(f"Async event filter for {self.event_type} uninstalled")

    async def _poll_loop(self) -> None:
        """Background async polling loop for HTTP provider events."""
        logger.debug(f"Async poll loop started for {self.event_type}")

        while self._running:
            try:
                # Get new entries from filter
                if self._filter:
                    # For async providers, get_new_entries() returns a coroutine
                    # Type system doesn't reflect this, so we need to ignore the type error
                    new_entries: list[LogReceipt] = await self._filter.get_new_entries()  # type: ignore[misc]

                    for entry in new_entries:
                        try:
                            # LogFilter from contract event has log_entry_formatter that
                            # converts LogReceipt to EventData, but type system shows LogReceipt
                            await self._process_event(cast(EventData, entry))
                        except Exception as e:
                            logger.error(f"Error processing event: {e}", exc_info=True)

                # Async sleep before next poll
                await asyncio.sleep(self._poll_interval)

            except asyncio.CancelledError:
                logger.debug(f"Async poll loop cancelled for {self.event_type}")
                break
            except Exception as e:
                logger.error(f"Error in async poll loop: {e}", exc_info=True)
                await asyncio.sleep(self._poll_interval)

        logger.debug(f"Async poll loop ended for {self.event_type}")

    async def _process_event(self, event_data: EventData) -> None:
        """
        Process a single event and trigger async callback.

        Args:
            event_data: Event data from Web3 filter
        """
        # Use base class to parse event data
        event, tx_hash = self._parse_event_data(event_data)

        # Trigger async callback with error handling
        try:
            await self.callback(event, tx_hash)  # type: ignore[arg-type]
        except Exception as e:
            logger.error(f"Error in async callback: {e}", exc_info=True)
