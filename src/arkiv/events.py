"""Event filtering and monitoring for Arkiv entities.

This module provides event watching functionality for Arkiv smart contract events.
It supports two polling strategies:

1. Filter-based polling (eth_newFilter + eth_getFilterChanges):
   - More efficient, uses persistent filters on the node
   - Works with local nodes and some RPC providers
   - Automatically tried first

2. Log polling (eth_getLogs):
   - Maximum compatibility, works with all RPC providers
   - Used as fallback when filter creation fails (e.g., Kaolin testnet blocks eth_newFilter)
   - Polls for new logs on each interval

The implementation automatically detects which method to use based on provider capabilities.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

from web3._utils.filters import LogFilter
from web3.contract import Contract
from web3.types import LogReceipt

from arkiv.utils import get_tx_hash, to_event

from .events_base import EventFilterBase
from .types import (
    ChangeOwnerCallback,
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
SyncCallback = (
    CreateCallback
    | UpdateCallback
    | ExtendCallback
    | DeleteCallback
    | ChangeOwnerCallback
)


class EventFilter(EventFilterBase[SyncCallback]):
    """
    Handle for watching entity events using HTTP polling.

    Uses direct log polling via eth_getLogs for maximum compatibility.
    This approach works with RPC providers that don't support eth_newFilter.
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

        # Track last processed block for log polling
        self._last_block: int | None = None

        # Try filter-based approach first (fallback to log polling if it fails)
        self._use_filter = True

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

        # Try to create a Web3 filter first (works with most local nodes)
        # If it fails (403 Forbidden from Kaolin), we'll use log polling instead
        try:
            filter_result = self._create_filter()
            assert isinstance(filter_result, LogFilter), (
                "Expected LogFilter for sync client"
            )
            self._filter = filter_result
            self._use_filter = True
            logger.info(f"Using filter-based polling for {self.event_type}")
        except Exception as e:
            logger.warning(f"Filter creation failed ({e}), falling back to log polling")
            self._use_filter = False
            # Initialize last_block for log polling
            if self.from_block == "latest":
                self._last_block = self.contract.w3.eth.block_number
            else:
                self._last_block = int(self.from_block) - 1

        # Start polling thread
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

        logger.info(f"Event filter for '{self.event_type}' started")

    def stop(self) -> None:
        """
        Stop polling for events.
        """
        if not self._running:
            logger.warning(f"Filter for '{self.event_type}' is not running")
            return

        logger.info(f"Stopping event filter for '{self.event_type}'")
        self._running = False

        # Wait for thread to finish
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

        logger.info(f"Event filter for '{self.event_type}' stopped")

    def uninstall(self) -> None:
        """Uninstall the filter and cleanup resources."""
        logger.info(f"Uninstalling event filter for '{self.event_type}'")

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
                if self._use_filter:
                    # Filter-based approach (works with local nodes)
                    if self._filter:
                        logs: list[LogReceipt] = self._filter.get_new_entries()
                        for log in logs:
                            try:
                                self._process_log(log)
                            except Exception as e:
                                logger.error(
                                    f"Error processing event: {e}", exc_info=True
                                )
                else:
                    # Log polling approach (works with Kaolin and other restricted RPC providers)
                    self._poll_logs()

                # Sleep before next poll
                time.sleep(self._poll_interval)

            except Exception as e:
                logger.error(f"Error in poll loop: {e}", exc_info=True)
                time.sleep(self._poll_interval)

        logger.debug(f"Poll loop ended for {self.event_type}")

    def _poll_logs(self) -> None:
        """
        Poll for logs using eth_getLogs.

        This is a fallback method for RPC providers that don't support eth_newFilter.
        """
        try:
            current_block = self.contract.w3.eth.block_number

            # Only query if there are new blocks
            if self._last_block is not None and current_block <= self._last_block:
                return

            # Get the contract event
            event_name = self._get_contract_event_name()
            contract_event = self.contract.events[event_name]

            # Calculate from_block for this poll
            from_block = (
                (self._last_block + 1)
                if self._last_block is not None
                else current_block
            )

            # Get logs for new blocks
            logs = contract_event.get_logs(
                from_block=from_block,
                to_block=current_block,
            )

            # Process each log
            for log in logs:
                try:
                    self._process_log(log)
                except Exception as e:
                    logger.error(f"Error processing event: {e}", exc_info=True)

            # Update last processed block
            self._last_block = current_block

            if logs:
                logger.debug(
                    f"Processed {len(logs)} {self.event_type} events "
                    f"from blocks {from_block} to {current_block}"
                )

        except Exception as e:
            logger.error(f"Error polling logs: {e}", exc_info=True)

    def _process_log(self, log: LogReceipt) -> None:
        """
        Process a single log receipt and trigger sync callback.

        Only processes logs from the contract address we're monitoring.
        Logs from other contracts are silently skipped.
        """
        try:
            # to_event handles both raw logs and already-processed EventData
            event = to_event(self.contract, log)
            tx_hash = get_tx_hash(log)

            logger.info(f"Starting callback for hash: {tx_hash} and event: {event}")
            self.callback(event, tx_hash)  # type: ignore[arg-type]

        except Exception as e:
            logger.error(f"Error in callback: {e}", exc_info=True)
