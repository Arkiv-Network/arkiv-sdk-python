"""
Pytest configuration and fixtures for blockchain testing.

Provides either external node connections (via env vars) or containerized test nodes.
"""

import logging
import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
from web3 import Web3

from arkiv import Arkiv, AsyncArkiv
from arkiv.account import NamedAccount
from arkiv.node import ArkivNode
from arkiv.provider import ProviderBuilder

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


# Load environment on import
_load_env_if_available()


@pytest.fixture(scope="session")
def arkiv_container() -> Generator[ArkivNode, None, None]:
    """
    Provide a containerized ArkivNode for testing.

    Creates and manages a local Docker-based Arkiv node.
    Use this fixture for tests that need container-specific features.
    """
    logger.info("Creating containerized test ArkivNode...")
    with ArkivNode() as node:
        logger.info(f"Test node ready at {node.http_url}")
        yield node


@pytest.fixture(scope="session")
def arkiv_testnet() -> ArkivNode:
    """
    Provide Kaolin testnet ArkivNode for testing.

    Always points to the Kaolin testnet.
    Use this fixture for tests that work with the public Kaolin testnet.
    """
    from arkiv.provider import HTTP, KAOLIN, NETWORK_URL, WS

    http_url = NETWORK_URL[KAOLIN][HTTP]
    ws_url = NETWORK_URL[KAOLIN][WS]

    logger.info(f"Using Kaolin testnet: {http_url}")
    return ArkivNode(http_url=http_url, ws_url=ws_url)


@pytest.fixture(scope="session")
def arkiv_node() -> Generator[ArkivNode, None, None]:
    """
    Provide an ArkivNode for testing.

    If RPC_URL and WS_URL are set in environment, creates an ArkivNode
    configured for the external node (no container management).
    Otherwise, creates and manages a local containerized node.
    Use this fixture for tests that work with either node type.
    """
    # Check for external node configuration
    rpc_url = os.getenv(RPC_URL_ENV)
    ws_url = os.getenv(WS_URL_ENV)

    if rpc_url and ws_url:
        logger.info(f"Using external node: {rpc_url}")
        # Create ArkivNode for external node (no container)
        node = ArkivNode(http_url=rpc_url, ws_url=ws_url)
        yield node
        # No cleanup needed for external nodes
        return

    # Fall back to containerized node
    logger.info("Creating containerized test ArkivNode...")
    with ArkivNode() as node:
        logger.info(f"Test node ready at {node.http_url}")
        yield node


@pytest.fixture(scope="session")
def arkiv_client_http(arkiv_node: ArkivNode, account_1: NamedAccount) -> Arkiv:
    """Return Arkiv client with funded account connected via HTTP."""
    # Fund the account using the node (only for local containerized nodes)
    if not arkiv_node.is_external:
        try:
            arkiv_node.fund_account(account_1)
        except RuntimeError as e:
            # Account may already be funded from previous tests
            if "account already exists" not in str(e):
                raise

    # Create provider and client
    provider = ProviderBuilder().node(arkiv_node).build()
    client = Arkiv(provider, account=account_1)

    assert client.is_connected(), f"Failed to connect to {provider.endpoint_uri}"  # type: ignore[attr-defined]
    logger.info(f"Arkiv client connected to {provider.endpoint_uri}")  # type: ignore[attr-defined]

    return client


@pytest.fixture(scope="session")
def web3_client_http(arkiv_node: ArkivNode) -> Web3:
    """Return Web3 client connected to HTTP endpoint."""
    provider = ProviderBuilder().node(arkiv_node).build()
    client = Web3(provider)

    assert client.is_connected(), f"Failed to connect to {provider.endpoint_uri}"  # type: ignore[attr-defined]
    logger.info(f"Web3 client connected to {provider.endpoint_uri}")  # type: ignore[attr-defined]

    return client


@pytest.fixture(scope="session")
def account_1(arkiv_node: ArkivNode) -> NamedAccount:
    """Provide the first (alice) account."""
    return create_account(1, ALICE)


@pytest.fixture(scope="session")
def account_2(arkiv_node: ArkivNode) -> NamedAccount:
    """Provide the second (bob) account."""
    account = create_account(2, BOB)

    # Fund the account using the node (only for local containerized nodes)
    if not arkiv_node.is_external:
        arkiv_node.fund_account(account)

    return account


@pytest.fixture
async def async_arkiv_client_http(
    arkiv_node: ArkivNode, account_1: NamedAccount
) -> AsyncGenerator[AsyncArkiv, None]:
    """Return AsyncArkiv client with funded account connected via HTTP.

    Note: This is function-scoped (unlike the sync arkiv_client_http which is session-scoped)
    because pytest-asyncio's event loop is function-scoped by default. Session-scoped async
    fixtures would require a session-scoped event loop, which can cause issues with cleanup
    and state management across tests.
    """
    # Fund the account using the node (only for local containerized nodes)
    if not arkiv_node.is_external:
        try:
            arkiv_node.fund_account(account_1)
        except RuntimeError as e:
            # Account may already be funded from previous tests
            if "account already exists" not in str(e):
                raise

    # Create async provider and client
    provider = ProviderBuilder().node(arkiv_node).async_mode().build()

    async with AsyncArkiv(provider, account=account_1) as client:
        assert await client.is_connected(), (
            f"Failed to connect to {provider.endpoint_uri}"  # type: ignore[attr-defined]
        )
        logger.info(f"AsyncArkiv client connected to {provider.endpoint_uri}")  # type: ignore[attr-defined]

        yield client

    # Cleanup happens automatically when exiting the async context manager
    logger.info("AsyncArkiv client closed")


@pytest.fixture(scope="session")
def provider(arkiv_node: ArkivNode):
    """Provide a Web3 provider for testing."""
    return ProviderBuilder().node(arkiv_node).build()


@pytest.fixture(scope="session")
def async_provider(arkiv_node: ArkivNode):
    """Provide a Web3 async provider for testing."""
    return ProviderBuilder().node(arkiv_node).async_mode().build()


@pytest.fixture(scope="session")
def unfunded_account() -> NamedAccount:
    """Provide an unfunded account (zero balance) for testing validation."""
    # Create a fresh account that has never been funded
    return create_account(999, "unfunded_test_account")
