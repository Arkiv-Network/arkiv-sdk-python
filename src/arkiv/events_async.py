"""Async event filtering and monitoring for Arkiv entities.

This module provides async event watching functionality for Arkiv smart contract events.
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

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from web3._utils.filters import LogFilter
from web3.contract import Contract
from web3.types import LogReceipt

from arkiv.utils import get_tx_hash, to_event

from .events_base import EventFilterBase
from .types import (
    AsyncChangeOwnerCallback,
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
    | AsyncChangeOwnerCallback
)


class AsyncEventFilter(EventFilterBase[AsyncCallback]):
    """
    Handle for watching entity events using async HTTP polling.

    Uses direct log polling via eth_getLogs for maximum compatibility.
    This approach works with RPC providers that don't support eth_newFilter.
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

        # Track last processed block for log polling
        self._last_block: int | None = None

        # Try filter-based approach first (fallback to log polling if it fails)
        self._use_filter = True

    async def _create_filter(self) -> Any:  # type: ignore[override]
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
        return await contract_event.create_filter(
            from_block=self.from_block,
            address=self.contract.address,
        )

    async def start(self) -> None:
        """
        Start async HTTP polling for events.
        """
        if self._running:
            logger.warning(f"Filter for {self.event_type} is already running")
            return

        logger.info(f"Starting async event filter for {self.event_type}")

        # Try to create a Web3 filter first (works with most local nodes)
        # If it fails (403 Forbidden from Kaolin), we'll use log polling instead
        try:
            self._filter = await self._create_filter()
            self._use_filter = True
            logger.info(f"Using filter-based polling for {self.event_type}")
        except Exception as e:
            logger.warning(f"Filter creation failed ({e}), falling back to log polling")
            self._use_filter = False
            # Initialize last_block for log polling
            if self.from_block == "latest":
                self._last_block = await self.contract.w3.eth.block_number  # type: ignore[misc]
            else:
                self._last_block = int(self.from_block) - 1

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
                if self._use_filter:
                    # Filter-based approach (works with local nodes)
                    if self._filter:
                        logs: list[LogReceipt] = await self._filter.get_new_entries()  # type: ignore[misc]
                        for log in logs:
                            try:
                                await self._process_log(log)
                            except Exception as e:
                                logger.error(
                                    f"Error processing event: {e}", exc_info=True
                                )
                else:
                    # Log polling approach (works with Kaolin and other restricted RPC providers)
                    await self._poll_logs()

                # Async sleep before next poll
                await asyncio.sleep(self._poll_interval)

            except asyncio.CancelledError:
                logger.debug(f"Async poll loop cancelled for {self.event_type}")
                break
            except Exception as e:
                logger.error(f"Error in async poll loop: {e}", exc_info=True)
                await asyncio.sleep(self._poll_interval)

        logger.debug(f"Async poll loop ended for {self.event_type}")

    async def _poll_logs(self) -> None:
        """
        Poll for logs using eth_getLogs (async version).

        This is a fallback method for RPC providers that don't support eth_newFilter.
        """
        try:
            current_block = await self.contract.w3.eth.block_number  # type: ignore[misc]

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
            logs = await contract_event.get_logs(
                from_block=from_block,
                to_block=current_block,
            )

            # Process each log
            for log in logs:
                try:
                    await self._process_log(log)
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

    async def _process_log(self, log: LogReceipt) -> None:
        """
        Process a single event and trigger async callback.

        Only processes logs from the contract address we're monitoring.
        Logs from other contracts are silently skipped.
        """
        try:
            # Defensive check: Only process logs from our contract
            log_address = log.get("address")
            if log_address and log_address.lower() != self.contract.address.lower():
                logger.debug(
                    f"Skipping log from different contract: {log_address} "
                    f"(expected {self.contract.address})"
                )
                return

            # to_event handles both raw logs and already-processed EventData
            event = to_event(self.contract, log)
            tx_hash = get_tx_hash(log)

            logger.info(f"Starting callback for hash: {tx_hash} and event: {event}")

            await self.callback(event, tx_hash)  # type: ignore[arg-type]

        except Exception as e:
            logger.error(f"Error in async callback: {e}", exc_info=True)
