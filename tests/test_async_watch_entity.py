"""Async event watching tests - focused on async-specific behavior."""

import asyncio
import logging

import pytest

from arkiv.types import (
    ChangeOwnerEvent,
    CreateEvent,
    DeleteEvent,
    ExtendEvent,
    TxHash,
    UpdateEvent,
)

logger = logging.getLogger(__name__)


class TestAsyncWatchEntityCreated:
    """Test async watching of entity creation events."""

    @pytest.mark.asyncio
    async def test_async_watch_entity_created_basic(self, async_arkiv_client_http):
        """Smoke test: async watch entity created works."""
        events_received = []

        async def on_created(event: CreateEvent, tx_hash: TxHash) -> None:
            logger.info(f"Async callback: Created {event.key}")
            events_received.append((event, tx_hash))

        # Create and start filter
        filter = await async_arkiv_client_http.arkiv.watch_entity_created(on_created)

        try:
            # Create an entity
            entity_key, receipt = await async_arkiv_client_http.arkiv.create_entity(
                payload=b"async test", attributes={"test": "async_created"}
            )

            # Wait for event to be processed
            await asyncio.sleep(5)

            # Verify callback was invoked
            assert len(events_received) == 1
            assert events_received[0][0].key == entity_key
            assert events_received[0][1] == receipt.tx_hash

        finally:
            await filter.uninstall()

    @pytest.mark.asyncio
    async def test_async_callback_is_awaited(self, async_arkiv_client_http):
        """Verify that async callbacks are properly awaited."""
        callback_started = asyncio.Event()
        callback_completed = asyncio.Event()
        events_received = []

        async def on_created(event: CreateEvent, tx_hash: TxHash) -> None:
            callback_started.set()
            # Simulate async work
            await asyncio.sleep(0.1)
            events_received.append(event)
            callback_completed.set()

        filter = await async_arkiv_client_http.arkiv.watch_entity_created(on_created)

        try:
            # Create entity
            entity_key, _ = await async_arkiv_client_http.arkiv.create_entity(
                payload=b"test await"
            )

            # Wait for callback to start
            await asyncio.wait_for(callback_started.wait(), timeout=3.0)

            # Verify callback completes (proving it was awaited)
            await asyncio.wait_for(callback_completed.wait(), timeout=2.0)

            assert len(events_received) == 1
            assert events_received[0].key == entity_key

        finally:
            await filter.uninstall()


class TestAsyncWatchEntityUpdated:
    """Test async watching of entity update events."""

    @pytest.mark.asyncio
    async def test_async_watch_entity_updated_basic(self, async_arkiv_client_http):
        """Smoke test: async watch entity updated works."""
        events_received = []

        async def on_updated(event: UpdateEvent, tx_hash: TxHash) -> None:
            logger.info(f"Async callback: Updated {event.key}")
            events_received.append((event, tx_hash))

        filter = await async_arkiv_client_http.arkiv.watch_entity_updated(on_updated)

        try:
            # Create then update an entity
            entity_key, _ = await async_arkiv_client_http.arkiv.create_entity(
                payload=b"original"
            )

            receipt = await async_arkiv_client_http.arkiv.update_entity(
                entity_key, payload=b"updated", attributes={"status": "updated"}
            )

            # Wait for event
            await asyncio.sleep(2)

            assert len(events_received) == 1
            assert events_received[0][0].key == entity_key
            assert events_received[0][1] == receipt.tx_hash

        finally:
            await filter.uninstall()


class TestAsyncWatchEntityExtended:
    """Test async watching of entity extension events."""

    @pytest.mark.asyncio
    async def test_async_watch_entity_extended_basic(self, async_arkiv_client_http):
        """Smoke test: async watch entity extended works."""
        events_received = []

        async def on_extended(event: ExtendEvent, tx_hash: TxHash) -> None:
            logger.info(f"Async callback: Extended {event.key}")
            events_received.append((event, tx_hash))

        filter = await async_arkiv_client_http.arkiv.watch_entity_extended(on_extended)

        try:
            # Create then extend an entity
            entity_key, _ = await async_arkiv_client_http.arkiv.create_entity(
                payload=b"test extend"
            )

            receipt = await async_arkiv_client_http.arkiv.extend_entity(
                entity_key, number_of_blocks=100
            )

            # Wait for event
            await asyncio.sleep(2)

            assert len(events_received) == 1
            assert events_received[0][0].key == entity_key
            assert events_received[0][1] == receipt.tx_hash

        finally:
            await filter.uninstall()


class TestAsyncWatchEntityDeleted:
    """Test async watching of entity deletion events."""

    @pytest.mark.asyncio
    async def test_async_watch_entity_deleted_basic(self, async_arkiv_client_http):
        """Smoke test: async watch entity deleted works."""
        events_received = []

        async def on_deleted(event: DeleteEvent, tx_hash: TxHash) -> None:
            logger.info(f"Async callback: Deleted {event.key}")
            events_received.append((event, tx_hash))

        filter = await async_arkiv_client_http.arkiv.watch_entity_deleted(on_deleted)

        try:
            # Create then delete an entity
            entity_key, _ = await async_arkiv_client_http.arkiv.create_entity(
                payload=b"to delete"
            )

            receipt = await async_arkiv_client_http.arkiv.delete_entity(entity_key)

            # Wait for event
            await asyncio.sleep(2)

            assert len(events_received) == 1
            assert events_received[0][0].key == entity_key
            assert events_received[0][1] == receipt.tx_hash

        finally:
            await filter.uninstall()


class TestAsyncWatchOwnerChanged:
    """Test async watching of entity owner change events."""

    @pytest.mark.asyncio
    async def test_async_watch_owner_changed_basic(
        self, async_arkiv_client_http, account_2
    ):
        """Smoke test: async watch owner changed works."""
        events_received = []

        async def on_owner_changed(event: ChangeOwnerEvent, tx_hash: TxHash) -> None:
            logger.info(
                f"Async callback: Owner changed for {event.key} from {event.old_owner_address} to {event.new_owner_address}"
            )
            events_received.append((event, tx_hash))

        filter = await async_arkiv_client_http.arkiv.watch_owner_changed(
            on_owner_changed
        )

        try:
            # Create an entity
            entity_key, _ = await async_arkiv_client_http.arkiv.create_entity(
                payload=b"test owner change"
            )

            # Get the entity to verify current owner
            entity = await async_arkiv_client_http.arkiv.get_entity(entity_key)
            original_owner = entity.owner

            # Change the owner
            receipt = await async_arkiv_client_http.arkiv.change_owner(
                entity_key, new_owner=account_2.address
            )

            # Wait for event
            await asyncio.sleep(2)

            # Verify callback was invoked
            assert len(events_received) == 1
            event, event_tx_hash = events_received[0]
            assert event.key == entity_key
            assert event.old_owner_address == original_owner
            assert event.new_owner_address == account_2.address
            assert event_tx_hash == receipt.tx_hash

        finally:
            await filter.uninstall()


class TestAsyncWatchConcurrentFilters:
    """Test concurrent async filter execution."""

    @pytest.mark.asyncio
    async def test_concurrent_filters_same_event_type(self, async_arkiv_client_http):
        """Test multiple filters watching the same event type concurrently."""
        events_filter1 = []
        events_filter2 = []

        async def callback1(event: CreateEvent, tx_hash: TxHash) -> None:
            await asyncio.sleep(0.05)  # Simulate async work
            events_filter1.append(event)

        async def callback2(event: CreateEvent, tx_hash: TxHash) -> None:
            await asyncio.sleep(0.05)  # Simulate async work
            events_filter2.append(event)

        # Create two filters for same event type
        filter1 = await async_arkiv_client_http.arkiv.watch_entity_created(callback1)
        filter2 = await async_arkiv_client_http.arkiv.watch_entity_created(callback2)

        try:
            # Create entities
            entity1, _ = await async_arkiv_client_http.arkiv.create_entity(b"entity1")
            entity2, _ = await async_arkiv_client_http.arkiv.create_entity(b"entity2")

            # Wait for events to be processed
            await asyncio.sleep(3)

            # Both filters should have received both events
            assert len(events_filter1) == 2
            assert len(events_filter2) == 2

            keys1 = {e.key for e in events_filter1}
            keys2 = {e.key for e in events_filter2}
            assert keys1 == {entity1, entity2}
            assert keys2 == {entity1, entity2}

        finally:
            await filter1.uninstall()
            await filter2.uninstall()

    @pytest.mark.asyncio
    async def test_concurrent_filters_different_event_types(
        self, async_arkiv_client_http
    ):
        """Test multiple filters watching different event types concurrently."""
        created_events = []
        updated_events = []
        deleted_events = []

        async def on_created(event: CreateEvent, tx_hash: TxHash) -> None:
            await asyncio.sleep(0.01)
            created_events.append(event)

        async def on_updated(event: UpdateEvent, tx_hash: TxHash) -> None:
            await asyncio.sleep(0.01)
            updated_events.append(event)

        async def on_deleted(event: DeleteEvent, tx_hash: TxHash) -> None:
            await asyncio.sleep(0.01)
            deleted_events.append(event)

        # Create filters for different event types
        filter_created = await async_arkiv_client_http.arkiv.watch_entity_created(
            on_created
        )
        filter_updated = await async_arkiv_client_http.arkiv.watch_entity_updated(
            on_updated
        )
        filter_deleted = await async_arkiv_client_http.arkiv.watch_entity_deleted(
            on_deleted
        )

        try:
            # Trigger different event types
            entity_key, _ = await async_arkiv_client_http.arkiv.create_entity(
                b"test concurrent"
            )
            await async_arkiv_client_http.arkiv.update_entity(
                entity_key, payload=b"updated"
            )
            await async_arkiv_client_http.arkiv.delete_entity(entity_key)

            # Wait for all events
            await asyncio.sleep(3)

            # Each filter should have received its event type
            assert len(created_events) == 1
            assert len(updated_events) == 1
            assert len(deleted_events) == 1

            assert created_events[0].key == entity_key
            assert updated_events[0].key == entity_key
            assert deleted_events[0].key == entity_key

        finally:
            await filter_created.uninstall()
            await filter_updated.uninstall()
            await filter_deleted.uninstall()


class TestAsyncWatchErrorHandling:
    """Test error handling in async callbacks."""

    @pytest.mark.asyncio
    async def test_callback_exception_does_not_stop_filter(
        self, async_arkiv_client_http
    ):
        """Verify that exceptions in callbacks don't stop the filter."""
        events_received = []
        exception_count = 0

        async def failing_callback(event: CreateEvent, tx_hash: TxHash) -> None:
            nonlocal exception_count
            exception_count += 1
            if exception_count == 1:
                # First event: raise exception
                raise ValueError("Intentional test exception")
            else:
                # Subsequent events: process normally
                events_received.append(event)

        filter = await async_arkiv_client_http.arkiv.watch_entity_created(
            failing_callback
        )

        try:
            # Create first entity (will trigger exception)
            await async_arkiv_client_http.arkiv.create_entity(b"entity1")
            await asyncio.sleep(2)

            # Create second entity (should be processed normally)
            entity2, _ = await async_arkiv_client_http.arkiv.create_entity(b"entity2")
            await asyncio.sleep(2)

            # Filter should still be running and process second event
            assert exception_count == 2
            assert len(events_received) == 1
            assert events_received[0].key == entity2

        finally:
            await filter.uninstall()


class TestAsyncWatchFilterLifecycle:
    """Test async filter lifecycle management."""

    @pytest.mark.asyncio
    async def test_manual_start_stop(self, async_arkiv_client_http):
        """Test manual start/stop of async filters."""
        events_received = []

        async def callback(event: CreateEvent, tx_hash: TxHash) -> None:
            events_received.append(event)

        # Create filter without auto-start
        filter = await async_arkiv_client_http.arkiv.watch_entity_created(
            callback, auto_start=False
        )

        try:
            # Filter not running yet
            assert not filter.is_running

            # Create entity while filter is stopped
            _ = await async_arkiv_client_http.arkiv.create_entity(b"stopped")
            await asyncio.sleep(1)

            # No events received
            assert len(events_received) == 0

            # Start filter
            await filter.start()
            assert filter.is_running

            # Create entity while filter is running
            entity2, _ = await async_arkiv_client_http.arkiv.create_entity(b"running")
            await asyncio.sleep(2)

            # Only second entity received
            assert len(events_received) == 1
            assert events_received[0].key == entity2

            # Stop filter
            await filter.stop()
            assert not filter.is_running

            # Create entity while stopped again
            await async_arkiv_client_http.arkiv.create_entity(b"stopped again")
            await asyncio.sleep(1)

            # Still only one event
            assert len(events_received) == 1

        finally:
            await filter.uninstall()

    @pytest.mark.asyncio
    async def test_cleanup_filters(self, async_arkiv_client_http):
        """Test cleanup_filters stops all active filters."""
        events1 = []
        events2 = []

        async def callback1(event: CreateEvent, tx_hash: TxHash) -> None:
            events1.append(event)

        async def callback2(event: UpdateEvent, tx_hash: TxHash) -> None:
            events2.append(event)

        # Create multiple filters
        filter1 = await async_arkiv_client_http.arkiv.watch_entity_created(callback1)
        filter2 = await async_arkiv_client_http.arkiv.watch_entity_updated(callback2)

        # Verify both running
        assert filter1.is_running
        assert filter2.is_running
        assert len(async_arkiv_client_http.arkiv.active_filters) >= 2

        # Cleanup all filters
        await async_arkiv_client_http.arkiv.cleanup_filters()

        # Verify both stopped
        assert not filter1.is_running
        assert not filter2.is_running

    @pytest.mark.asyncio
    async def test_uninstall_running_filter(self, async_arkiv_client_http):
        """Test that uninstall stops a running filter."""
        events_received = []

        async def callback(event: CreateEvent, tx_hash: TxHash) -> None:
            events_received.append(event)

        filter = await async_arkiv_client_http.arkiv.watch_entity_created(callback)

        assert filter.is_running

        # Uninstall should stop the filter
        await filter.uninstall()

        assert not filter.is_running

        # Create entity after uninstall
        await async_arkiv_client_http.arkiv.create_entity(b"after uninstall")
        await asyncio.sleep(1)

        # No events should be received
        assert len(events_received) == 0
