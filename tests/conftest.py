"""
Pytest configuration and fixtures for blockchain testing.

Provides either external node connections (via env vars) or containerized test nodes.
"""

import logging
import os
from collections.abc import Generator
from pathlib import Path

import pytest
from testcontainers.core.container import DockerContainer
from web3 import Web3
from web3.providers.base import BaseProvider

from arkiv import Arkiv
from arkiv.account import NamedAccount
from arkiv.provider import ProviderBuilder
from tests.node_container import create_container_node

from .utils import create_account

# Environment variable names for external node configuration
RPC_URL_ENV = "RPC_URL"
WS_URL_ENV = "WS_URL"

# Environment variable names for external wallet configuration
WALLET_FILE_ENV_PREFIX = "WALLET_FILE"
WALLET_PASSWORD_ENV_PREFIX = "WALLET_PASSWORD"

ALICE = "alice"
BOB = "bob"

logger = logging.getLogger(__name__)


def _load_env_if_available() -> None:
    """Load .env file if dotenv is available and file exists."""
    try:
        from dotenv import load_dotenv

        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
            logger.info("Loaded environment variables from .env")
    except ImportError:
        logger.debug("python-dotenv not available, using system environment only")


def check_and_get_web3(name: str, provider: BaseProvider) -> Web3:
    """Create and verify a Web3 client connection."""
    return verify_connection(name, Web3(provider))


def check_and_get_arkiv(
    name: str, provider: BaseProvider, account: NamedAccount | None = None
) -> Arkiv:
    """Create and verify an Arkiv client connection."""
    if account:
        return verify_connection(name, Arkiv(provider, account=account))
    else:
        return verify_connection(name, Arkiv(provider))


def verify_connection(name: str, client: Web3) -> Web3:
    """Verify Web3 client connection and return checked client."""
    assert client.is_connected(), (
        f"{name}: Failed to connect to {client.provider.endpoint_uri}"
    )  # type: ignore[attr-defined]
    logger.info(f"{name} client connected to {client.provider.endpoint_uri}")  # type: ignore[attr-defined]
    return client


# Load environment on import
_load_env_if_available()


@pytest.fixture(scope="session")
def arkiv_node() -> Generator[tuple[DockerContainer | None, str, str], None, None]:
    """
    Provide Arkiv node connection details.

    Returns:
        Tuple of (container, http_url, ws_url)
        - container is None for external nodes
    """
    # Try external node first
    rpc_url = os.getenv(RPC_URL_ENV)
    ws_url = os.getenv(WS_URL_ENV)

    if rpc_url and ws_url:
        logger.info(f"Using external node: {rpc_url}")
        yield None, rpc_url, ws_url
        return

    # Fall back to containerized node
    logger.info("Using containerized node")
    yield from create_container_node()


@pytest.fixture(scope="session")
def testcontainer_provider_http(
    arkiv_node: tuple[DockerContainer | None, str, str],
) -> BaseProvider:
    """Returns testcontainer HTTPProvider using the ProviderBuilder."""
    _, http_url, _ = arkiv_node
    return ProviderBuilder().custom(http_url).build()


@pytest.fixture(scope="session")
def testcontainer_provider_ws(
    arkiv_node: tuple[DockerContainer | None, str, str],
) -> BaseProvider:
    """Returns testcontainer WebSocketProvider using the ProviderBuilder."""
    _, _, ws_url = arkiv_node
    # Note: .ws() is to make transport explicit, it is not strictly necessary as the URL scheme is ws:// or wss://
    return ProviderBuilder().custom(ws_url).ws().build()


@pytest.fixture(scope="session")
def web3_client_http(testcontainer_provider_http: BaseProvider) -> Web3:
    """Return Web3 client connected to HTTP endpoint."""
    return check_and_get_web3("Web3 HTTP", testcontainer_provider_http)


@pytest.fixture(scope="session")
def arkiv_ro_client_http(testcontainer_provider_http: BaseProvider) -> Arkiv:
    """Return a read only Arkiv client connected to HTTP endpoint."""
    return check_and_get_arkiv("Arkiv HTTP (read only)", testcontainer_provider_http)


@pytest.fixture(scope="session")
def arkiv_client_http(
    testcontainer_provider_http: BaseProvider, account_1: NamedAccount
) -> Arkiv:
    """Return a read only Arkiv client connected to HTTP endpoint."""
    return check_and_get_arkiv(
        "Arkiv HTTP", testcontainer_provider_http, account=account_1
    )


@pytest.fixture(scope="session")
def account_1(arkiv_node: tuple[DockerContainer | None, str, str]) -> NamedAccount:
    """Provide the first (alice) account."""
    container, _, _ = arkiv_node
    return create_account(1, ALICE, container)


@pytest.fixture(scope="session")
def account_2(arkiv_node: tuple[DockerContainer | None, str, str]) -> NamedAccount:
    """Provide the second (bob) account."""
    container, _, _ = arkiv_node
    return create_account(2, BOB, container)
