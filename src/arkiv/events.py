"""Event filtering and monitoring for Arkiv entities."""

from __future__ import annotations

import logging
import threading
import time
from typing import cast

from eth_typing import HexStr
from web3._utils.filters import LogFilter
from web3.contract import Contract
from web3.contract.contract import ContractEvent
from web3.types import EventData, LogReceipt

from .contract import EVENTS
from .types import (
    CreateCallback,
    CreateEvent,
    DeleteCallback,
    DeleteEvent,
    EventType,
    ExtendCallback,
    ExtendEvent,
    TxHash,
    UpdateCallback,
    UpdateEvent,
)
from .utils import to_entity_key

logger = logging.getLogger(__name__)


class EventFilter:
    """Handle for watching entity events."""

    def __init__(
        self,
        contract: Contract,
        event_type: EventType,
        callback: CreateCallback | UpdateCallback | ExtendCallback | DeleteCallback,
        from_block: str | int = "latest",
        auto_start: bool = True,
    ) -> None:
        """
        Initialize event filter.

        Args:
            contract: Web3 contract instance
            event_type: Type of event to watch
            callback: Callback function for the event
            from_block: Starting block for the filter
            auto_start: If True, starts polling immediately
        """
        self.contract: Contract = contract
        self.event_type: EventType = event_type
        self.callback: (
            CreateCallback | UpdateCallback | ExtendCallback | DeleteCallback
        ) = callback
        self.from_block: str | int = from_block

        # Internal state
        self._filter: LogFilter | None = None
        self._running: bool = False
        self._thread: threading.Thread | None = None
        self._poll_interval: float = 2.0  # seconds

        if auto_start:
            self.start()

    def start(self) -> None:
        """
        Start polling for events.
        """
        if self._running:
            logger.warning(f"Filter for {self.event_type} is already running")
            return

        logger.info(f"Starting event filter for {self.event_type}")

        # Create the Web3 filter
        contract_event: ContractEvent
        if self.event_type in EVENTS.keys():
            event_name = EVENTS[self.event_type]
            contract_event = self.contract.events[event_name]
            self._filter = contract_event.create_filter(from_block=self.from_block)
        else:
            raise NotImplementedError(
                f"Event type {self.event_type} not yet implemented"
            )

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

        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

        logger.info(f"Event filter for {self.event_type} stopped")

    @property
    def is_running(self) -> bool:
        """
        Check if the filter is currently running.

        Returns:
            True if the filter's polling loop is active, False otherwise
        """
        return self._running

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
        """Background polling loop for events."""
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
        Process a single event and trigger callback.

        Args:
            event_data: Event data from Web3 filter
        """
        logger.info(f"Processing event: {event_data}")

        # Extract common data
        entity_key = to_entity_key(event_data["args"]["entityKey"])
        tx_hash = self._extract_tx_hash(event_data)

        # Create event object and trigger callback based on type
        if self.event_type == "created":
            create_event = CreateEvent(
                entity_key=entity_key,
                expiration_block=event_data["args"]["expirationBlock"],
            )
            self._trigger_callback(
                cast(CreateCallback, self.callback), create_event, tx_hash
            )

        elif self.event_type == "updated":
            update_event = UpdateEvent(
                entity_key=entity_key,
                expiration_block=event_data["args"]["expirationBlock"],
            )
            self._trigger_callback(
                cast(UpdateCallback, self.callback), update_event, tx_hash
            )

        elif self.event_type == "extended":
            extend_event = ExtendEvent(
                entity_key=entity_key,
                old_expiration_block=event_data["args"]["oldExpirationBlock"],
                new_expiration_block=event_data["args"]["newExpirationBlock"],
            )
            self._trigger_callback(
                cast(ExtendCallback, self.callback), extend_event, tx_hash
            )

        elif self.event_type == "deleted":
            delete_event = DeleteEvent(entity_key=entity_key)
            self._trigger_callback(
                cast(DeleteCallback, self.callback), delete_event, tx_hash
            )

        else:
            logger.warning(f"Unknown event type: {self.event_type}")

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

    def _trigger_callback(
        self,
        callback: CreateCallback | UpdateCallback | ExtendCallback | DeleteCallback,
        event: CreateEvent | UpdateEvent | ExtendEvent | DeleteEvent,
        tx_hash: TxHash,
    ) -> None:
        """
        Trigger callback with error handling.

        Args:
            callback: Callback function to invoke
            event: Event object to pass to callback
            tx_hash: Transaction hash to pass to callback
        """
        try:
            callback(event, tx_hash)  # type: ignore[arg-type]
        except Exception as e:
            logger.error(f"Error in callback: {e}", exc_info=True)
