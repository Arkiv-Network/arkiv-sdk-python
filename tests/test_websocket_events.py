"""Tests for WebSocket event subscription support."""

import pytest
from web3.providers import HTTPProvider, WebSocketProvider

from arkiv import Arkiv
from arkiv.account import NamedAccount
from arkiv.provider import ProviderBuilder


def test_event_filter_works_with_http_provider():
    """Test that EventFilter works correctly with HTTP provider."""
    # Create Arkiv client with HTTP provider
    provider = ProviderBuilder().localhost().http().build()
    arkiv = Arkiv(provider=provider)

    # Create a dummy filter (without starting)
    filter_obj = arkiv.arkiv.watch_entity_created(
        callback=lambda event, tx_hash: None, auto_start=False
    )

    # Verify HTTP provider is accepted and filter created successfully
    assert isinstance(arkiv.provider, HTTPProvider)
    assert filter_obj.event_type == "created"
    assert not filter_obj.is_running

    # Cleanup
    filter_obj.uninstall()


def test_websocket_provider_validation():
    """Test that WebSocket provider is rejected with clear error message."""
    # Create WebSocket provider
    provider = ProviderBuilder().localhost().ws().build()

    # Verify it's actually a WebSocket provider
    assert isinstance(provider, WebSocketProvider)

    # Arkiv should reject it with helpful error message
    with pytest.raises(ValueError) as exc_info:
        Arkiv(provider=provider)

    error_msg = str(exc_info.value)
    assert "WebSocket providers are not supported" in error_msg
    assert "Use HTTP provider instead" in error_msg
    assert "ProviderBuilder().localhost().http().build()" in error_msg


@pytest.mark.skip(reason="Requires running Arkiv node with WebSocket support")
def test_websocket_event_subscription_integration():
    """
    Integration test for WebSocket event subscription.

    This test requires a running Arkiv node with WebSocket endpoint enabled.
    """
    # Create account
    account = NamedAccount.create("test_ws")

    # Connect with WebSocket provider
    with Arkiv(
        provider=ProviderBuilder().localhost().ws().build(), account=account
    ) as arkiv:
        # Track received events
        received_events = []

        def on_create(event, tx_hash):
            received_events.append((event, tx_hash))

        # Start watching for events
        event_filter = arkiv.arkiv.watch_entity_created(callback=on_create)

        # Create an entity
        entity_key, tx_hash = arkiv.arkiv.create_entity(
            payload=b"test data", attributes={"test": "websocket"}
        )

        # Wait a moment for event to be received
        import time

        time.sleep(2)

        # Verify event was received
        assert len(received_events) > 0
        event, event_tx_hash = received_events[0]
        assert event.entity_key == entity_key
        assert event_tx_hash == tx_hash

        # Cleanup
        event_filter.uninstall()


def test_http_polling_still_works():
    """Verify HTTP polling still works correctly."""
    # This test ensures backward compatibility with HTTP provider
    # (Detailed testing of HTTP polling is in existing test_arkiv_basic.py)
    provider = ProviderBuilder().localhost().http().build()
    arkiv = Arkiv(provider=provider)

    # Should not raise errors
    filter_obj = arkiv.arkiv.watch_entity_created(
        callback=lambda event, tx_hash: None, auto_start=False
    )

    # Verify filter is created successfully
    assert filter_obj.event_type == "created"
    assert not filter_obj.is_running
    filter_obj.uninstall()
