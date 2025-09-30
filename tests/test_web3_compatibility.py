"""Consolidated Web3 functionality tests for both Web3 and Arkiv clients."""

import logging

import pytest
from web3 import Web3

from arkiv import Arkiv

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "client_fixture",
    ["web3_client_http", "arkiv_client_http"],
    ids=["web3", "arkiv"],
)
def test_client_connection(client_fixture: str, request: pytest.FixtureRequest) -> None:
    """Test that client is connected and responsive."""
    client: Web3 | Arkiv = request.getfixturevalue(client_fixture)
    assert client.is_connected(), "Client should be connected"
    logger.info(f"{client_fixture} connection verified")


@pytest.mark.parametrize(
    "client_fixture",
    ["web3_client_http", "arkiv_client_http"],
    ids=["web3", "arkiv"],
)
def test_client_chain_id(client_fixture: str, request: pytest.FixtureRequest) -> None:
    """Test retrieving chain ID from the node."""
    client: Web3 | Arkiv = request.getfixturevalue(client_fixture)
    chain_id = client.eth.chain_id
    assert isinstance(chain_id, int), "Chain ID should be an integer"
    assert chain_id > 0, "Chain ID should be positive"
    logger.info(f"{client_fixture} Chain ID: {chain_id}")


@pytest.mark.parametrize(
    "client_fixture",
    ["web3_client_http", "arkiv_client_http"],
    ids=["web3", "arkiv"],
)
def test_client_block_number(
    client_fixture: str, request: pytest.FixtureRequest
) -> None:
    """Test retrieving current block number."""
    client: Web3 | Arkiv = request.getfixturevalue(client_fixture)
    block_number = client.eth.block_number
    assert isinstance(block_number, int), "Block number should be an integer"
    assert block_number >= 0, "Block number should be non-negative"
    logger.info(f"{client_fixture} Block number: {block_number}")


@pytest.mark.parametrize(
    "client_fixture",
    ["web3_client_http", "arkiv_client_http"],
    ids=["web3", "arkiv"],
)
def test_client_get_block(client_fixture: str, request: pytest.FixtureRequest) -> None:
    """Test retrieving block information."""
    client: Web3 | Arkiv = request.getfixturevalue(client_fixture)
    latest_block = client.eth.get_block("latest")

    assert latest_block is not None, "Should retrieve latest block"
    assert "number" in latest_block, "Block should have number field"
    assert "hash" in latest_block, "Block should have hash field"
    assert "timestamp" in latest_block, "Block should have timestamp field"

    block_number = latest_block["number"]
    logger.info(f"{client_fixture} Latest block: {block_number}")


@pytest.mark.parametrize(
    "client_fixture",
    ["web3_client_http", "arkiv_client_http"],
    ids=["web3", "arkiv"],
)
def test_client_accounts(client_fixture: str, request: pytest.FixtureRequest) -> None:
    """Test retrieving available accounts."""
    client: Web3 | Arkiv = request.getfixturevalue(client_fixture)
    accounts = client.eth.accounts
    assert isinstance(accounts, list), "Accounts should be a list"
    logger.info(f"{client_fixture} Available accounts: {len(accounts)}")


@pytest.mark.parametrize(
    "client_fixture",
    ["web3_client_http", "arkiv_client_http"],
    ids=["web3", "arkiv"],
)
def test_client_gas_price(client_fixture: str, request: pytest.FixtureRequest) -> None:
    """Test retrieving current gas price."""
    client: Web3 | Arkiv = request.getfixturevalue(client_fixture)
    gas_price = client.eth.gas_price
    assert isinstance(gas_price, int), "Gas price should be an integer (wei)"
    assert gas_price >= 0, "Gas price should be non-negative"
    logger.info(f"{client_fixture} Gas price: {gas_price} wei")


@pytest.mark.parametrize(
    "client_fixture",
    ["web3_client_http", "arkiv_client_http"],
    ids=["web3", "arkiv"],
)
def test_client_net_version(
    client_fixture: str, request: pytest.FixtureRequest
) -> None:
    """Test retrieving network version."""
    client: Web3 | Arkiv = request.getfixturevalue(client_fixture)
    net_version = client.net.version
    assert isinstance(net_version, str), "Network version should be a string"
    assert len(net_version) > 0, "Network version should not be empty"
    logger.info(f"{client_fixture} Network version: {net_version}")


@pytest.mark.parametrize(
    "client_fixture",
    ["web3_client_http", "arkiv_client_http"],
    ids=["web3", "arkiv"],
)
def test_client_version(client_fixture: str, request: pytest.FixtureRequest) -> None:
    """Test retrieving client version information."""
    client: Web3 | Arkiv = request.getfixturevalue(client_fixture)
    client_version = client.client_version
    assert isinstance(client_version, str), "Client version should be a string"
    assert len(client_version) > 0, "Client version should not be empty"
    logger.info(f"{client_fixture} Client version: {client_version}")
