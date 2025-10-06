"""Tests for automatic filter cleanup on context exit."""

import time

from arkiv import Arkiv
from arkiv.account import NamedAccount
from arkiv.provider import ProviderBuilder
from arkiv.types import CreateEvent, TxHash


def test_filter_cleanup_on_context_exit(arkiv_node):
    """Test that filters are automatically cleaned up when client context exits."""
    received_events: list[tuple[CreateEvent, TxHash]] = []

    def on_create(event: CreateEvent, tx_hash: TxHash) -> None:
        """Callback for create events."""
        received_events.append((event, tx_hash))

    # Create and fund a fresh account
    account = NamedAccount.create("test_cleanup")
    arkiv_node.fund_account(account)
    provider = ProviderBuilder().node(arkiv_node).build()
    # Use context manager - filters should auto-cleanup on exit
    with Arkiv(provider, account=account) as arkiv:
        # Create a filter
        event_filter = arkiv.arkiv.watch_entity_created(on_create, from_block="latest")

        # Verify filter is running
        assert event_filter.is_running

        # Verify it's tracked
        assert len(arkiv.arkiv.active_filters) == 1
        assert event_filter in arkiv.arkiv.active_filters

        # Create an entity to trigger the event
        arkiv.arkiv.create_entity(payload=b"test", btl=100)
        time.sleep(3)  # Wait for event

        # Event should be received
        assert len(received_events) >= 1

    # After context exit, filter should be stopped and uninstalled
    assert not event_filter.is_running
    assert len(arkiv.arkiv.active_filters) == 0


def test_multiple_filters_cleanup_on_context_exit(arkiv_node):
    """Test that multiple filters are all cleaned up."""

    def callback1(event: CreateEvent, tx_hash: TxHash) -> None:
        pass

    def callback2(event: CreateEvent, tx_hash: TxHash) -> None:
        pass

    # Create and fund a fresh account
    account = NamedAccount.create("test_multi_cleanup")
    arkiv_node.fund_account(account)
    provider = ProviderBuilder().node(arkiv_node).build()

    # Use context manager
    with Arkiv(provider, account=account) as arkiv:
        filter1 = arkiv.arkiv.watch_entity_created(callback1, from_block="latest")
        filter2 = arkiv.arkiv.watch_entity_created(callback2, from_block="latest")

        # Both should be tracked
        assert len(arkiv.arkiv.active_filters) == 2
        assert filter1.is_running
        assert filter2.is_running

    # After exit, both should be stopped
    assert not filter1.is_running
    assert not filter2.is_running
    assert len(arkiv.arkiv.active_filters) == 0


def test_manual_cleanup_filters(arkiv_client_http):
    """Test manual cleanup_filters() call."""

    def callback(event: CreateEvent, tx_hash: TxHash) -> None:
        pass

    # Create filters
    filter1 = arkiv_client_http.arkiv.watch_entity_created(
        callback, from_block="latest"
    )
    filter2 = arkiv_client_http.arkiv.watch_entity_created(
        callback, from_block="latest"
    )

    assert filter1.is_running
    assert filter2.is_running
    assert len(arkiv_client_http.arkiv.active_filters) == 2

    # Manual cleanup
    arkiv_client_http.arkiv.cleanup_filters()

    # Both should be stopped and list cleared
    assert not filter1.is_running
    assert not filter2.is_running
    assert len(arkiv_client_http.arkiv.active_filters) == 0


def test_filter_cleanup_with_manual_uninstall(arkiv_client_http):
    """Test that manually uninstalled filters don't cause issues during cleanup."""

    def callback(event: CreateEvent, tx_hash: TxHash) -> None:
        pass

    filter1 = arkiv_client_http.arkiv.watch_entity_created(
        callback, from_block="latest"
    )
    filter2 = arkiv_client_http.arkiv.watch_entity_created(
        callback, from_block="latest"
    )

    def callback(event: CreateEvent, tx_hash: TxHash) -> None:
        pass

    filter1 = arkiv_client_http.arkiv.watch_entity_created(
        callback, from_block="latest"
    )
    filter2 = arkiv_client_http.arkiv.watch_entity_created(
        callback, from_block="latest"
    )

    # Manually uninstall one filter
    filter1.uninstall()
    assert not filter1.is_running

    # Cleanup should handle already-stopped filters gracefully
    arkiv_client_http.arkiv.cleanup_filters()

    assert not filter1.is_running
    assert not filter2.is_running
    assert len(arkiv_client_http.arkiv.active_filters) == 0
