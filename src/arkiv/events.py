"""Event filtering and monitoring for Arkiv entities."""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, cast

from web3._utils.filters import LogFilter
from web3.contract import Contract
from web3.contract.contract import ContractEvent
from web3.types import EventData, LogReceipt

from .events_base import EventFilterBase
from .types import (
    CreateCallback,
    DeleteCallback,
    EventType,
    ExtendCallback,
    UpdateCallback,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Union of all sync callback types
SyncCallback = CreateCallback | UpdateCallback | ExtendCallback | DeleteCallback


class EventFilter(EventFilterBase[SyncCallback]):
    """
    Handle for watching entity events using HTTP polling.

    Uses polling-based filter with get_new_entries() for event monitoring.
    WebSocket providers are not supported by the sync Arkiv client.

    Inherits shared event parsing logic from EventFilterBase.
    """

    def __init__(
        self,
        contract: Contract,
        event_type: EventType,
        callback: SyncCallback,
        from_block: str | int = "latest",
        auto_start: bool = True,
    ) -> None:
        """
        Initialize event filter for HTTP polling.

        Args:
            contract: Web3 contract instance
            event_type: Type of event to watch
            callback: Callback function for the event (sync)
            from_block: Starting block for the filter
            auto_start: If True, starts polling immediately
        """
        # Initialize base class (but don't auto-start yet)
        super().__init__(contract, event_type, callback, from_block, auto_start=False)

        # Sync-specific state for HTTP polling
        self._thread: threading.Thread | None = None
        self._filter: LogFilter | None = None

        if auto_start:
            self.start()

    def start(self) -> None:
        """
        Start HTTP polling for events.
        """
        if self._running:
            logger.warning(f"Filter for {self.event_type} is already running")
            return

        logger.info(f"Starting event filter for {self.event_type}")

        # Create the Web3 filter using base class helper
        event_name = self._get_contract_event_name()
        contract_event: ContractEvent = self.contract.events[event_name]
        self._filter = contract_event.create_filter(from_block=self.from_block)

        # Start polling thread
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

        logger.info(f"Event filter for {self.event_type} started")

    def stop(self) -> None:
        """
        Stop polling for events.
        """
        if not self._running:
            logger.warning(f"Filter for {self.event_type} is not running")
            return

        logger.info(f"Stopping event filter for {self.event_type}")
        self._running = False

        # Wait for thread to finish
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

        logger.info(f"Event filter for {self.event_type} stopped")

    def uninstall(self) -> None:
        """Uninstall the filter and cleanup resources."""
        logger.info(f"Uninstalling event filter for {self.event_type}")

        # Stop polling if running
        if self._running:
            self.stop()

        # Clear filter reference (Web3 filters don't have uninstall method)
        self._filter = None

        logger.info(f"Event filter for {self.event_type} uninstalled")

    def _poll_loop(self) -> None:
        """Background polling loop for HTTP provider events."""
        logger.debug(f"Poll loop started for {self.event_type}")

        while self._running:
            try:
                # Get new entries from filter
                if self._filter:
                    new_entries: list[LogReceipt] = self._filter.get_new_entries()

                    for entry in new_entries:
                        try:
                            # LogFilter from contract event has log_entry_formatter that
                            # converts LogReceipt to EventData, but type system shows LogReceipt
                            self._process_event(cast(EventData, entry))
                        except Exception as e:
                            logger.error(f"Error processing event: {e}", exc_info=True)

                # Sleep before next poll
                time.sleep(self._poll_interval)

            except Exception as e:
                logger.error(f"Error in poll loop: {e}", exc_info=True)
                time.sleep(self._poll_interval)

        logger.debug(f"Poll loop ended for {self.event_type}")

    def _process_event(self, event_data: EventData) -> None:
        """
        Process a single event and trigger sync callback.

        Args:
            event_data: Event data from Web3 filter
        """
        # Use base class to parse event data
        event, tx_hash = self._parse_event_data(event_data)

        # Trigger sync callback with error handling
        try:
            self.callback(event, tx_hash)  # type: ignore[arg-type]
        except Exception as e:
            logger.error(f"Error in callback: {e}", exc_info=True)
