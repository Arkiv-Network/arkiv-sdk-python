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
    Local and fully functional Arkiv development node using Docker containers.

    Examples:
        Context manager (recommended):
            >>> from arkiv.node import ArkivNode
            >>> from arkiv import Arkiv
            >>> with ArkivNode() as node:
            ...     arkiv = Arkiv.from_node(node)
            ...     assert arkiv.is_connected()

        Quick prototyping:
            >>> node = ArkivNode()
            >>> arkiv = Arkiv.from_node(node)  # Starts automatically
            >>> # ... do work ...
            >>> node.stop()  # Don't forget cleanup

    Note:
        Requires Docker to be running and testcontainers package to be installed:
            pip install arkiv-sdk[dev]
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
        auto_start: bool = False,
    ) -> None:
        """
        Initialize the Arkiv node.

        Args:
            image: Docker image to use (default: golemnetwork/golembase-op-geth:latest)
            http_port: Internal HTTP port (default: 8545)
            ws_port: Internal WebSocket port (default: 8546)
            auto_start: Automatically start the node on initialization (default: False)

        Raises:
            ImportError: If testcontainers is not installed
        """
        try:
            import testcontainers  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "ArkivNode requires testcontainers. "
                "Install with: pip install 'arkiv-sdk[dev]' or pip install testcontainers"
            ) from e

        self._image = image or self.DEFAULT_IMAGE
        self._http_port = http_port or self.DEFAULT_HTTP_PORT
        self._ws_port = ws_port or self.DEFAULT_WS_PORT

        self._container: DockerContainer | None = None
        self._http_url: str = ""
        self._ws_url: str = ""
        self._is_running: bool = False

        if auto_start:
            self.start()

    @property
    def http_url(self) -> str:
        """
        Returns the HTTP RPC endpoint URL.

        Raises:
            RuntimeError: If node is not running
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
            RuntimeError: If node is not running
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
            RuntimeError: If node is not running
        """
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
            RuntimeError: If node is not running
        """
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
            RuntimeError: If node is not running
        """
        if not self._container:
            raise RuntimeError(
                "Container not available. Call start() first or use context manager."
            )
        return self._container

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

        Note:
            This method waits for both HTTP and WebSocket endpoints to be ready
            before returning, which may take several seconds.
            When the node is already running, this is a no-op.
        """
        # Immediately return if already running
        if self._is_running:
            logger.debug("Node is already running, nothing to start")
            return None

        from testcontainers.core.container import DockerContainer
        from testcontainers.core.wait_strategies import HttpWaitStrategy

        logger.info(f"Starting Arkiv node from image: {self._image}")

        # Create container
        self._container = (
            DockerContainer(self._image)
            .with_exposed_ports(self._http_port, self._ws_port)
            .with_command(self._get_command())
        )

        # Start container
        self._container.start()

        # Get connection details
        host = self._container.get_container_host_ip()
        self._http_url = (
            f"http://{host}:{self._container.get_exposed_port(self._http_port)}"
        )
        self._ws_url = f"ws://{host}:{self._container.get_exposed_port(self._ws_port)}"

        logger.info(f"Arkiv node endpoints: {self._http_url} | {self._ws_url}")

        # Wait for services to be ready
        self._container.waiting_for(
            HttpWaitStrategy(self._http_port).for_status_code(200)
        )
        self._wait_for_websocket()

        self._is_running = True
        logger.info("Arkiv node is ready")

    def stop(self) -> None:
        """
        Stop and remove the Arkiv node container.

        Stops the Docker container and performs cleanup.
        If the node is not running, this is a no-op.
        """
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
            RuntimeError: If the node is not running or funding operations fail

        Examples:
            Fund a NamedAccount:
                >>> from arkiv.node import ArkivNode
                >>> from arkiv.account import NamedAccount
                >>> with ArkivNode() as node:
                ...     account = NamedAccount.create("alice")
                ...     node.fund_account(account)
        """
        if not self.is_running():
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
            "--http.api 'eth,web3,net,debug,golembase' "
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

        Returns:
            Self for use in with statement

        Example:
            >>> with ArkivNode() as node:
            ...     print(node.http_url)
        """
        self.start()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """
        Context manager exit - stop and cleanup the node.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
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
