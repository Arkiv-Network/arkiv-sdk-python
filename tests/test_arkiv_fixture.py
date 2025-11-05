"""Tests for basic Arkiv client functionality and arkiv module availability."""

import logging

import pytest

from arkiv import Arkiv
from arkiv.account import NamedAccount
from arkiv.module import ArkivModule

logger = logging.getLogger(__name__)


def test_arkiv_client_extends_web3(arkiv_client_http: Arkiv) -> None:
    """Test that Arkiv client properly extends Web3 functionality."""
    # Should have all Web3 attributes
    assert hasattr(arkiv_client_http, "eth"), "Should have eth module"
    assert hasattr(arkiv_client_http, "net"), "Should have net module"
    assert hasattr(arkiv_client_http, "middleware_onion"), (
        "Should have middleware_onion"
    )
    assert hasattr(arkiv_client_http, "is_connected"), "Should have is_connected method"

    # Should be connected
    assert arkiv_client_http.is_connected(), "Should be connected to node"

    # Check arkiv atttributes
    assert hasattr(arkiv_client_http, "arkiv"), "Should have arkiv module"
    assert hasattr(arkiv_client_http, "switch_to"), "Should have switch_to method"

    logger.info("Arkiv client properly extends Web3")


def test_arkiv_client_has_arkiv_module(arkiv_client_http: Arkiv) -> None:
    """Test that Arkiv client has the arkiv module available."""
    assert hasattr(arkiv_client_http, "arkiv"), "Arkiv client should have arkiv module"

    arkiv_module = arkiv_client_http.arkiv
    assert arkiv_module is not None, "Arkiv module should not be None"
    assert isinstance(arkiv_module, ArkivModule), "Should be ArkivModule instance"

    # Test availability check
    is_available = arkiv_module.is_available()
    assert isinstance(is_available, bool), "is_available should return boolean"
    assert is_available is True, "Arkiv module should be available"

    logger.info("Arkiv module is available")


def test_arkiv_client_repr(arkiv_client_http: Arkiv) -> None:
    """Test Arkiv client string representation."""
    repr_str = repr(arkiv_client_http)
    assert isinstance(repr_str, str), "repr should return string"
    assert "Arkiv" in repr_str, "repr should contain 'Arkiv'"
    assert "connected=" in repr_str, "repr should show connection status"

    logger.info(f"Arkiv client repr: {repr_str}")


def test_arkiv_module_has_client_reference(arkiv_client_http: Arkiv) -> None:
    """Test that arkiv module has reference to parent client."""
    arkiv_module = arkiv_client_http.arkiv

    assert hasattr(arkiv_module, "client"), "Arkiv module should have client reference"
    assert arkiv_module.client is arkiv_client_http, (
        "Client reference should point to parent"
    )

    logger.info("Arkiv module has proper client reference")


def test_arkiv_accounts_are_funded(
    arkiv_client_http: Arkiv, account_1: NamedAccount, account_2: NamedAccount
) -> None:
    """Test that accounts are funded."""
    account_1_balance = arkiv_client_http.eth.get_balance(account_1.address)
    account_2_balance = arkiv_client_http.eth.get_balance(account_2.address)

    logger.info(f"account_1 ({account_1.name}) balance: {account_1_balance / 10**18}")
    logger.info(f"account_2 ({account_2.name}) balance: {account_2_balance / 10**18}")

    assert account_1_balance > 0, "Fixture account 1 should be funded"
    assert account_2_balance > 0, "Fixture account 2 should be funded"

    logger.info("Arkiv fixture accounts are funded (balances > 0)")


@pytest.mark.skip("Skipping ETH transfer not (yet) supported on db chains.")
def test_arkiv_transfer_eth_account(
    arkiv_client_http: Arkiv, account_1: NamedAccount, account_2: NamedAccount
) -> None:
    """Test that ETH (GLM) transfer works."""
    account_1_balance_before = arkiv_client_http.eth.get_balance(account_1.address)
    account_2_balance_before = arkiv_client_http.eth.get_balance(account_2.address)
    amount = 42

    arkiv_client_http.arkiv.transfer_eth(account_2, amount)

    account_1_balance_after = arkiv_client_http.eth.get_balance(account_1.address)
    account_2_balance_after = arkiv_client_http.eth.get_balance(account_2.address)

    assert account_2_balance_after == account_2_balance_before + amount, (
        "Account 2 balance should increase by transfer amount"
    )
    assert account_1_balance_after <= account_1_balance_before - amount, (
        "Account 1 balance should decrease by transfer amount"
    )

    logger.info("Arkiv ETH transfer between accounts succeeded (to: NamedAccount)")


@pytest.mark.skip("Skipping ETH transfer not (yet) supported on db chains.")
def test_arkiv_transfer_eth_address(
    arkiv_client_http: Arkiv, account_1: NamedAccount, account_2: NamedAccount
) -> None:
    """Test that ETH (GLM) transfer works."""
    account_1_balance_before = arkiv_client_http.eth.get_balance(account_1.address)
    account_2_balance_before = arkiv_client_http.eth.get_balance(account_2.address)
    amount = 42

    arkiv_client_http.arkiv.transfer_eth(account_2.address, amount)

    account_1_balance_after = arkiv_client_http.eth.get_balance(account_1.address)
    account_2_balance_after = arkiv_client_http.eth.get_balance(account_2.address)

    assert account_2_balance_after == account_2_balance_before + amount, (
        "Account 2 balance should increase by transfer amount"
    )
    assert account_1_balance_after <= account_1_balance_before - amount, (
        "Account 1 balance should decrease by transfer amount"
    )

    logger.info("Arkiv ETH transfer between accounts succeeded (to: checksum address)")
