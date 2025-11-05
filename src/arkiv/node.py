"""
Local Arkiv node for development and testing.

Provides containerized Arkiv node management for quick prototyping and testing.
Requires testcontainers to be installed.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from .account import NamedAccount

if TYPE_CHECKING:
    from testcontainers.core.container import DockerContainer

logger = logging.getLogger(__name__)


class ArkivNode:
    """
    Arkiv node for development and testing - supports both containerized and external nodes.

    This class provides two modes of operation:

    1. **Containerized Node (default)**: Automatically manages a local Docker container
       running an Arkiv node for quick prototyping and testing.

    2. **External Node**: Connects to an existing external Arkiv node (e.g., testnet,
       mainnet) by providing HTTP and WebSocket URLs.

    Note:
        Most users don't need to use ArkivNode directly. The Arkiv client automatically
        creates and manages a node when instantiated without a provider:

            >>> from arkiv import Arkiv
            >>> from arkiv.node import ArkivNode
            >>> with Arkiv() as client:
            ...     assert client.is_connected()
            ...     node: ArkivNode = client.node
            ...     # do work

    Containerized Mode Examples:
        Explicit node management:
            >>> from arkiv import Arkiv
            >>> from arkiv.node import ArkivNode
            >>> from arkiv.provider import ProviderBuilder
            >>> with ArkivNode() as node:
            ...     provider = ProviderBuilder().node(node).build()
            ...     arkiv = Arkiv(provider)
            ...     assert arkiv.is_connected()

    External Node Examples:
        Connect to external network (e.g., testnet/mainnet):
            >>> from arkiv import Arkiv
            >>> from arkiv.node import ArkivNode
            >>> from arkiv.provider import ProviderBuilder
            >>> with ArkivNode(http_url="...", ws_url="...") as node:
            ...     provider = ProviderBuilder().node(node).build()
            ...     arkiv = Arkiv(provider)
            ...     # Use arkiv...
            ... # No cleanup - external node remains running

    Advanced Use Cases:
        - Custom Docker images or ports for containerized nodes
        - Sharing a single node across multiple test fixtures
        - Direct access to container for CLI commands (containerized only)
        - Using nodes in pytest fixtures (see tests/conftest.py)

    Attributes:
        - Containerized nodes require Docker and testcontainers: `pip install arkiv-sdk[dev]`
        - External nodes cannot be started, stopped, or have accounts funded via the SDK
        - External node accounts must be pre-funded through external means
        - Context manager works safely with both modes (no-op for external nodes)
    """

    DEFAULT_IMAGE = "golemnetwork/golembase-op-geth:latest"
    DEFAULT_HTTP_PORT = 8545
    DEFAULT_WS_PORT = 8546

    def __init__(
        self,
        *,
        image: str | None = None,
        http_port: int | None = None,
        ws_port: int | None = None,
        http_url: str | None = None,
        ws_url: str | None = None,
    ) -> None:
        """
        Initialize the Arkiv node.

        Args:
            image: Docker image to use (default: golemnetwork/golembase-op-geth:latest)
            http_port: Internal HTTP port (default: 8545)
            ws_port: Internal WebSocket port (default: 8546)
            http_url: External HTTP RPC URL (for external nodes, disables container)
            ws_url: External WebSocket RPC URL (for external nodes, disables container)

        Raises:
            ImportError: If testcontainers is not installed (only for containerized nodes)
            ValueError: If only one of http_url/ws_url is provided
        """
        # Initialize common attributes first
        self._container: DockerContainer | None = None
        self._http_url: str = ""
        self._ws_url: str = ""
        self._is_running: bool = False
        self._is_external: bool = False

        # Check if this is an external node configuration
        if http_url or ws_url:
            if not (http_url and ws_url):
                raise ValueError(
                    "Both http_url and ws_url must be provided for external nodes"
                )
            # External node configuration - no container needed
            self._image = ""
            self._http_port = 0
            self._ws_port = 0
            self._http_url = http_url
            self._ws_url = ws_url
            self._is_running = True  # External nodes are always "running"
            self._is_external = True
            return

        # Containerized node configuration
        try:
            import testcontainers  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "ArkivNode requires testcontainers for containerized nodes. "
                "Install with: pip install 'arkiv-sdk[dev]' or pip install testcontainers"
            ) from e

        self._image = image or self.DEFAULT_IMAGE
        self._http_port = http_port or self.DEFAULT_HTTP_PORT
        self._ws_port = ws_port or self.DEFAULT_WS_PORT

    @property
    def http_url(self) -> str:
        """
        Returns the HTTP RPC endpoint URL.

        Raises:
            RuntimeError: If node is not running (for containerized nodes only)
        """
        if not self._is_running:
            raise RuntimeError(
                "Node is not running. Call start() first or use context manager."
            )
        return self._http_url

    @property
    def ws_url(self) -> str:
        """
        Returns the WebSocket RPC endpoint URL.

        Raises:
            RuntimeError: If node is not running (for containerized nodes only)
        """
        if not self._is_running:
            raise RuntimeError(
                "Node is not running. Call start() first or use context manager."
            )
        return self._ws_url

    @property
    def http_port(self) -> int:
        """
        Returns the mapped HTTP port number.

        Raises:
            RuntimeError: If node is not running or is an external node
        """
        if self._is_external:
            raise RuntimeError("External nodes do not expose port information")
        if not self._is_running or not self._container:
            raise RuntimeError(
                "Node is not running. Call start() first or use context manager."
            )
        return int(self._container.get_exposed_port(self._http_port))

    @property
    def ws_port(self) -> int:
        """
        Returns the mapped WebSocket port number.

        Raises:
            RuntimeError: If node is not running or is an external node
        """
        if self._is_external:
            raise RuntimeError("External nodes do not expose port information")
        if not self._is_running or not self._container:
            raise RuntimeError(
                "Node is not running. Call start() first or use context manager."
            )
        return int(self._container.get_exposed_port(self._ws_port))

    @property
    def container(self) -> DockerContainer:
        """
        The underlying Docker container.

        Returns:
            The testcontainers DockerContainer instance

        Raises:
            RuntimeError: If node is an external node or not running
        """
        if self._is_external:
            raise RuntimeError("External nodes do not have containers")
        if not self._container:
            raise RuntimeError(
                "Container not available. Call start() first or use context manager."
            )
        return self._container

    @property
    def is_external(self) -> bool:
        """
        Check if this node is configured as an external node.

        Returns:
            True if the node is external, False if containerized
        """
        return self._is_external

    @property
    def is_running(self) -> bool:
        """
        Check if the node is currently running.

        Returns:
            True if the node is running, False otherwise
        """
        return self._is_running

    def start(self) -> None:
        """
        Start the Arkiv node container.

        Starts the Docker container, waits for services to be ready,
        and sets up HTTP and WebSocket endpoints.

        Raises:
            ImportError: If testcontainers is not installed
            RuntimeError: If called on an external node

        Note:
            This method waits for both HTTP and WebSocket endpoints to be ready
            before returning, which may take several seconds.
            When the node is already running, this is a no-op.
            External nodes cannot be started.
        """
        # Check if this is an external node
        if self._is_external:
            raise RuntimeError(
                "Cannot start external node - it is already configured and running"
            )

        # Immediately return if already running
        if self._is_running:
            logger.debug("Node is already running, nothing to start")
            return None

        from testcontainers.core.container import DockerContainer
        from testcontainers.core.wait_strategies import HttpWaitStrategy

        logger.info(f"Starting Arkiv node from image: {self._image}")

        # Create container
        container = (
            DockerContainer(self._image)
            .with_exposed_ports(self._http_port, self._ws_port)
            .with_command(self._get_command())
        )

        # Start container
        container.start()
        self._container = container

        # Get connection details
        host = container.get_container_host_ip()
        self._http_url = f"http://{host}:{container.get_exposed_port(self._http_port)}"
        self._ws_url = f"ws://{host}:{container.get_exposed_port(self._ws_port)}"

        logger.info(f"Arkiv node endpoints: {self._http_url} | {self._ws_url}")

        # Wait for services to be ready
        container.waiting_for(HttpWaitStrategy(self._http_port).for_status_code(200))
        self._wait_for_websocket()

        self._is_running = True
        logger.info("Arkiv node is ready")

    def stop(self) -> None:
        """
        Stop and remove the Arkiv node container.

        Stops the Docker container and performs cleanup.
        If the node is not running, this is a no-op.

        Raises:
            RuntimeError: If called on an external node
        """
        # External nodes cannot be stopped
        if self._is_external:
            raise RuntimeError(
                "Cannot stop external node - external nodes are managed externally"
            )

        if not self._is_running:
            logger.debug("Node is not running, nothing to stop")
            return

        if self._container:
            logger.info("Stopping Arkiv node...")
            self._container.stop()
            self._container = None

        self._is_running = False
        self._http_url = ""
        self._ws_url = ""
        logger.info("Arkiv node stopped")

    def fund_account(self, account: NamedAccount) -> None:
        """
        Fund an account with test tokens.

        This method uses the golembase CLI inside the container to import
        the account's private key and fund the account with test tokens.

        Args:
            account: A NamedAccount to fund

        Raises:
            RuntimeError: If the node is not running, is an external node, or funding operations fail

        Examples:
            Fund a NamedAccount:
                >>> from arkiv.node import ArkivNode
                >>> from arkiv.account import NamedAccount
                >>> with ArkivNode() as node:
                ...     account = NamedAccount.create("alice")
                ...     node.fund_account(account)
        """
        if self._is_external:
            raise RuntimeError(
                f"Cannot fund account on external node - account {account.name} must be pre-funded via external means"
            )

        if not self.is_running:
            msg = "Node is not running. Call start() first."
            raise RuntimeError(msg)

        # Extract address and optionally import private key
        address = account.address
        # Import the account's private key into the container
        exit_code, output = self.container.exec(
            ["golembase", "account", "import", "--key", account.key.hex()]
        )
        if exit_code != 0:
            msg = f"Failed to import account: {output.decode()}"
            raise RuntimeError(msg)

        logger.info(f"Imported account {account.name} ({address})")

        # Fund the account
        exit_code, output = self.container.exec(["golembase", "account", "fund"])
        if exit_code != 0:
            msg = f"Failed to fund account: {output.decode()}"
            raise RuntimeError(msg)

        logger.info(f"Funded account {address}")

        # Check and log the balance
        exit_code, output = self.container.exec(
            ["golembase", "account", "balance", address]
        )
        if exit_code == 0:
            balance = output.decode().strip()
            logger.info(f"Account {address} balance: {balance}")
        else:
            logger.warning(f"Could not verify balance for {address}")

    def _get_command(self) -> str:
        """
        Get the command to run in the container.

        Returns:
            The geth command with appropriate flags for development mode
        """
        return (
            "--dev "
            "--http "
            "--http.api 'eth,web3,net,debug,golembase,arkiv' "
            f"--http.port {self._http_port} "
            "--http.addr '0.0.0.0' "
            "--http.corsdomain '*' "
            "--http.vhosts '*' "
            "--ws "
            f"--ws.port {self._ws_port} "
            "--ws.addr '0.0.0.0' "
            "--datadir '/geth_data'"
        )

    def _wait_for_websocket(self, timeout: int = 30) -> None:
        """
        Wait for WebSocket endpoint to be ready.

        Args:
            timeout: Maximum seconds to wait for WebSocket to be ready

        Raises:
            RuntimeError: If WebSocket is not ready within timeout
        """
        try:
            import websockets
        except ImportError:
            logger.warning(
                "websockets package not available, skipping WebSocket readiness check"
            )
            return

        async def check_connection() -> bool:
            try:
                async with websockets.connect(self._ws_url, open_timeout=2):
                    return True
            except Exception:
                return False

        for attempt in range(timeout):
            try:
                if asyncio.run(check_connection()):
                    logger.info(f"WebSocket ready (attempt {attempt + 1})")
                    return
            except Exception as e:
                logger.debug(f"WebSocket check attempt {attempt + 1} failed: {e}")

            time.sleep(1)

        raise RuntimeError(
            f"WebSocket not ready after {timeout} seconds: {self._ws_url}"
        )

    def __enter__(self) -> ArkivNode:
        """
        Context manager entry - start the node.

        For external nodes, this is a no-op (already running).
        For containerized nodes, this starts the container.

        Returns:
            Self for use in with statement

        Example:
            >>> with ArkivNode() as node:
            ...     print(node.http_url)
        """
        if not self._is_external:
            self.start()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """
        Context manager exit - stop and cleanup the node.

        For external nodes, this is a no-op (managed externally).
        For containerized nodes, this stops the container.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        if not self._is_external:
            self.stop()

    def __repr__(self) -> str:
        """
        String representation of the node.

        Returns:
            A string describing the node's state
        """
        if self._is_running:
            return f"ArkivNode(running=True, http={self._http_url}, ws={self._ws_url})"

        return f"ArkivNode(running=False, image={self._image})"
