"""Provider builder for creating Web3 providers with Arkiv presets."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, cast

from web3.providers import AsyncHTTPProvider, HTTPProvider, WebSocketProvider
from web3.providers.async_base import AsyncBaseProvider
from web3.providers.base import BaseProvider

if TYPE_CHECKING:
    from .node import ArkivNode

# Networks
LOCALHOST = "localhost"
KAOLIN = "kaolin"
NETWORK_DEFAULT = LOCALHOST

# Ports
DEFAULT_PORT = 8545

# Transport types
HTTP = "http"
WS = "ws"
TRANSPORT_DEFAULT = HTTP

NETWORK_URL = {
    LOCALHOST: {
        HTTP: "http://127.0.0.1",  # Port will be appended in build()
        WS: "ws://127.0.0.1",  # Port will be appended in build()
    },
    KAOLIN: {
        HTTP: "https://kaolin.hoodi.arkiv.network/rpc",
        WS: "wss://kaolin.hoodi.arkiv.network/rpc/ws",
    },
}

TransportType = Literal["http", "ws"]

logger = logging.getLogger(__name__)


class ProviderBuilder:
    """
    Fluent builder for Web3 providers with Arkiv presets.

    Examples:
      - ProviderBuilder().localhost().build()                 # http://127.0.0.1:8545 (HTTPProvider)
      - ProviderBuilder().localhost(9000).ws().build()        # ws://127.0.0.1:9000 (WebSocketProvider, async)
      - ProviderBuilder().localhost().async_mode().build()    # http://127.0.0.1:8545 (AsyncHTTPProvider)
      - ProviderBuilder().kaolin().build()                    # https://kaolin.hoodi.arkiv.network/rpc
      - ProviderBuilder().custom("https://my-rpc.io").build() # https://my-rpc.io
      - ProviderBuilder().node().build()                      # Auto-creates and starts ArkivNode
      - ProviderBuilder().node(my_node).ws().build()          # Use existing node with WebSocket (async)

    Note:
      For best practice, call async_mode() at the end of your builder chain, just before build():
        >>> ProviderBuilder().localhost().http().async_mode().build()

    Defaults:
      - Transport: HTTP (sync HTTPProvider)
      - Network: localhost:8545
      - Async mode: False (sync providers)

      WebSocket transport (ws()) always returns async providers (AsyncBaseProvider),
      regardless of async_mode() setting, as WebSocketProvider is inherently async.
    """

    def __init__(self) -> None:
        """Initialize the provider builder."""
        self._network: str | None = NETWORK_DEFAULT
        self._transport: TransportType = cast(TransportType, TRANSPORT_DEFAULT)
        self._port: int | None = DEFAULT_PORT  # Set default port for localhost
        self._url: str | None = None
        self._node: ArkivNode | None = None
        self._is_async: bool = False  # Default to sync providers

    def localhost(self, port: int | None = None) -> ProviderBuilder:
        """
        Configure for localhost development node.

        Args:
            port: Port number for the local node (default: 8545)

        Returns:
            Self for method chaining
        """
        self._network = LOCALHOST
        self._port = port if port is not None else DEFAULT_PORT
        self._url = None
        return self

    def kaolin(self) -> ProviderBuilder:
        """
        Configure for Kaolin testnet.

        Returns:
            Self for method chaining
        """
        self._network = KAOLIN
        self._url = None
        self._port = None
        return self

    def custom(self, url: str) -> ProviderBuilder:
        """
        Configure with custom RPC URL.

        Args:
            url: Custom RPC endpoint URL

        Returns:
            Self for method chaining
        """
        self._network = None
        self._url = url
        self._port = None
        return self

    def node(self, arkiv_node: ArkivNode | None = None) -> ProviderBuilder:
        """
        Configure for a local ArkivNode instance.

        If no node is provided, creates a new ArkivNode and starts it.
        The node will be auto-started if not already running.

        The URL will be selected based on the current transport setting (HTTP or WebSocket).
        You can chain .http() or .ws() to switch transports.

        Args:
            arkiv_node: ArkivNode instance to connect to, or None to create a new one

        Returns:
            Self for method chaining

        Examples:
            With existing node:
                >>> from arkiv.node import ArkivNode
                >>> node = ArkivNode()
                >>> provider = ProviderBuilder().node(node).build()

            Auto-create node:
                >>> provider = ProviderBuilder().node().build()

            Use WebSocket transport:
                >>> provider = ProviderBuilder().node(node).ws().build()
        """
        from .node import ArkivNode

        if arkiv_node is None:
            arkiv_node = ArkivNode()

        # Auto-start the node if not running
        if not arkiv_node.is_running:
            logger.debug("Auto-starting managed ArkivNode...")
            arkiv_node.start()

        # Store the node reference and clear network/port
        # The URL will be determined in build() based on transport
        self._node = arkiv_node
        self._network = None
        self._port = None
        self._url = None
        return self

    def http(self) -> ProviderBuilder:
        """
        Use HTTP transport.

        Returns:
            Self for method chaining
        """
        self._transport = cast(TransportType, HTTP)
        return self

    def ws(self) -> ProviderBuilder:
        """
        Use WebSocket transport.

        Note: WebSocket providers are always async (AsyncBaseProvider).

        Returns:
            Self for method chaining
        """
        self._transport = cast(TransportType, WS)
        return self

    def async_mode(self, async_provider: bool = True) -> ProviderBuilder:
        """
        Sets the async provider mode.

        When enabled, build() will return async-compatible providers:
        - HTTP transport → AsyncHTTPProvider
        - WebSocket transport → WebSocketProvider (inherently async)

        By default (async mode disabled), build() returns sync providers:
        - HTTP transport → HTTPProvider
        - WebSocket transport → WebSocketProvider (inherently async)

        Returns:
            Self for method chaining

        Examples:
            Async HTTP provider:
                >>> provider = ProviderBuilder().localhost().async_mode().build()
                >>> # Returns AsyncHTTPProvider

            Async WebSocket provider:
                >>> provider = ProviderBuilder().localhost().ws().async_mode().build()
                >>> # Returns WebSocketProvider (always async)

            Sync HTTP provider (default):
                >>> provider = ProviderBuilder().localhost().build() # or .async_mode(False)
                >>> # Returns HTTPProvider
        """
        self._is_async = async_provider
        return self

    def build(self) -> BaseProvider | AsyncBaseProvider:
        """
        Build and return the Web3 provider.

        Returns:
            Configured Web3 provider instance.

            By default (sync mode):
            - HTTP transport → HTTPProvider
            - WebSocket transport → WebSocketProvider (inherently async)

            With async_mode() enabled:
            - HTTP transport → AsyncHTTPProvider
            - WebSocket transport → WebSocketProvider (inherently async)

        Raises:
            ValueError: If no URL has been configured or if transport is not available
        """
        url: str
        # Top priority: Check if we have an ArkivNode reference
        if self._node is not None:
            # Get URL from node based on transport
            if self._transport == HTTP:
                url = self._node.http_url
            else:
                url = self._node.ws_url
        # 2nd priority: Custom URL overrides network constant
        elif self._url is not None:
            url = self._url
        # Fallback: Get URL from network constants
        elif self._network is not None:
            network_urls = NETWORK_URL.get(self._network)
            if network_urls is None:
                raise ValueError(f"Unknown network: {self._network}")

            url_from_network = network_urls.get(self._transport)
            if url_from_network is None:
                available = ", ".join(network_urls.keys())
                raise ValueError(
                    f"Transport '{self._transport}' is not available for network '{self._network}'. "
                    f"Available transports: {available}"
                )
            url = url_from_network

            if self._port is not None:
                # Append port only for localhost
                if self._network == LOCALHOST:
                    url = f"{url}:{self._port}"
                else:
                    raise ValueError("Port can only be set for localhost network")
        else:
            raise ValueError(
                "No URL or network configured. Use localhost(), kaolin(), or custom()."
            )

        # Build provider based on transport
        if self._transport == HTTP:
            # Consider async mode
            if self._is_async:
                return AsyncHTTPProvider(url)
            else:
                return HTTPProvider(url)
        # Web socket transport (always async)
        else:
            return cast(AsyncBaseProvider, WebSocketProvider(url))
