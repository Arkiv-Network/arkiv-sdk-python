"""Tests for provider builder functionality."""

import pytest
from web3.providers import HTTPProvider, WebSocketProvider
from web3.providers.base import BaseProvider

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
