"""Tests for provider builder functionality."""

import pytest
from web3.providers import AsyncHTTPProvider, HTTPProvider, WebSocketProvider
from web3.providers.async_base import AsyncBaseProvider
from web3.providers.base import BaseProvider

from arkiv.node import ArkivNode
from arkiv.provider import (
    DEFAULT_PORT,
    HTTP,
    KAOLIN,
    LOCALHOST,
    NETWORK_URL,
    WS,
    ProviderBuilder,
    TransportType,
)


def get_expected_default_url(transport: TransportType, port: int = DEFAULT_PORT) -> str:
    """Helper to get the default localhost URL with port."""
    url = NETWORK_URL[LOCALHOST][transport]
    url += f":{port}"
    return url


def get_expected_kaolin_url(transport: TransportType) -> str:
    """Helper to get the default Kaolin URL with port."""
    url = NETWORK_URL[KAOLIN][transport]
    return url


def assert_provider(
    provider: BaseProvider,
    expected_class: type[BaseProvider],
    expected_url: str,
    label: str,
) -> None:
    """Helper to assert provider against expected properties."""
    assert isinstance(provider, expected_class), (
        f"{label}: Expected provider type {expected_class.__name__}, "
        f"got {type(provider).__name__}"
    )
    assert provider.endpoint_uri == expected_url, (
        f"{label}: Expected endpoint URI '{expected_url}', "
        f"got '{provider.endpoint_uri}'"
    )


class TestProviderBuilderDefaults:
    """Test default behavior of ProviderBuilder."""

    def test_provider_default_initialization(self) -> None:
        """Test that builder initializes with localhost HTTP as defaults."""
        provider = ProviderBuilder().build()
        assert_provider(
            provider,
            HTTPProvider,
            get_expected_default_url(HTTP),
            "test_provider_default_initialization",
        )

    def test_provider_default_network_is_localhost(self) -> None:
        """Test that default network is localhost."""
        builder = ProviderBuilder()
        assert builder._network == LOCALHOST

    def test_provider_default_transport_is_http(self) -> None:
        """Test that default transport is HTTP."""
        builder = ProviderBuilder()
        assert builder._transport == HTTP


class TestProviderBuilderLocalhost:
    """Test localhost network configuration."""

    def test_provider_localhost_default_defaults(self) -> None:
        """Test localhost defaults to HTTP transport."""
        provider = ProviderBuilder().localhost().build()
        assert_provider(
            provider,
            HTTPProvider,
            get_expected_default_url(HTTP),
            "test_provider_localhost_default_defaults",
        )

    def test_provider_localhost_default_port_http(self) -> None:
        """Test localhost with default port and HTTP."""
        provider = ProviderBuilder().localhost().http().build()
        assert_provider(
            provider,
            HTTPProvider,
            get_expected_default_url(HTTP),
            "test_provider_localhost_default_port_http",
        )
        assert provider.endpoint_uri.startswith("http://")

    def test_provider_localhost_default_port_ws(self) -> None:
        """Test localhost with default port and WebSocket."""
        provider = ProviderBuilder().localhost().ws().build()
        assert_provider(
            provider,
            WebSocketProvider,
            get_expected_default_url(WS),
            "test_provider_localhost_default_port_ws",
        )
        assert provider.endpoint_uri.startswith("ws://")

    def test_provider_localhost_custom_port_http(self) -> None:
        """Test localhost with custom port and HTTP."""
        custom_port = 9000
        provider = ProviderBuilder().localhost(custom_port).http().build()
        assert_provider(
            provider,
            HTTPProvider,
            get_expected_default_url(HTTP, custom_port),
            "test_provider_localhost_custom_port_http",
        )

    def test_provider_localhost_custom_port_ws(self) -> None:
        """Test localhost with custom port and WebSocket."""
        custom_port = 9545
        provider = ProviderBuilder().localhost(custom_port).ws().build()
        assert_provider(
            provider,
            WebSocketProvider,
            get_expected_default_url(WS, custom_port),
            "test_provider_localhost_custom_port_ws",
        )


class TestProviderBuilderKaolin:
    """Test Kaolin network configuration."""

    def test_provider_kaolin_defaults(self) -> None:
        """Test Kaolin with HTTP transport."""
        provider = ProviderBuilder().kaolin().build()
        assert_provider(
            provider,
            HTTPProvider,
            get_expected_kaolin_url(HTTP),
            "test_provider_kaolin_defaults",
        )

    def test_provider_kaolin_http(self) -> None:
        """Test Kaolin with HTTP transport."""
        provider = ProviderBuilder().kaolin().http().build()
        assert_provider(
            provider,
            HTTPProvider,
            get_expected_kaolin_url(HTTP),
            "test_provider_kaolin_http",
        )
        assert provider.endpoint_uri.startswith("https://")

    def test_provider_kaolin_ws(self) -> None:
        """Test Kaolin with WebSocket transport."""
        provider = ProviderBuilder().kaolin().ws().build()
        assert_provider(
            provider,
            WebSocketProvider,
            get_expected_kaolin_url(WS),
            "test_provider_kaolin_ws",
        )
        assert provider.endpoint_uri.startswith("wss://")

    def test_provider_kaolin_clears_port(self) -> None:
        """Test that kaolin() clears any previously set port."""
        provider = ProviderBuilder().localhost(9000).kaolin().build()
        # Should use kaolin URL, not localhost with port
        assert_provider(
            provider,
            HTTPProvider,
            get_expected_kaolin_url(HTTP),
            "test_provider_kaolin_clears_port",
        )


class TestProviderBuilderCustom:
    """Test custom URL configuration."""

    def test_provider_custom_http_url(self) -> None:
        """Test custom HTTP URL."""
        custom_url = "https://my-custom-rpc.io"
        provider = ProviderBuilder().custom(custom_url).build()
        assert_provider(
            provider,
            HTTPProvider,
            custom_url,
            "test_provider_custom_http_url",
        )

    def test_provider_custom_ws_url(self) -> None:
        """Test custom WebSocket URL."""
        custom_url = "wss://my-custom-rpc.io"
        provider = ProviderBuilder().custom(custom_url).ws().build()
        assert_provider(
            provider,
            WebSocketProvider,
            custom_url,
            "test_provider_custom_ws_url",
        )

    def test_provider_custom_url_overrides_network(self) -> None:
        """Test that custom URL overrides previously set network."""
        custom_url = "https://override.io"
        provider = ProviderBuilder().localhost().custom(custom_url).build()
        assert_provider(
            provider,
            HTTPProvider,
            custom_url,
            "test_provider_custom_url_overrides_network",
        )

    def test_provider_custom_clears_port(self) -> None:
        """Test that custom() clears any previously set port."""
        custom_url = "https://my-rpc.io"
        builder = ProviderBuilder().localhost(9000).custom(custom_url)

        assert builder._port is None

    def test_provider_custom_clears_network(self) -> None:
        """Test that custom() clears network."""
        builder = ProviderBuilder().kaolin().custom("https://my-rpc.io")

        assert builder._network is None


class TestProviderBuilderNode:
    """Test ArkivNode integration."""

    def test_provider_node_with_existing_node(self) -> None:
        """Test node() with an existing ArkivNode instance."""
        with ArkivNode() as node:
            provider = ProviderBuilder().node(node).build()
            assert_provider(
                provider,
                HTTPProvider,
                node.http_url,
                "test_provider_node_with_existing_node",
            )

    def test_provider_node_auto_creates_node(self) -> None:
        """Test node() auto-creates and starts a new ArkivNode when None is passed."""
        provider = ProviderBuilder().node().build()
        assert isinstance(provider, HTTPProvider)
        # URL should match the ArkivNode default format
        assert provider.endpoint_uri.startswith("http://")

    def test_provider_node_auto_starts_node(self) -> None:
        """Test node() auto-starts a node that isn't running."""
        node = ArkivNode()
        assert not node.is_running

        provider = ProviderBuilder().node(node).build()
        assert node.is_running
        assert isinstance(provider, HTTPProvider)
        assert provider.endpoint_uri == node.http_url

        # Cleanup
        node.stop()

    def test_provider_node_with_websocket(self) -> None:
        """Test node() can be combined with ws() transport."""
        with ArkivNode() as node:
            provider = ProviderBuilder().node(node).ws().build()
            # Should use the node's WebSocket URL
            assert isinstance(provider, WebSocketProvider)
            assert provider.endpoint_uri == node.ws_url

    def test_provider_node_sets_correct_state(self) -> None:
        """Test node() sets correct internal state."""
        with ArkivNode() as node:
            builder = ProviderBuilder().node(node)

            assert builder._node is node
            assert builder._url is None  # URL determined in build()
            assert builder._network is None
            assert builder._port is None


class TestProviderBuilderTransportSwitching:
    """Test switching between transports."""

    def test_switch_from_http_to_ws(self) -> None:
        """Test switching from HTTP to WebSocket."""
        provider = ProviderBuilder().localhost().http().ws().build()
        assert_provider(
            provider,
            WebSocketProvider,
            get_expected_default_url(WS),
            "test_switch_from_http_to_ws",
        )

    def test_switch_from_ws_to_http(self) -> None:
        """Test switching from WebSocket to HTTP."""
        provider = ProviderBuilder().localhost().ws().http().build()
        assert_provider(
            provider,
            HTTPProvider,
            get_expected_default_url(HTTP),
            "test_switch_from_ws_to_http",
        )


class TestProviderBuilderErrorHandling:
    """Test error handling and validation."""

    def test_port_on_non_localhost_raises_error(self) -> None:
        """Test that setting port for non-localhost network raises error."""
        # This is tricky since port is only set by localhost()
        # But we can test the internal logic by manipulating state
        builder = ProviderBuilder()
        builder._network = KAOLIN
        builder._port = 9000

        with pytest.raises(ValueError, match="Port can only be set for localhost"):
            builder.build()

    def test_unknown_network_raises_error(self) -> None:
        """Test that unknown network raises error."""
        builder = ProviderBuilder()
        builder._network = "unknown_network"

        with pytest.raises(ValueError, match="Unknown network"):
            builder.build()

    def test_transport_not_available_raises_error(self) -> None:
        """Test appropriate error when transport isn't available."""
        # All networks currently support both transports, so we need to
        # manipulate the network URLs to test this
        builder = ProviderBuilder()
        builder._network = LOCALHOST
        builder._transport = "invalid"  # type: ignore[assignment]

        with pytest.raises(ValueError, match=r"Transport .* is not available"):
            builder.build()


class TestProviderBuilderStateMangement:
    """Test internal state management."""

    def test_localhost_sets_correct_state(self) -> None:
        """Test localhost() sets correct internal state."""
        builder = ProviderBuilder().localhost(9000)

        assert builder._network == LOCALHOST
        assert builder._port == 9000
        assert builder._url is None

    def test_kaolin_sets_correct_state(self) -> None:
        """Test kaolin() sets correct internal state."""
        builder = ProviderBuilder().kaolin()

        assert builder._network == KAOLIN
        assert builder._url is None
        assert builder._port is None

    def test_provider_custom_sets_correct_state(self) -> None:
        """Test custom() sets correct internal state."""
        custom_url = "https://test.io"
        builder = ProviderBuilder().custom(custom_url)

        assert builder._network is None
        assert builder._url == custom_url
        assert builder._port is None

    def test_http_sets_correct_state(self) -> None:
        """Test http() sets correct transport."""
        builder = ProviderBuilder().ws().http()

        assert builder._transport == HTTP

    def test_ws_sets_correct_state(self) -> None:
        """Test ws() sets correct transport."""
        builder = ProviderBuilder().http().ws()

        assert builder._transport == WS


class TestProviderBuilderAsyncMode:
    """Test async mode functionality."""

    def test_async_mode_sets_correct_state_for_default(self) -> None:
        """Test async_mode() sets internal flag."""
        builder = ProviderBuilder().async_mode()

        assert builder._is_async is True

    def test_async_mode_sets_correct_state_for_false(self) -> None:
        """Test async_mode() sets internal flag."""
        builder = ProviderBuilder().async_mode(False)

        assert builder._is_async is False

    def test_default_is_sync_mode(self) -> None:
        """Test default mode is sync (not async)."""
        builder = ProviderBuilder()

        assert builder._is_async is False

    def test_async_mode_with_http_creates_async_http_provider(self) -> None:
        """Test async_mode() with HTTP creates AsyncHTTPProvider."""
        provider = ProviderBuilder().localhost().async_mode().build()

        assert isinstance(provider, AsyncHTTPProvider)
        assert isinstance(provider, AsyncBaseProvider)
        assert provider.endpoint_uri == get_expected_default_url(HTTP)

    def test_async_mode_with_ws_creates_websocket_provider(self) -> None:
        """Test async_mode() with WebSocket creates WebSocketProvider (always async)."""
        provider = ProviderBuilder().localhost().ws().async_mode().build()

        assert isinstance(provider, WebSocketProvider)
        assert isinstance(provider, AsyncBaseProvider)
        assert provider.endpoint_uri == get_expected_default_url(WS)

    def test_sync_mode_with_http_creates_http_provider(self) -> None:
        """Test default (sync) mode with HTTP creates HTTPProvider."""
        provider = ProviderBuilder().localhost().build()

        assert isinstance(provider, HTTPProvider)
        assert isinstance(provider, BaseProvider)
        assert not isinstance(provider, AsyncBaseProvider)
        assert provider.endpoint_uri == get_expected_default_url(HTTP)

    def test_sync_mode_with_ws_creates_websocket_provider(self) -> None:
        """Test sync mode with WebSocket still creates WebSocketProvider (always async)."""
        provider = ProviderBuilder().localhost().ws().build()

        # WebSocketProvider is always async, even without async_mode()
        assert isinstance(provider, WebSocketProvider)
        assert isinstance(provider, AsyncBaseProvider)
        assert provider.endpoint_uri == get_expected_default_url(WS)

    def test_async_mode_with_kaolin_http(self) -> None:
        """Test async_mode() with Kaolin HTTP."""
        provider = ProviderBuilder().kaolin().async_mode().build()

        assert isinstance(provider, AsyncHTTPProvider)
        assert provider.endpoint_uri == get_expected_kaolin_url(HTTP)

    def test_async_mode_with_kaolin_ws(self) -> None:
        """Test async_mode() with Kaolin WebSocket."""
        provider = ProviderBuilder().kaolin().ws().async_mode().build()

        assert isinstance(provider, WebSocketProvider)
        assert provider.endpoint_uri == get_expected_kaolin_url(WS)

    def test_async_mode_with_custom_url(self) -> None:
        """Test async_mode() with custom URL."""
        custom_url = "https://my-async-rpc.io"
        provider = ProviderBuilder().custom(custom_url).async_mode().build()

        assert isinstance(provider, AsyncHTTPProvider)
        assert provider.endpoint_uri == custom_url

    def test_async_mode_chaining(self) -> None:
        """Test async_mode() can be chained in different positions."""
        # async_mode() before transport
        provider1 = ProviderBuilder().localhost().async_mode().http().build()
        assert isinstance(provider1, AsyncHTTPProvider)

        # async_mode() after transport
        provider2 = ProviderBuilder().localhost().http().async_mode().build()
        assert isinstance(provider2, AsyncHTTPProvider)

        # async_mode() in middle of chain
        provider3 = ProviderBuilder().async_mode().localhost().http().build()
        assert isinstance(provider3, AsyncHTTPProvider)

    def test_async_mode_with_node(self) -> None:
        """Test async_mode() works with node() configuration."""
        with ArkivNode() as node:
            # Async HTTP
            provider_http = ProviderBuilder().node(node).async_mode().build()
            assert isinstance(provider_http, AsyncHTTPProvider)
            assert provider_http.endpoint_uri == node.http_url

            # Async WebSocket
            provider_ws = ProviderBuilder().node(node).ws().async_mode().build()
            assert isinstance(provider_ws, WebSocketProvider)
            assert provider_ws.endpoint_uri == node.ws_url

    def test_async_mode_return_type_attribute(self) -> None:
        """Test that async providers are correctly typed."""
        # This test mainly validates type attributes work correctly
        sync_provider: BaseProvider = ProviderBuilder().localhost().build()
        async_provider: AsyncBaseProvider = (
            ProviderBuilder().localhost().async_mode().build()
        )

        # Runtime validation
        assert isinstance(sync_provider, BaseProvider)
        assert isinstance(async_provider, AsyncBaseProvider)
