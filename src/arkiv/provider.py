"""Provider builder for creating Web3 providers with Arkiv presets."""

from typing import Literal, cast

from web3.providers import HTTPProvider, WebSocketProvider
from web3.providers.base import BaseProvider

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


class ProviderBuilder:
    """
    Fluent builder for Web3 providers with Arkiv presets.

    Examples:
      - ProviderBuilder().localhost().build()                 # http://127.0.0.1:8545
      - ProviderBuilder().localhost(9000).ws().build()        # ws://127.0.0.1:9000
      - ProviderBuilder().kaolin().build()                    # https://kaolin.hoodi.arkiv.network/rpc
      - ProviderBuilder().custom("https://my-rpc.io").build() # https://my-rpc.io
    """

    def __init__(self) -> None:
        """Initialize the provider builder."""
        self._network: str | None = NETWORK_DEFAULT
        self._transport: TransportType = cast(TransportType, TRANSPORT_DEFAULT)
        self._port: int | None = DEFAULT_PORT  # Set default port for localhost
        self._url: str | None = None

    def localhost(self, port: int | None = None) -> "ProviderBuilder":
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

    def kaolin(self) -> "ProviderBuilder":
        """
        Configure for Kaolin testnet.

        Returns:
            Self for method chaining
        """
        self._network = KAOLIN
        self._url = None
        self._port = None
        return self

    def custom(self, url: str) -> "ProviderBuilder":
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

    def http(self) -> "ProviderBuilder":
        """
        Use HTTP transport.

        Returns:
            Self for method chaining
        """
        self._transport = cast(TransportType, HTTP)
        return self

    def ws(self) -> "ProviderBuilder":
        """
        Use WebSocket transport.

        Returns:
            Self for method chaining
        """
        self._transport = cast(TransportType, WS)
        return self

    def build(self) -> BaseProvider:
        """
        Build and return the Web3 provider.

        Returns:
            Configured Web3 provider instance.
            Uses HTTPProvider or WebSocketProvider based on specified transport (HTTP being default).

        Raises:
            ValueError: If no URL has been configured or if transport is not available
        """
        url: str
        # Custom URL overrides network constant
        if self._url is not None:
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

        if self._transport == HTTP:
            return HTTPProvider(url)
        else:
            return cast(BaseProvider, WebSocketProvider(url))
