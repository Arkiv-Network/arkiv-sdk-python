"""Tests for entity update event watching functionality."""

import logging
import time
from threading import Event as ThreadEvent

import pytest

from arkiv.types import Attributes, TxHash, UpdateEvent, UpdateOp

from .utils import bulk_update_entities

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("arkiv_client_http")
class TestWatchEntityUpdated:
    """Test suite for watch_entity_updated functionality."""

    def test_watch_entity_updated_basic(self, arkiv_client_http):
        """Test basic watch_entity_updated functionality."""
        # Setup: Create an entity first
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"initial data",
            attributes=Attributes({"version": "1"}),
            btl=100,
        )

        # Setup callback with threading event
        callback_triggered = ThreadEvent()
        received_events: list[tuple[UpdateEvent, TxHash]] = []

        def on_update(event: UpdateEvent, tx_hash: TxHash) -> None:
            """Callback for update events."""
            received_events.append((event, tx_hash))
            callback_triggered.set()

        # Start watching for update events
        event_filter = arkiv_client_http.arkiv.watch_entity_updated(
            on_update, from_block="latest"
        )

        try:
            # Update the entity - this should trigger the callback
            receipt = arkiv_client_http.arkiv.update_entity(
                entity_key=entity_key,
                payload=b"updated data",
                attributes=Attributes({"version": "2"}),
                btl=100,
            )

            # Wait for callback (with timeout)
            assert callback_triggered.wait(timeout=10.0), (
                "Callback was not triggered within timeout"
            )

            # Verify we received the event
            assert len(received_events) == 1
            event, event_tx_hash = received_events[0]
            logger.info(f"Received update event: {event}")

            # Verify event data
            assert event.key == entity_key
            assert event.new_expiration_block > 0
            assert event.new_expiration_block >= event.old_expiration_block
            assert event_tx_hash == receipt.tx_hash

        finally:
            # Cleanup: stop and uninstall the filter
            event_filter.uninstall()

    def test_watch_entity_updated_multiple_events(self, arkiv_client_http):
        """Test watching multiple update events."""
        # Create 3 entities first
        entity_keys = []
        for i in range(3):
            entity_key, _ = arkiv_client_http.arkiv.create_entity(
                payload=f"initial data {i}".encode(),
                btl=100,
            )
            entity_keys.append(entity_key)

        # Setup callback
        callback_triggered = ThreadEvent()
        received_events: list[tuple[UpdateEvent, TxHash]] = []

        def on_update(event: UpdateEvent, tx_hash: TxHash) -> None:
            """Callback for update events."""
            received_events.append((event, tx_hash))
            if len(received_events) == 3:
                callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_updated(
            on_update, from_block="latest"
        )

        try:
            # Update all entities
            update_hashes = []
            for i, entity_key in enumerate(entity_keys):
                tx_hash = arkiv_client_http.arkiv.update_entity(
                    entity_key=entity_key,
                    payload=f"updated data {i}".encode(),
                    btl=100,
                )
                update_hashes.append(tx_hash)

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

    def test_watch_entity_updated_manual_start_stop(self, arkiv_client_http):
        """Test manual start/stop of event filter."""
        # Create an entity first
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"initial", btl=100
        )

        received_events: list[tuple[UpdateEvent, TxHash]] = []

        def on_update(event: UpdateEvent, tx_hash: TxHash) -> None:
            """Callback for update events."""
            received_events.append((event, tx_hash))

        # Create filter without auto-start
        event_filter = arkiv_client_http.arkiv.watch_entity_updated(
            on_update, from_block="latest", auto_start=False
        )

        try:
            # Filter should not be running
            assert not event_filter.is_running

            # Update entity - should NOT trigger callback (filter not started)
            arkiv_client_http.arkiv.update_entity(
                entity_key=entity_key, payload=b"update 1", btl=100
            )
            time.sleep(2)  # Wait a bit
            assert len(received_events) == 0

            # Now start the filter
            event_filter.start()
            assert event_filter.is_running

            # Update again - SHOULD trigger callback
            arkiv_client_http.arkiv.update_entity(
                entity_key=entity_key, payload=b"update 2", btl=100
            )
            time.sleep(3)  # Wait for polling
            assert len(received_events) == 1

            # Stop the filter
            event_filter.stop()
            assert not event_filter.is_running

            # Update again - should NOT trigger callback
            count_after_stopping = len(received_events)
            arkiv_client_http.arkiv.update_entity(
                entity_key=entity_key, payload=b"update 3", btl=100
            )
            time.sleep(2)
            assert len(received_events) == count_after_stopping

        finally:
            event_filter.uninstall()

    def test_watch_entity_updated_from_block_latest(self, arkiv_client_http):
        """Test that from_block='latest' only catches new updates."""
        # Create entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"initial", btl=100
        )

        received_events: list[tuple[UpdateEvent, TxHash]] = []

        # Update BEFORE starting the watcher
        arkiv_client_http.arkiv.update_entity(
            entity_key=entity_key, payload=b"before", btl=100
        )

        def on_update(event: UpdateEvent, tx_hash: TxHash) -> None:
            """Callback for update events."""
            received_events.append((event, tx_hash))

        # Start watching from 'latest'
        event_filter = arkiv_client_http.arkiv.watch_entity_updated(
            on_update, from_block="latest"
        )

        try:
            # Wait a bit for filter to initialize
            time.sleep(1)

            # The update before should NOT be in received_events
            assert len(received_events) == 0

            # Update again after filter started
            arkiv_client_http.arkiv.update_entity(
                entity_key=entity_key, payload=b"after", btl=100
            )
            time.sleep(3)  # Wait for polling

            # The new update should be received
            assert len(received_events) == 1
            assert received_events[0][0].key == entity_key

        finally:
            event_filter.uninstall()

    def test_watch_entity_updated_bulk_update(self, arkiv_client_http):
        """Test that bulk update triggers callback for each entity."""
        # Create 3 entities first
        entity_keys = []
        for i in range(3):
            entity_key, _ = arkiv_client_http.arkiv.create_entity(
                payload=f"initial {i}".encode(), btl=100
            )
            entity_keys.append(entity_key)

        # Setup callback
        callback_triggered = ThreadEvent()
        received_events: list[tuple[UpdateEvent, TxHash]] = []

        def on_update(event: UpdateEvent, tx_hash: TxHash) -> None:
            """Callback for update events."""
            received_events.append((event, tx_hash))
            if len(received_events) == 3:
                callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_updated(
            on_update, from_block="latest"
        )

        try:
            # Update 3 entities in a single bulk transaction
            update_ops = [
                UpdateOp(
                    key=entity_keys[0],
                    payload=b"bulk update 1",
                    content_type="text/plain",
                    attributes=Attributes({}),
                    btl=100,
                ),
                UpdateOp(
                    key=entity_keys[1],
                    payload=b"bulk update 2",
                    content_type="text/plain",
                    attributes=Attributes({}),
                    btl=100,
                ),
                UpdateOp(
                    key=entity_keys[2],
                    payload=b"bulk update 3",
                    content_type="text/plain",
                    attributes=Attributes({}),
                    btl=100,
                ),
            ]
            tx_hash = bulk_update_entities(
                arkiv_client_http, update_ops, label="test_bulk_update"
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
            assert tx_hashes.pop() == tx_hash

        finally:
            event_filter.uninstall()

    def test_watch_entity_updated_lifecycle_operations(self, arkiv_client_http):
        """Test that only updates trigger callback, not create/extend/delete."""
        # Create an entity first
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"initial data", btl=100
        )

        received_events: list[tuple[UpdateEvent, TxHash]] = []

        def on_update(event: UpdateEvent, tx_hash: TxHash) -> None:
            """Callback for update events."""
            received_events.append((event, tx_hash))

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_updated(
            on_update, from_block="latest"
        )

        try:
            # Create happened before filter, so no callback
            time.sleep(1)
            assert len(received_events) == 0

            # Update the entity - SHOULD trigger callback
            receipt = arkiv_client_http.arkiv.update_entity(
                entity_key=entity_key, payload=b"updated data", btl=100
            )
            time.sleep(3)  # Wait for callback
            assert len(received_events) == 1
            assert received_events[0][0].key == entity_key
            assert received_events[0][1] == receipt.tx_hash

            # Extend the entity - should NOT trigger callback
            arkiv_client_http.arkiv.extend_entity(
                entity_key=entity_key, number_of_blocks=50
            )
            time.sleep(3)  # Wait to ensure no callback
            assert len(received_events) == 1  # Still only 1 event

            # Delete the entity - should NOT trigger callback
            arkiv_client_http.arkiv.delete_entity(entity_key=entity_key)
            time.sleep(3)  # Wait to ensure no callback
            assert len(received_events) == 1  # Still only 1 event

            # Verify the single event is the update event
            event, tx_hash = received_events[0]
            assert event.key == entity_key
            assert tx_hash == receipt.tx_hash

        finally:
            event_filter.uninstall()

    def test_watch_entity_updated_only_payload(self, arkiv_client_http):
        """Test update event when only payload changes."""
        # Create entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"initial payload",
            attributes=Attributes({"key": "value"}),
            btl=100,
        )

        callback_triggered = ThreadEvent()
        received_events: list[tuple[UpdateEvent, TxHash]] = []

        def on_update(event: UpdateEvent, tx_hash: TxHash) -> None:
            """Callback for update events."""
            received_events.append((event, tx_hash))
            callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_updated(
            on_update, from_block="latest"
        )

        try:
            # Update only payload (keep same attributes and btl)
            arkiv_client_http.arkiv.update_entity(
                entity_key=entity_key,
                payload=b"new payload only",
                attributes=Attributes({"key": "value"}),  # Same attributes
                btl=100,  # Same BTL
            )

            # Should trigger callback
            assert callback_triggered.wait(timeout=10.0), (
                "Callback was not triggered for payload-only update"
            )

            assert len(received_events) == 1
            assert received_events[0][0].key == entity_key

        finally:
            event_filter.uninstall()

    def test_watch_entity_updated_only_attributes(self, arkiv_client_http):
        """Test update event when only attributes change."""
        # Create entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"same payload",
            attributes=Attributes({"version": "1"}),
            btl=100,
        )

        callback_triggered = ThreadEvent()
        received_events: list[tuple[UpdateEvent, TxHash]] = []

        def on_update(event: UpdateEvent, tx_hash: TxHash) -> None:
            """Callback for update events."""
            received_events.append((event, tx_hash))
            callback_triggered.set()

        # Start watching
        event_filter = arkiv_client_http.arkiv.watch_entity_updated(
            on_update, from_block="latest"
        )

        try:
            # Update only attributes (keep same payload and btl)
            arkiv_client_http.arkiv.update_entity(
                entity_key=entity_key,
                payload=b"same payload",  # Same payload
                attributes=Attributes({"version": "2"}),  # Different attributes
                btl=100,  # Same BTL
            )

            # Should trigger callback
            assert callback_triggered.wait(timeout=10.0), (
                "Callback was not triggered for attributes-only update"
            )

            assert len(received_events) == 1
            assert received_events[0][0].key == entity_key

        finally:
            event_filter.uninstall()
