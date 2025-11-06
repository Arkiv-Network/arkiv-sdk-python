"""Tests for event watching functionality."""

import time
from threading import Event as ThreadEvent

import pytest

from arkiv.types import Attributes, CreateEvent, CreateOp, TxHash

from .utils import create_entities


@pytest.mark.usefixtures("arkiv_client_http")
class TestWatchEntityCreated:
    """Test suite for watch_entity_created functionality."""

    def test_watch_entity_created_basic(self, arkiv_client_http):
        """Test basic watch_entity_created functionality."""
        # Setup: Use a threading.Event to signal when callback is triggered
        callback_triggered = ThreadEvent()
        received_events: list[tuple[CreateEvent, TxHash]] = []

        def on_create(event: CreateEvent, tx_hash: TxHash) -> None:
            """Callback for create events."""
            received_events.append((event, tx_hash))
            callback_triggered.set()

        # Start watching for create events
        event_filter = arkiv_client_http.arkiv.watch_entity_created(
            on_create, from_block="latest"
        )

        try:
            # Create an entity - this should trigger the callback
            entity_key, receipt = arkiv_client_http.arkiv.create_entity(
                payload=b"test data",
                attributes=Attributes({"test": "value"}),
                btl=100,
            )

            # Wait for callback (with timeout)
            assert callback_triggered.wait(timeout=10.0), (
                "Callback was not triggered within timeout"
            )

            # Verify we received the event
            assert len(received_events) == 1
            event, event_tx_hash = received_events[0]

            # Verify event data
            assert event.key == entity_key
            assert event.expiration_block > 0
            assert event_tx_hash == receipt.tx_hash

        finally:
            # Cleanup: stop and uninstall the filter
            event_filter.uninstall()

    def test_watch_entity_created_multiple_events(self, arkiv_client_http):
        """Test watching multiple create events."""
        callback_triggered = ThreadEvent()
        received_events: list[tuple[CreateEvent, TxHash]] = []

        def on_create(event: CreateEvent, tx_hash: TxHash) -> None:
            """Callback for create events."""
            received_events.append((event, tx_hash))
            if len(received_events) == 3:
                callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_created(
            on_create, from_block="latest"
        )

        try:
            # Create multiple entities
            keys_and_hashes = []
            for i in range(3):
                entity_key, tx_hash = arkiv_client_http.arkiv.create_entity(
                    payload=f"test data {i}".encode(),
                    btl=100,
                )
                keys_and_hashes.append((entity_key, tx_hash))

            # Wait for all callbacks
            assert callback_triggered.wait(timeout=15.0), (
                "Not all callbacks were triggered within timeout"
            )

            # Verify we received all events
            assert len(received_events) == 3

            # Verify all entity keys match
            received_keys = {event.key for event, _ in received_events}
            expected_keys = {key for key, _ in keys_and_hashes}
            assert received_keys == expected_keys

        finally:
            event_filter.uninstall()

    def test_watch_entity_created_manual_start_stop(self, arkiv_client_http):
        """Test manual start/stop of event filter."""
        received_events: list[tuple[CreateEvent, TxHash]] = []

        def on_create(event: CreateEvent, tx_hash: TxHash) -> None:
            """Callback for create events."""
            received_events.append((event, tx_hash))

        # Create filter without auto-start
        event_filter = arkiv_client_http.arkiv.watch_entity_created(
            on_create, from_block="latest", auto_start=False
        )

        try:
            # Filter should not be running
            assert not event_filter.is_running

            # Create an entity - should NOT trigger callback (filter not started)
            arkiv_client_http.arkiv.create_entity(payload=b"test 1", btl=100)
            time.sleep(2)  # Wait a bit
            assert len(received_events) == 0

            # Now start the filter
            event_filter.start()
            assert event_filter.is_running

            # Create another entity - SHOULD trigger callback
            arkiv_client_http.arkiv.create_entity(payload=b"test 2", btl=100)
            time.sleep(3)  # Wait for polling
            assert len(received_events) == 1

            # Stop the filter
            event_filter.stop()
            assert not event_filter.is_running

            # Create another entity - should NOT trigger callback
            count_after_stopping = len(received_events)
            arkiv_client_http.arkiv.create_entity(payload=b"test 3", btl=100)
            time.sleep(2)
            assert len(received_events) == count_after_stopping

        finally:
            event_filter.uninstall()

    def test_watch_entity_created_from_block_latest(self, arkiv_client_http):
        """Test that from_block='latest' only catches new events."""
        received_events: list[tuple[CreateEvent, TxHash]] = []

        # Create an entity BEFORE starting the watcher
        entity_key_before, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"before", btl=100
        )

        def on_create(event: CreateEvent, tx_hash: TxHash) -> None:
            """Callback for create events."""
            received_events.append((event, tx_hash))

        # Start watching from 'latest'
        event_filter = arkiv_client_http.arkiv.watch_entity_created(
            on_create, from_block="latest"
        )

        try:
            # Wait a bit for filter to initialize
            time.sleep(1)

            # The entity created before should NOT be in received_events
            assert not any(
                event.key == entity_key_before for event, _ in received_events
            )

            # Create a new entity
            entity_key_after, _ = arkiv_client_http.arkiv.create_entity(
                payload=b"after", btl=100
            )
            time.sleep(3)  # Wait for polling

            # The new entity should be received
            assert any(event.key == entity_key_after for event, _ in received_events)

        finally:
            event_filter.uninstall()

    def test_watch_entity_created_bulk_create(self, arkiv_client_http):
        """Test that bulk create triggers callback for each entity."""
        callback_triggered = ThreadEvent()
        received_events: list[tuple[CreateEvent, TxHash]] = []

        def on_create(event: CreateEvent, tx_hash: TxHash) -> None:
            """Callback for create events."""
            received_events.append((event, tx_hash))
            if len(received_events) == 3:
                callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_created(
            on_create, from_block="latest"
        )

        try:
            # Create 3 entities in a single bulk transaction
            create_ops = [
                CreateOp(
                    payload=b"bulk entity 1",
                    content_type="text/plain",
                    attributes=Attributes({}),
                    btl=100,
                ),
                CreateOp(
                    payload=b"bulk entity 2",
                    content_type="text/plain",
                    attributes=Attributes({}),
                    btl=100,
                ),
                CreateOp(
                    payload=b"bulk entity 3",
                    content_type="text/plain",
                    attributes=Attributes({}),
                    btl=100,
                ),
            ]
            entity_keys, tx_hash = create_entities(arkiv_client_http, create_ops)

            # Wait for all callbacks
            assert callback_triggered.wait(timeout=15.0), (
                "Not all callbacks were triggered within timeout"
            )

            # Verify we received 3 events (one for each entity)
            assert len(received_events) == 3

            # Verify all entity keys match and all have the same tx_hash (same transaction)
            received_keys = {event.key for event, _ in received_events}
            expected_keys = set(entity_keys)
            assert received_keys == expected_keys

            # Verify all events share the same transaction hash
            tx_hashes = {event_tx_hash for _, event_tx_hash in received_events}
            assert len(tx_hashes) == 1, (
                "All events should share the same transaction hash"
            )
            assert tx_hashes.pop() == tx_hash

        finally:
            event_filter.uninstall()

    def test_watch_entity_created_lifecycle_operations(self, arkiv_client_http):
        """Test that only creation triggers callback, not update/extend/delete."""
        received_events: list[tuple[CreateEvent, TxHash]] = []

        def on_create(event: CreateEvent, tx_hash: TxHash) -> None:
            """Callback for create events."""
            received_events.append((event, tx_hash))

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_created(
            on_create, from_block="latest"
        )

        try:
            # Create an entity - SHOULD trigger callback
            entity_key, receipt = arkiv_client_http.arkiv.create_entity(
                payload=b"initial data", btl=100
            )
            time.sleep(3)  # Wait for callback
            assert len(received_events) == 1
            assert received_events[0][0].key == entity_key

            # Update the entity - should NOT trigger callback
            _ = arkiv_client_http.arkiv.update_entity(
                entity_key=entity_key, payload=b"updated data", btl=100
            )
            time.sleep(3)  # Wait to ensure no callback
            assert len(received_events) == 1  # Still only 1 event

            # Extend the entity - should NOT trigger callback
            _ = arkiv_client_http.arkiv.extend_entity(
                entity_key=entity_key, number_of_blocks=50
            )
            time.sleep(3)  # Wait to ensure no callback
            assert len(received_events) == 1  # Still only 1 event

            # Delete the entity - should NOT trigger callback
            _ = arkiv_client_http.arkiv.delete_entity(entity_key=entity_key)
            time.sleep(3)  # Wait to ensure no callback
            assert len(received_events) == 1  # Still only 1 event

            # Verify the single event is the creation event
            event, tx_hash = received_events[0]
            assert event.key == entity_key
            assert tx_hash == receipt.tx_hash

        finally:
            event_filter.uninstall()
