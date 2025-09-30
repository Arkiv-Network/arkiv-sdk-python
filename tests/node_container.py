"""
Container management for Arkiv test nodes.

Provides Docker container lifecycle management for blockchain testing.
"""

import asyncio
import logging
import time
from collections.abc import Generator

from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import HttpWaitStrategy

logger = logging.getLogger(__name__)


class ArkivTestContainer:
    """Manages Arkiv test container lifecycle."""

    IMAGE = "golemnetwork/golembase-op-geth:latest"
    HTTP_PORT = 8545
    WS_PORT = 8546

    def __init__(self) -> None:
        """Initialize container configuration."""
        self.container = self._create_container()
        self._http_url = ""
        self._ws_url = ""

    def _create_container(self) -> DockerContainer:
        """Create and configure the Docker container."""
        return (
            DockerContainer(self.IMAGE)
            .with_exposed_ports(self.HTTP_PORT, self.WS_PORT)
            .with_command(self._get_command())
        )

    def _get_command(self) -> str:
        """Get the command to run in the container."""
        return (
            "--dev "
            "--http "
            "--http.api 'eth,web3,net,debug,golembase' "
            f"--http.port {self.HTTP_PORT} "
            "--http.addr '0.0.0.0' "
            "--http.corsdomain '*' "
            "--http.vhosts '*' "
            "--ws "
            f"--ws.port {self.WS_PORT} "
            "--ws.addr '0.0.0.0' "
            "--datadir '/geth_data'"
        )

    def start(self) -> tuple[str, str]:
        """Start the container and return connection URLs."""
        logger.info("Starting containerized Arkiv node...")

        self.container.start()

        host = self.container.get_container_host_ip()
        self._http_url = (
            f"http://{host}:{self.container.get_exposed_port(self.HTTP_PORT)}"
        )
        self._ws_url = f"ws://{host}:{self.container.get_exposed_port(self.WS_PORT)}"

        logger.info(f"Arkiv Node endpoints: {self._http_url} | {self._ws_url}")

        # Wait for services to be ready
        self.container.waiting_for(
            HttpWaitStrategy(self.HTTP_PORT).for_status_code(200)
        )
        self._wait_for_websocket()

        logger.info("Arkiv Node is ready")
        return self._http_url, self._ws_url

    def stop(self) -> None:
        """Stop and cleanup the container."""
        if self.container:
            self.container.stop()
            logger.info("Container stopped")

    def get_connection_details(self) -> tuple[DockerContainer, str, str]:
        """Get container and connection details."""
        return self.container, self._http_url, self._ws_url

    def _wait_for_websocket(self, timeout: int = 30) -> None:
        """Wait for WebSocket endpoint to be ready."""
        try:
            import websockets
        except ImportError:
            logger.warning("Websockets not available, skipping WS check")
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
                logger.debug(f"WS check failed: {e}")

            time.sleep(1)

        raise RuntimeError(
            f"WebSocket not ready after {timeout} attempts: {self._ws_url}"
        )

    def __enter__(self) -> "ArkivTestContainer":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit."""
        self.stop()


def create_container_node() -> Generator[tuple[DockerContainer, str, str], None, None]:
    """Create and manage a containerized blockchain node."""
    with ArkivTestContainer() as container:
        yield container.get_connection_details()
