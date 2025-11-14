"""Tests for entity extension event watching functionality."""

import time
from threading import Event as ThreadEvent

import pytest

from arkiv.types import ExtendEvent, ExtendOp, TxHash

from .utils import bulk_extend_entities


@pytest.mark.usefixtures("arkiv_client_http")
class TestWatchEntityExtended:
    """Test suite for watch_entity_extended functionality."""

    def test_watch_entity_extended_basic(self, arkiv_client_http):
        """Test basic watch_entity_extended functionality."""
        # Setup: Create an entity first
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"test data",
            expires_in=100,
        )

        # Get initial expiration block
        entity = arkiv_client_http.arkiv.get_entity(entity_key)
        initial_expiration = entity.expires_at_block

        # Setup callback with threading event
        callback_triggered = ThreadEvent()
        received_events: list[tuple[ExtendEvent, TxHash]] = []

        def on_extend(event: ExtendEvent, tx_hash: TxHash) -> None:
            """Callback for extend events."""
            received_events.append((event, tx_hash))
            callback_triggered.set()

        # Start watching for extend events
        event_filter = arkiv_client_http.arkiv.watch_entity_extended(
            on_extend, from_block="latest"
        )

        try:
            # Extend the entity - this should trigger the callback
            seconds = 50
            extension_blocks = arkiv_client_http.arkiv.to_blocks(seconds=seconds)
            receipt = arkiv_client_http.arkiv.extend_entity(
                entity_key=entity_key,
                extend_by=seconds,
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
            assert event.old_expiration_block == initial_expiration
            assert event.new_expiration_block > event.old_expiration_block
            assert event.new_expiration_block == initial_expiration + extension_blocks
            assert event_tx_hash == receipt.tx_hash

        finally:
            # Cleanup: stop and uninstall the filter
            event_filter.uninstall()

    def test_watch_entity_extended_multiple_events(self, arkiv_client_http):
        """Test watching multiple extension events."""
        # Create 3 entities first
        entity_keys = []
        for i in range(3):
            entity_key, _ = arkiv_client_http.arkiv.create_entity(
                payload=f"data {i}".encode(),
                expires_in=100,
            )
            entity_keys.append(entity_key)

        # Setup callback
        callback_triggered = ThreadEvent()
        received_events: list[tuple[ExtendEvent, TxHash]] = []

        def on_extend(event: ExtendEvent, tx_hash: TxHash) -> None:
            """Callback for extend events."""
            received_events.append((event, tx_hash))
            if len(received_events) == 3:
                callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_extended(
            on_extend, from_block="latest"
        )

        try:
            # Extend all entities
            extend_hashes = []
            seconds = 70
            extension_blocks = arkiv_client_http.arkiv.to_blocks(seconds=seconds)
            for entity_key in entity_keys:
                tx_hash = arkiv_client_http.arkiv.extend_entity(
                    entity_key=entity_key,
                    extend_by=seconds,
                )
                extend_hashes.append(tx_hash)

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

            # Verify all events have correct expiration block difference
            for event, _ in received_events:
                assert (
                    event.new_expiration_block
                    == event.old_expiration_block + extension_blocks
                )

        finally:
            event_filter.uninstall()

    def test_watch_entity_extended_manual_start_stop(self, arkiv_client_http):
        """Test manual start/stop of event filter."""
        # Create an entity first
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"initial", expires_in=100
        )

        received_events: list[tuple[ExtendEvent, TxHash]] = []

        def on_extend(event: ExtendEvent, tx_hash: TxHash) -> None:
            """Callback for extend events."""
            received_events.append((event, tx_hash))

        # Create filter without auto-start
        event_filter = arkiv_client_http.arkiv.watch_entity_extended(
            on_extend, from_block="latest", auto_start=False
        )

        try:
            # Filter should not be running
            assert not event_filter.is_running

            # Extend entity - should NOT trigger callback (filter not started)
            arkiv_client_http.arkiv.extend_entity(entity_key=entity_key, extend_by=50)
            time.sleep(2)  # Wait a bit
            assert len(received_events) == 0

            # Now start the filter
            event_filter.start()
            assert event_filter.is_running

            # Extend again - SHOULD trigger callback
            arkiv_client_http.arkiv.extend_entity(entity_key=entity_key, extend_by=30)
            time.sleep(3)  # Wait for polling
            assert len(received_events) == 1

            # Stop the filter
            event_filter.stop()
            assert not event_filter.is_running

            # Extend again - should NOT trigger callback
            count_after_stopping = len(received_events)
            arkiv_client_http.arkiv.extend_entity(entity_key=entity_key, extend_by=30)
            time.sleep(2)
            assert len(received_events) == count_after_stopping

        finally:
            event_filter.uninstall()

    def test_watch_entity_extended_from_block_latest(self, arkiv_client_http):
        """Test that from_block='latest' only catches new extensions."""
        # Create entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"initial", expires_in=100
        )

        received_events: list[tuple[ExtendEvent, TxHash]] = []

        # Extend BEFORE starting the watcher
        arkiv_client_http.arkiv.extend_entity(entity_key=entity_key, extend_by=20)

        def on_extend(event: ExtendEvent, tx_hash: TxHash) -> None:
            """Callback for extend events."""
            received_events.append((event, tx_hash))

        # Start watching from 'latest'
        event_filter = arkiv_client_http.arkiv.watch_entity_extended(
            on_extend, from_block="latest"
        )

        try:
            # Wait a bit for filter to initialize
            time.sleep(1)

            # The extension before should NOT be in received_events
            assert len(received_events) == 0

            # Extend again after filter started
            arkiv_client_http.arkiv.extend_entity(entity_key=entity_key, extend_by=40)
            time.sleep(3)  # Wait for polling

            # The new extension should be received
            assert len(received_events) == 1
            assert received_events[0][0].key == entity_key

        finally:
            event_filter.uninstall()

    def test_watch_entity_extended_bulk_extend(self, arkiv_client_http):
        """Test that bulk extend triggers callback for each entity."""
        # Create 3 entities first
        entity_keys = []
        for i in range(3):
            entity_key, _ = arkiv_client_http.arkiv.create_entity(
                payload=f"initial {i}".encode(), expires_in=100
            )
            entity_keys.append(entity_key)

        # Setup callback
        callback_triggered = ThreadEvent()
        received_events: list[tuple[ExtendEvent, TxHash]] = []

        def on_extend(event: ExtendEvent, tx_hash: TxHash) -> None:
            """Callback for extend events."""
            received_events.append((event, tx_hash))
            if len(received_events) == 3:
                callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_extended(
            on_extend, from_block="latest"
        )

        try:
            # Extend 3 entities in a single bulk transaction
            extend_ops = [
                ExtendOp(key=entity_keys[0], extend_by=60),
                ExtendOp(key=entity_keys[1], extend_by=70),
                ExtendOp(key=entity_keys[2], extend_by=80),
            ]
            receipt = bulk_extend_entities(
                arkiv_client_http, extend_ops, label="test_bulk_extend"
            )

            # Wait for all callbacks
            assert callback_triggered.wait(timeout=15.0), (
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

            # Verify each entity has the correct extension
            for event, _ in received_events:
                idx = entity_keys.index(event.key)
                expected_seconds = [60, 70, 80][idx]
                expected_blocks = arkiv_client_http.arkiv.to_blocks(
                    seconds=expected_seconds
                )
                assert (
                    event.new_expiration_block
                    == event.old_expiration_block + expected_blocks
                )

        finally:
            event_filter.uninstall()

    def test_watch_entity_extended_lifecycle_operations(self, arkiv_client_http):
        """Test that only extensions trigger callback, not create/update/delete."""
        # Create an entity first
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"initial data", expires_in=100
        )

        received_events: list[tuple[ExtendEvent, TxHash]] = []

        def on_extend(event: ExtendEvent, tx_hash: TxHash) -> None:
            """Callback for extend events."""
            received_events.append((event, tx_hash))

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_extended(
            on_extend, from_block="latest"
        )

        try:
            # Create happened before filter, so no callback
            time.sleep(1)
            assert len(received_events) == 0

            # Update the entity - should NOT trigger callback
            _ = arkiv_client_http.arkiv.update_entity(
                entity_key=entity_key, payload=b"updated data", expires_in=100
            )
            time.sleep(3)  # Wait to ensure no callback
            assert len(received_events) == 0

            # Extend the entity - SHOULD trigger callback
            receipt = arkiv_client_http.arkiv.extend_entity(
                entity_key=entity_key, extend_by=50
            )
            time.sleep(3)  # Wait for callback
            assert len(received_events) == 1
            assert received_events[0][0].key == entity_key
            assert received_events[0][1] == receipt.tx_hash

            # Delete the entity - should NOT trigger callback
            _ = arkiv_client_http.arkiv.delete_entity(entity_key=entity_key)
            time.sleep(3)  # Wait to ensure no callback
            assert len(received_events) == 1  # Still only 1 event

            # Verify the single event is the extend event
            event, tx_hash = received_events[0]
            assert event.key == entity_key
            assert tx_hash == receipt.tx_hash

        finally:
            event_filter.uninstall()

    def test_watch_entity_extended_multiple_extensions(self, arkiv_client_http):
        """Test watching multiple extensions of the same entity."""
        # Create entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"test data", expires_in=100
        )

        # Get initial expiration
        entity = arkiv_client_http.arkiv.get_entity(entity_key)
        current_expiration = entity.expires_at_block

        callback_triggered = ThreadEvent()
        received_events: list[tuple[ExtendEvent, TxHash]] = []

        def on_extend(event: ExtendEvent, tx_hash: TxHash) -> None:
            """Callback for extend events."""
            received_events.append((event, tx_hash))
            if len(received_events) == 3:
                callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_extended(
            on_extend, from_block="latest"
        )

        try:
            # Extend the same entity 3 times with different block counts
            extensions = [25, 40, 55]
            for seconds in extensions:
                arkiv_client_http.arkiv.extend_entity(
                    entity_key=entity_key, extend_by=seconds
                )
                # Update current_expiration for next iteration
                current_expiration += seconds

            # Wait for all callbacks
            assert callback_triggered.wait(timeout=15.0), (
                "Not all callbacks were triggered within timeout"
            )

            # Verify we received 3 events
            assert len(received_events) == 3

            # Verify progression of expiration blocks
            expected_old = entity.expires_at_block
            for i, (event, _) in enumerate(received_events):
                assert event.key == entity_key
                assert event.old_expiration_block == expected_old
                assert (
                    event.new_expiration_block
                    == event.old_expiration_block
                    + arkiv_client_http.arkiv.to_blocks(seconds=extensions[i])
                )
                # Update expected_old for next event
                expected_old = event.new_expiration_block

        finally:
            event_filter.uninstall()

    def test_watch_entity_extended_expiration_tracking(self, arkiv_client_http):
        """Test that extend events correctly track old and new expiration blocks."""
        # Create entity with specific expiration time
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"tracking test", expires_in=200
        )

        # Get initial expiration block
        entity = arkiv_client_http.arkiv.get_entity(entity_key)
        initial_expiration = entity.expires_at_block

        callback_triggered = ThreadEvent()
        received_events: list[tuple[ExtendEvent, TxHash]] = []

        def on_extend(event: ExtendEvent, tx_hash: TxHash) -> None:
            """Callback for extend events."""
            received_events.append((event, tx_hash))
            callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_extended(
            on_extend, from_block="latest"
        )

        try:
            # Extend by a specific number of seconds
            extension_seconds = 100
            arkiv_client_http.arkiv.extend_entity(
                entity_key=entity_key, extend_by=extension_seconds
            )

            # Wait for callback
            assert callback_triggered.wait(timeout=10.0), (
                "Callback was not triggered within timeout"
            )

            # Verify the event has correct old and new expiration blocks
            assert len(received_events) == 1
            event, _ = received_events[0]

            extension_blocks = arkiv_client_http.arkiv.to_blocks(
                seconds=extension_seconds
            )
            assert event.old_expiration_block == initial_expiration
            assert event.new_expiration_block == initial_expiration + extension_blocks
            assert (
                event.new_expiration_block - event.old_expiration_block
                == extension_blocks
            )

            # Verify actual entity expiration matches the event
            updated_entity = arkiv_client_http.arkiv.get_entity(entity_key)
            assert updated_entity.expires_at_block == event.new_expiration_block

        finally:
            event_filter.uninstall()
