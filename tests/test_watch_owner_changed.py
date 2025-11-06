"""Tests for entity owner transferred event watching functionality."""

import logging
import time
from threading import Event as ThreadEvent

import pytest

from arkiv.types import Attributes, ChangeOwnerEvent, TxHash

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("arkiv_client_http")
class TestWatchOwnerChanged:
    """Test suite for watch_owner_changed functionality."""

    def test_watch_owner_changed_basic(self, arkiv_client_http, account_2):
        """Test basic watch_owner_changed functionality."""
        # Setup: Create an entity first
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"test data",
            attributes=Attributes({"type": "test"}),
            btl=100,
        )

        # Get original owner
        entity_before = arkiv_client_http.arkiv.get_entity(entity_key)
        original_owner = entity_before.owner

        # Setup callback with threading event
        callback_triggered = ThreadEvent()
        received_events: list[tuple[ChangeOwnerEvent, TxHash]] = []

        def on_owner_changed(event: ChangeOwnerEvent, tx_hash: TxHash) -> None:
            """Callback for owner transferred events."""
            received_events.append((event, tx_hash))
            callback_triggered.set()

        # Start watching for owner transfer events
        event_filter = arkiv_client_http.arkiv.watch_owner_changed(
            on_owner_changed, from_block="latest"
        )

        try:
            # Transfer ownership - this should trigger the callback
            receipt = arkiv_client_http.arkiv.change_owner(
                entity_key=entity_key,
                new_owner=account_2.address,
            )

            # Wait for callback (with timeout)
            assert callback_triggered.wait(timeout=10.0), (
                "Callback was not triggered within timeout"
            )

            # Verify we received the event
            assert len(received_events) == 1
            event, event_tx_hash = received_events[0]
            logger.info(f"Received owner transferred event: {event}")

            # Verify event data
            assert event.key == entity_key
            assert event.old_owner_address == original_owner
            assert event.new_owner_address == account_2.address
            assert event_tx_hash == receipt.tx_hash

        finally:
            # Cleanup: stop and uninstall the filter
            event_filter.uninstall()

    def test_watch_owner_changed_multiple_events(self, arkiv_client_http, account_2):
        """Test watching multiple owner transfer events."""
        # Create 3 entities first
        entity_keys = []
        for i in range(3):
            entity_key, _ = arkiv_client_http.arkiv.create_entity(
                payload=f"entity {i}".encode(),
                btl=100,
            )
            entity_keys.append(entity_key)

        # Setup callback
        callback_triggered = ThreadEvent()
        received_events: list[tuple[ChangeOwnerEvent, TxHash]] = []

        def on_owner_changed(event: ChangeOwnerEvent, tx_hash: TxHash) -> None:
            """Callback for owner transferred events."""
            received_events.append((event, tx_hash))
            if len(received_events) == 3:
                callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_owner_changed(
            on_owner_changed, from_block="latest"
        )

        try:
            # Transfer ownership of all entities
            transfer_hashes = []
            for entity_key in entity_keys:
                tx_hash = arkiv_client_http.arkiv.change_owner(
                    entity_key=entity_key,
                    new_owner=account_2.address,
                )
                transfer_hashes.append(tx_hash)

            # Wait for all callbacks
            assert callback_triggered.wait(timeout=15.0), (
                "Not all callbacks were triggered within timeout"
            )

            # Verify we received all events
            assert len(received_events) == 3

            # Verify all entity keys match
            received_keys = {event.key for event, _ in received_events}
            expected_keys = set(entity_keys)
            assert received_keys == expected_keys

            # Verify all new owners are account_2
            for event, _ in received_events:
                assert event.new_owner_address == account_2.address

        finally:
            event_filter.uninstall()

    def test_watch_owner_changed_manual_start_stop(self, arkiv_client_http, account_2):
        """Test manual start/stop of event filter."""
        # Create an entity first
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"initial", btl=100
        )

        received_events: list[tuple[ChangeOwnerEvent, TxHash]] = []

        def on_owner_changed(event: ChangeOwnerEvent, tx_hash: TxHash) -> None:
            """Callback for owner transferred events."""
            received_events.append((event, tx_hash))

        # Create filter without auto-start
        event_filter = arkiv_client_http.arkiv.watch_owner_changed(
            on_owner_changed, from_block="latest", auto_start=False
        )

        try:
            # Filter should not be running
            assert not event_filter.is_running

            # Transfer ownership - should NOT trigger callback (filter not started)
            arkiv_client_http.arkiv.change_owner(
                entity_key=entity_key, new_owner=account_2.address
            )
            time.sleep(2)  # Wait a bit
            assert len(received_events) == 0

            # Now start the filter
            event_filter.start()
            assert event_filter.is_running

            # Create a new entity and transfer - SHOULD trigger callback
            entity_key2, _ = arkiv_client_http.arkiv.create_entity(
                payload=b"second entity", btl=100
            )
            arkiv_client_http.arkiv.change_owner(
                entity_key=entity_key2, new_owner=account_2.address
            )
            time.sleep(3)  # Wait for polling
            assert len(received_events) == 1

            # Stop the filter
            event_filter.stop()
            assert not event_filter.is_running

            # Transfer again - should NOT trigger callback
            entity_key3, _ = arkiv_client_http.arkiv.create_entity(
                payload=b"third entity", btl=100
            )
            count_after_stopping = len(received_events)
            arkiv_client_http.arkiv.change_owner(
                entity_key=entity_key3, new_owner=account_2.address
            )
            time.sleep(2)
            assert len(received_events) == count_after_stopping

        finally:
            event_filter.uninstall()

    def test_watch_owner_changed_from_block_latest(
        self, arkiv_client_http, account_1, account_2
    ):
        """Test that from_block='latest' only catches new ownership transfers."""
        # Create entity and transfer ownership BEFORE starting the watcher
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"from account_1 (initial)", btl=100
        )

        # Transfer ownership before starting the filter
        arkiv_client_http.arkiv.change_owner(
            entity_key=entity_key, new_owner=account_2.address
        )

        received_events: list[tuple[ChangeOwnerEvent, TxHash]] = []

        def on_owner_changed(event: ChangeOwnerEvent, tx_hash: TxHash) -> None:
            """Callback for owner transferred events."""
            received_events.append((event, tx_hash))

        # Start watching from 'latest'
        event_filter = arkiv_client_http.arkiv.watch_owner_changed(
            on_owner_changed, from_block="latest"
        )

        try:
            # Wait a bit for filter to initialize
            time.sleep(1)

            # The transfer before should NOT be in received_events
            assert len(received_events) == 0

            # Create new entity as account_1 (default account)
            entity_key2, _ = arkiv_client_http.arkiv.create_entity(
                payload=b"from account_1 (after)", btl=100
            )

            # Transfer the second entity (this should be captured)
            owner_change_receipt = arkiv_client_http.arkiv.change_owner(
                entity_key=entity_key2, new_owner=account_2.address
            )
            time.sleep(3)  # Wait for polling

            # The new transfer should be received
            logger.info(f"Received events: {received_events}")
            assert len(received_events) == 1
            received_event = received_events[0]
            changed_event = received_event[0]
            assert changed_event.key == entity_key2, "Entity key mismatch"
            assert changed_event.old_owner_address == account_1.address, (
                "Old owner mismatch"
            )
            assert changed_event.new_owner_address == account_2.address, (
                "New owner mismatch"
            )
            assert received_event[1] == owner_change_receipt.tx_hash, "Tx hash mismatch"

        finally:
            event_filter.uninstall()

    def test_watch_owner_changed_lifecycle_operations(
        self, arkiv_client_http, account_2
    ):
        """Test that only ownership transfers trigger callback, not create/update/delete."""
        # Create an entity first
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"initial data", btl=100
        )

        received_events: list[tuple[ChangeOwnerEvent, TxHash]] = []

        def on_owner_changed(event: ChangeOwnerEvent, tx_hash: TxHash) -> None:
            """Callback for owner transferred events."""
            received_events.append((event, tx_hash))

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_owner_changed(
            on_owner_changed, from_block="latest"
        )

        try:
            # Create happened before filter, so no callback
            time.sleep(1)
            assert len(received_events) == 0

            # Update the entity - should NOT trigger callback
            arkiv_client_http.arkiv.update_entity(
                entity_key=entity_key, payload=b"updated data", btl=100
            )
            time.sleep(3)  # Wait to ensure no callback
            assert len(received_events) == 0

            # Extend the entity - should NOT trigger callback
            arkiv_client_http.arkiv.extend_entity(
                entity_key=entity_key, number_of_blocks=50
            )
            time.sleep(3)  # Wait to ensure no callback
            assert len(received_events) == 0

            # Transfer ownership - SHOULD trigger callback
            receipt = arkiv_client_http.arkiv.change_owner(
                entity_key=entity_key, new_owner=account_2.address
            )
            time.sleep(3)  # Wait for callback
            assert len(received_events) == 1
            assert received_events[0][0].key == entity_key
            assert received_events[0][1] == receipt.tx_hash

            # Verify the event details
            event, tx_hash = received_events[0]
            assert event.new_owner_address == account_2.address
            assert tx_hash == receipt.tx_hash

        finally:
            event_filter.uninstall()

    def test_watch_owner_changed_chained_transfers(
        self, arkiv_client_http, account_1, account_2
    ):
        """Test watching multiple transfers of the same entity."""
        # Create entity as account_1 (default)
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"test entity", btl=100
        )

        callback_triggered = ThreadEvent()
        received_events: list[tuple[ChangeOwnerEvent, TxHash]] = []

        def on_owner_changed(event: ChangeOwnerEvent, tx_hash: TxHash) -> None:
            """Callback for owner transferred events."""
            received_events.append((event, tx_hash))
            if len(received_events) == 2:
                callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_owner_changed(
            on_owner_changed, from_block="latest"
        )

        try:
            # First transfer: account_1 -> account_2
            receipt1 = arkiv_client_http.arkiv.change_owner(
                entity_key=entity_key, new_owner=account_2.address
            )

            # Switch to account_2
            arkiv_client_http.accounts[account_2.name] = account_2
            arkiv_client_http.switch_to(account_2.name)

            # Second transfer: account_2 -> account_1
            receipt2 = arkiv_client_http.arkiv.change_owner(
                entity_key=entity_key, new_owner=account_1.address
            )

            # Wait for both callbacks
            assert callback_triggered.wait(timeout=15.0), (
                "Not all callbacks were triggered within timeout"
            )

            # Verify we received 2 events
            assert len(received_events) == 2

            # Match events by transaction hash (order may vary)
            events_by_tx = {tx_hash: event for event, tx_hash in received_events}

            # Verify first transfer
            assert receipt1.tx_hash in events_by_tx
            event1 = events_by_tx[receipt1.tx_hash]
            assert event1.key == entity_key
            assert event1.old_owner_address == account_1.address, (
                f"Expected old owner {account_1.address}, got {event1.old_owner_address}"
            )
            assert event1.new_owner_address == account_2.address, (
                f"Expected new owner {account_2.address}, got {event1.new_owner_address}"
            )

            # Verify second transfer
            assert receipt2.tx_hash in events_by_tx
            event2 = events_by_tx[receipt2.tx_hash]
            assert event2.key == entity_key
            assert event2.old_owner_address == account_2.address, (
                f"Expected old owner {account_2.address}, got {event2.old_owner_address}"
            )
            assert event2.new_owner_address == account_1.address, (
                f"Expected new owner {account_1.address}, got {event2.new_owner_address}"
            )

        finally:
            # Switch back to default account
            arkiv_client_http.switch_to(account_1.name)
            event_filter.uninstall()

    def test_watch_owner_changed_same_owner(self, arkiv_client_http):
        """Test that transferring to same owner still triggers event."""
        # Create entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(payload=b"test", btl=100)

        entity = arkiv_client_http.arkiv.get_entity(entity_key)
        original_owner = entity.owner

        callback_triggered = ThreadEvent()
        received_events: list[tuple[ChangeOwnerEvent, TxHash]] = []

        def on_owner_changed(event: ChangeOwnerEvent, tx_hash: TxHash) -> None:
            """Callback for owner transferred events."""
            received_events.append((event, tx_hash))
            callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_owner_changed(
            on_owner_changed, from_block="latest"
        )

        try:
            # Transfer to same owner
            receipt = arkiv_client_http.arkiv.change_owner(
                entity_key=entity_key, new_owner=original_owner
            )

            # Should still trigger callback
            assert callback_triggered.wait(timeout=10.0), (
                "Callback was not triggered for same-owner transfer"
            )

            assert len(received_events) == 1
            event, tx_hash = received_events[0]
            assert event.key == entity_key
            assert event.old_owner_address == original_owner
            assert event.new_owner_address == original_owner
            assert tx_hash == receipt.tx_hash

        finally:
            event_filter.uninstall()
