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
            btl=100,
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
            receipt = arkiv_client_http.arkiv.extend_entity(
                entity_key=entity_key,
                number_of_blocks=50,
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
            assert event.new_expiration_block == initial_expiration + 50
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
                btl=100,
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
            for entity_key in entity_keys:
                tx_hash = arkiv_client_http.arkiv.extend_entity(
                    entity_key=entity_key,
                    number_of_blocks=75,
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
                assert event.new_expiration_block == event.old_expiration_block + 75

        finally:
            event_filter.uninstall()

    def test_watch_entity_extended_manual_start_stop(self, arkiv_client_http):
        """Test manual start/stop of event filter."""
        # Create an entity first
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"initial", btl=100
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
            arkiv_client_http.arkiv.extend_entity(
                entity_key=entity_key, number_of_blocks=25
            )
            time.sleep(2)  # Wait a bit
            assert len(received_events) == 0

            # Now start the filter
            event_filter.start()
            assert event_filter.is_running

            # Extend again - SHOULD trigger callback
            arkiv_client_http.arkiv.extend_entity(
                entity_key=entity_key, number_of_blocks=30
            )
            time.sleep(3)  # Wait for polling
            assert len(received_events) == 1

            # Stop the filter
            event_filter.stop()
            assert not event_filter.is_running

            # Extend again - should NOT trigger callback
            count_after_stopping = len(received_events)
            arkiv_client_http.arkiv.extend_entity(
                entity_key=entity_key, number_of_blocks=35
            )
            time.sleep(2)
            assert len(received_events) == count_after_stopping

        finally:
            event_filter.uninstall()

    def test_watch_entity_extended_from_block_latest(self, arkiv_client_http):
        """Test that from_block='latest' only catches new extensions."""
        # Create entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"initial", btl=100
        )

        received_events: list[tuple[ExtendEvent, TxHash]] = []

        # Extend BEFORE starting the watcher
        arkiv_client_http.arkiv.extend_entity(
            entity_key=entity_key, number_of_blocks=20
        )

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
            arkiv_client_http.arkiv.extend_entity(
                entity_key=entity_key, number_of_blocks=40
            )
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
                payload=f"initial {i}".encode(), btl=100
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
                ExtendOp(key=entity_keys[0], number_of_blocks=60),
                ExtendOp(key=entity_keys[1], number_of_blocks=70),
                ExtendOp(key=entity_keys[2], number_of_blocks=80),
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
                expected_blocks = [60, 70, 80][idx]
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
            payload=b"initial data", btl=100
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
                entity_key=entity_key, payload=b"updated data", btl=100
            )
            time.sleep(3)  # Wait to ensure no callback
            assert len(received_events) == 0

            # Extend the entity - SHOULD trigger callback
            receipt = arkiv_client_http.arkiv.extend_entity(
                entity_key=entity_key, number_of_blocks=50
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
            payload=b"test data", btl=100
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
            for blocks in extensions:
                arkiv_client_http.arkiv.extend_entity(
                    entity_key=entity_key, number_of_blocks=blocks
                )
                # Update current_expiration for next iteration
                current_expiration += blocks

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
                    == event.old_expiration_block + extensions[i]
                )
                # Update expected_old for next event
                expected_old = event.new_expiration_block

        finally:
            event_filter.uninstall()

    def test_watch_entity_extended_expiration_tracking(self, arkiv_client_http):
        """Test that extend events correctly track old and new expiration blocks."""
        # Create entity with specific BTL
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"tracking test", btl=200
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
            # Extend by a specific number of blocks
            extension_blocks = 100
            arkiv_client_http.arkiv.extend_entity(
                entity_key=entity_key, number_of_blocks=extension_blocks
            )

            # Wait for callback
            assert callback_triggered.wait(timeout=10.0), (
                "Callback was not triggered within timeout"
            )

            # Verify the event has correct old and new expiration blocks
            assert len(received_events) == 1
            event, _ = received_events[0]

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
