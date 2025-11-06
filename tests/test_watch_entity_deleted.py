"""Tests for entity deletion event watching functionality."""

import time
from threading import Event as ThreadEvent

import pytest

from arkiv.types import DeleteEvent, DeleteOp, TxHash

from .utils import bulk_delete_entities


@pytest.mark.usefixtures("arkiv_client_http")
class TestWatchEntityDeleted:
    """Test suite for watch_entity_deleted functionality."""

    def test_watch_entity_deleted_basic(self, arkiv_client_http):
        """Test basic watch_entity_deleted functionality."""
        # Setup: Create an entity first
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"test data",
            btl=100,
        )

        # Setup callback with threading event
        callback_triggered = ThreadEvent()
        received_events: list[tuple[DeleteEvent, TxHash]] = []

        def on_delete(event: DeleteEvent, tx_hash: TxHash) -> None:
            """Callback for delete events."""
            received_events.append((event, tx_hash))
            # Only trigger event for OUR entity (prevents cross-test pollution)
            if event.key == entity_key:
                callback_triggered.set()

        # Start watching for delete events
        event_filter = arkiv_client_http.arkiv.watch_entity_deleted(
            on_delete, from_block="latest"
        )

        try:
            # Delete the entity - this should trigger the callback
            receipt = arkiv_client_http.arkiv.delete_entity(entity_key=entity_key)

            # Wait for callback (with timeout)
            assert callback_triggered.wait(timeout=10.0), (
                "Callback was not triggered within timeout"
            )

            # Filter to only our entity's events (robust against concurrent test events)
            our_events = [
                (event, tx_hash)
                for event, tx_hash in received_events
                if event.key == entity_key
            ]

            # Verify we received exactly one event for our entity
            assert len(our_events) == 1, (
                f"Expected 1 event for our entity, got {len(our_events)}. "
                f"Total events received: {len(received_events)}"
            )
            event, event_tx_hash = our_events[0]

            # Verify event data
            assert event.key == entity_key
            assert event_tx_hash == receipt.tx_hash

        finally:
            # Cleanup: stop and uninstall the filter
            event_filter.uninstall()

    def test_watch_entity_deleted_multiple_events(self, arkiv_client_http):
        """Test watching multiple deletion events."""
        # Create 3 entities first
        entity_keys = []
        for i in range(3):
            entity_key, _ = arkiv_client_http.arkiv.create_entity(
                payload=f"data {i}".encode(),
                btl=100,
            )
            entity_keys.append(entity_key)

        # Setup callback
        callback_triggered = ThreadEvent()
        received_events: list[tuple[DeleteEvent, TxHash]] = []

        def on_delete(event: DeleteEvent, tx_hash: TxHash) -> None:
            """Callback for delete events."""
            # Only trigger event for OUR entity (prevents cross-test pollution)
            if event.key in entity_keys:
                received_events.append((event, tx_hash))
                if len(received_events) == 3:
                    callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_deleted(
            on_delete, from_block="latest"
        )

        try:
            # Delete all entities
            delete_hashes = []
            for entity_key in entity_keys:
                tx_hash = arkiv_client_http.arkiv.delete_entity(entity_key=entity_key)
                delete_hashes.append(tx_hash)

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

        finally:
            event_filter.uninstall()

    def test_watch_entity_deleted_manual_start_stop(self, arkiv_client_http):
        """Test manual start/stop of event filter."""
        # Create 3 entities first
        entity_keys = []
        for i in range(3):
            entity_key, _ = arkiv_client_http.arkiv.create_entity(
                payload=f"data {i}".encode(),
                btl=100,
            )
            entity_keys.append(entity_key)

        # Setup callback
        callback_triggered = ThreadEvent()
        received_events: list[tuple[DeleteEvent, TxHash]] = []

        def on_delete(event: DeleteEvent, tx_hash: TxHash) -> None:
            """Callback for delete events."""
            # Only trigger event for OUR entity (prevents cross-test pollution)
            if event.key in entity_keys:
                received_events.append((event, tx_hash))
                if len(received_events) == 3:
                    callback_triggered.set()

        # Create filter without auto-start
        event_filter = arkiv_client_http.arkiv.watch_entity_deleted(
            on_delete, from_block="latest", auto_start=False
        )

        try:
            # Filter should not be running
            assert not event_filter.is_running

            # Delete entity - should NOT trigger callback (filter not started)
            arkiv_client_http.arkiv.delete_entity(entity_key=entity_keys[0])
            time.sleep(5)  # Wait a bit
            assert len(received_events) == 0

            # Now start the filter
            event_filter.start()
            assert event_filter.is_running

            # Delete again - SHOULD trigger callback
            arkiv_client_http.arkiv.delete_entity(entity_key=entity_keys[1])
            time.sleep(5)  # Wait for polling
            assert len(received_events) == 1
            assert received_events[0][0].key == entity_keys[1]

            # Stop the filter
            event_filter.stop()
            assert not event_filter.is_running

            # Delete again - should NOT trigger callback
            count_after_stopping = len(received_events)
            arkiv_client_http.arkiv.delete_entity(entity_key=entity_keys[2])
            time.sleep(5)
            assert len(received_events) == count_after_stopping

        finally:
            event_filter.uninstall()

    def test_watch_entity_deleted_bulk_delete(self, arkiv_client_http):
        """Test that bulk delete triggers callback for each entity."""
        # Create 3 entities first
        entity_keys = []
        for i in range(3):
            entity_key, _ = arkiv_client_http.arkiv.create_entity(
                payload=f"initial {i}".encode(), btl=100
            )
            entity_keys.append(entity_key)

        # Setup callback
        callback_triggered = ThreadEvent()
        received_events: list[tuple[DeleteEvent, TxHash]] = []

        def on_delete(event: DeleteEvent, tx_hash: TxHash) -> None:
            """Callback for delete events."""
            # Only trigger event for OUR entity (prevents cross-test pollution)
            if event.key in entity_keys:
                received_events.append((event, tx_hash))
                if len(received_events) == 3:
                    callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_deleted(
            on_delete, from_block="latest"
        )

        try:
            # Delete 3 entities in a single bulk transaction
            delete_ops = [
                DeleteOp(key=entity_keys[0]),
                DeleteOp(key=entity_keys[1]),
                DeleteOp(key=entity_keys[2]),
            ]
            receipt = bulk_delete_entities(
                arkiv_client_http, delete_ops, label="test_bulk_delete"
            )

            # Wait for all callbacks
            assert callback_triggered.wait(timeout=5.0), (
                "Not all callbacks were triggered within timeout"
            )

            # Verify we received 3 events (one for each entity)
            assert len(received_events) == 3

            # Verify all entity keys match
            received_keys = {event.key for event, _ in received_events}
            expected_keys = set(entity_keys)
            assert received_keys == expected_keys

            # Verify all events share the same transaction hash
            tx_hashes = {event_tx_hash for _, event_tx_hash in received_events}
            assert len(tx_hashes) == 1, (
                "All events should share the same transaction hash"
            )
            assert tx_hashes.pop() == receipt.tx_hash

        finally:
            event_filter.uninstall()

    def test_watch_entity_deleted_lifecycle_operations(self, arkiv_client_http):
        """Test that only deletions trigger callback, not create/update/extend."""
        # Create an entity first
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"initial data", btl=100
        )

        received_events: list[tuple[DeleteEvent, TxHash]] = []

        def on_delete(event: DeleteEvent, tx_hash: TxHash) -> None:
            """Callback for delete events."""
            # Only trigger event for OUR entity (prevents cross-test pollution)
            if event.key == entity_key:
                received_events.append((event, tx_hash))

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_deleted(
            on_delete, from_block="latest"
        )

        try:
            # Create happened before filter, so no callback
            time.sleep(1)
            assert len(received_events) == 0

            # Update the entity - should NOT trigger callback
            _ = arkiv_client_http.arkiv.update_entity(
                entity_key=entity_key, payload=b"updated data", btl=100
            )
            time.sleep(3)  # Wait to ensure no callback
            assert len(received_events) == 0

            # Extend the entity - should NOT trigger callback
            _ = arkiv_client_http.arkiv.extend_entity(
                entity_key=entity_key, number_of_blocks=50
            )
            time.sleep(3)  # Wait to ensure no callback
            assert len(received_events) == 0

            # Delete the entity - SHOULD trigger callback
            receipt = arkiv_client_http.arkiv.delete_entity(entity_key=entity_key)
            time.sleep(3)  # Wait for callback
            assert len(received_events) == 1
            assert received_events[0][0].key == entity_key
            assert received_events[0][1] == receipt.tx_hash

            # Verify the single event is the delete event
            event, tx_hash = received_events[0]
            assert event.key == entity_key
            assert tx_hash == receipt.tx_hash

        finally:
            event_filter.uninstall()

    def test_watch_entity_deleted_entity_not_exist_after_delete(
        self, arkiv_client_http
    ):
        """Test that deleted entities no longer exist in storage."""
        # Create entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"test data", btl=100
        )

        # Verify entity exists
        assert arkiv_client_http.arkiv.entity_exists(entity_key)

        callback_triggered = ThreadEvent()
        received_events: list[tuple[DeleteEvent, TxHash]] = []

        def on_delete(event: DeleteEvent, tx_hash: TxHash) -> None:
            """Callback for delete events."""
            # Only set event if it's OUR entity (filter isolation from other tests)
            if event.key == entity_key:
                received_events.append((event, tx_hash))
                callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_deleted(
            on_delete, from_block="latest"
        )

        try:
            # Delete the entity
            arkiv_client_http.arkiv.delete_entity(entity_key=entity_key)

            # Wait for callback
            assert callback_triggered.wait(timeout=5.0), (
                "Callback was not triggered within timeout"
            )

            # Verify we received at least our event (may include events from other tests in same block)
            our_events = [
                (event, tx_hash)
                for event, tx_hash in received_events
                if event.key == entity_key
            ]
            assert len(our_events) == 1, (
                f"Expected 1 event for our entity, got {len(our_events)}. "
                f"Total events: {len(received_events)} (may include other tests in same block)"
            )
            assert our_events[0][0].key == entity_key

            # Verify entity no longer exists
            assert not arkiv_client_http.arkiv.entity_exists(entity_key)

        finally:
            event_filter.uninstall()

    def test_watch_entity_deleted_multiple_filters(self, arkiv_client_http):
        """Test multiple delete filters can coexist."""
        # Create an entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"test data", btl=100
        )

        # Setup two separate callbacks
        callback_1_triggered = ThreadEvent()
        callback_2_triggered = ThreadEvent()
        received_events_1: list[tuple[DeleteEvent, TxHash]] = []
        received_events_2: list[tuple[DeleteEvent, TxHash]] = []

        def on_delete_1(event: DeleteEvent, tx_hash: TxHash) -> None:
            """First callback for delete events."""
            # Only trigger event for OUR entity (prevents cross-test pollution)
            if event.key == entity_key:
                received_events_1.append((event, tx_hash))
                callback_1_triggered.set()

        def on_delete_2(event: DeleteEvent, tx_hash: TxHash) -> None:
            """Second callback for delete events."""
            if event.key == entity_key:
                received_events_2.append((event, tx_hash))
                callback_2_triggered.set()

        # Start two filters
        filter_1 = arkiv_client_http.arkiv.watch_entity_deleted(
            on_delete_1, from_block="latest"
        )
        filter_2 = arkiv_client_http.arkiv.watch_entity_deleted(
            on_delete_2, from_block="latest"
        )

        try:
            # Delete the entity
            receipt = arkiv_client_http.arkiv.delete_entity(entity_key=entity_key)

            # Wait for both callbacks
            assert callback_1_triggered.wait(timeout=5.0), (
                "Callback 1 was not triggered"
            )
            assert callback_2_triggered.wait(timeout=5.0), (
                "Callback 2 was not triggered"
            )

            # Verify both received the event
            assert len(received_events_1) == 1
            assert len(received_events_2) == 1

            # Verify both events have the same data
            assert received_events_1[0][0].key == entity_key
            assert received_events_2[0][0].key == entity_key
            assert received_events_1[0][1] == receipt.tx_hash
            assert received_events_2[0][1] == receipt.tx_hash

        finally:
            filter_1.uninstall()
            filter_2.uninstall()
