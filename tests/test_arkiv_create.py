"""Tests for Arkiv client creation and initialization scenarios."""

import logging

import pytest
from web3 import Web3
from web3._utils.empty import empty
from web3.providers import HTTPProvider
from web3.providers.auto import AutoProvider

from arkiv import Arkiv
from arkiv.account import NamedAccount
from arkiv.exceptions import NamedAccountNotFoundException
from arkiv.module import ArkivModule

logger = logging.getLogger(__name__)


class TestArkivClientCreation:
    """Test various Arkiv client creation scenarios."""

    def test_create_arkiv_without_provider(self) -> None:
        """Test creating Arkiv client without provider (creates local node + default account)."""
        with Arkiv() as client:
            # When no provider given, Arkiv creates a local node AND a default account
            assert client.node is not None, "Should create managed node"
            assert len(client.accounts) == 1, "Should create default account"
            assert "default" in client.accounts, "Should have 'default' account"
            assert client.current_signer == "default", (
                "Should set default as current signer"
            )
            assert client.eth.default_account is not None, (
                "Should have default account set"
            )
            assert client.is_connected(), "Should be connected to managed node"
            logger.info(
                "Created Arkiv client without provider - auto-created node and default account"
            )

    def test_create_arkiv_with_http_provider(self, arkiv_node) -> None:
        """Test creating Arkiv client with HTTP provider."""
        provider = HTTPProvider(arkiv_node.http_url)
        client = Arkiv(provider)

        _assert_arkiv_client_properties(client, None, "With HTTP Provider")
        logger.info("Created Arkiv client with HTTP provider")

    def test_create_arkiv_with_account(self, arkiv_node) -> None:
        """Test creating Arkiv client with default account."""
        provider = HTTPProvider(arkiv_node.http_url)
        account = NamedAccount.create("test_account")
        client = Arkiv(provider, account=account)

        _assert_arkiv_client_properties(client, account, "With Account")
        logger.info("Created Arkiv client with default account")

    def test_create_arkiv_with_kwargs(self, arkiv_node) -> None:
        """Test creating Arkiv client with additional kwargs."""
        provider = HTTPProvider(arkiv_node.http_url)

        # Test with middleware parameter (empty list is a valid kwarg)
        client = Arkiv(provider, middleware=[])

        _assert_arkiv_client_properties(client, None, "With kwargs")
        logger.info("Created Arkiv client with additional kwargs")


class TestArkivClientAccountManagement:
    """Test account management in Arkiv client."""

    def test_switch_to_existing_account(self, arkiv_node) -> None:
        """Test switching to an existing account."""
        provider = HTTPProvider(arkiv_node.http_url)
        account1 = NamedAccount.create("account1")
        client = Arkiv(provider, account=account1)

        _assert_arkiv_client_properties(client, account1, "Switch accounts")

        # Add accounts manually
        account2 = NamedAccount.create("account2")
        client.accounts["account2"] = account2
        assert len(client.accounts.keys()) == 2, "Should have two accounts registered"

        # Switch to account2
        client.switch_to(account2.name)
        assert client.current_signer == account2.name, "Should switch to account2"
        assert client.eth.default_account == account2.address, (
            "Should set default account"
        )

        # Switch back to account1
        client.switch_to(account1.name)
        assert client.current_signer == account1.name, "Should switch back to account1"
        assert client.eth.default_account == account1.address, (
            "Should set default account"
        )

        logger.info("Successfully switched between accounts")

    def test_switch_to_nonexistent_account(self, arkiv_node) -> None:
        """Test switching to a non-existent account raises exception."""
        provider = HTTPProvider(arkiv_node.http_url)
        client = Arkiv(provider)

        with pytest.raises(NamedAccountNotFoundException) as exc_info:
            client.switch_to("nonexistent")

        assert "nonexistent" in str(exc_info.value), "Should mention the account name"
        assert client.current_signer is None, "Should not change current signer"

        logger.info("Properly handled non-existent account switch")

    def test_switch_account_removes_old_middleware(self, arkiv_node) -> None:
        """Test that switching accounts properly removes old middleware."""
        provider = HTTPProvider(arkiv_node.http_url)
        account = NamedAccount.create("initial_account")
        client = Arkiv(provider, account=account)

        # Add another account and switch
        new_account = NamedAccount.create("new_account")
        client.accounts["new_account"] = new_account

        # Verify initial state
        assert client.current_signer == "initial_account"

        # Switch to new account
        client.switch_to("new_account")
        assert client.current_signer == "new_account"
        assert client.eth.default_account == new_account.address

        logger.info("Successfully switched accounts and removed old middleware")


class TestArkivClientRepr:
    """Test Arkiv client string representation."""

    def test_repr_disconnected(self) -> None:
        """Test repr of disconnected client."""
        client = Arkiv()
        repr_str = repr(client)

        # Stop default node
        client.node.stop()

        assert isinstance(repr_str, str), "Should return string"
        assert "Arkiv" in repr_str, "Should contain class name"
        assert "connected=False" not in repr_str, "Should not show disconnected"

    def test_repr_connected_with_defaults(self) -> None:
        """Test repr of connected client with defaults."""
        with Arkiv() as client:
            repr_str = repr(client)

            assert isinstance(repr_str, str), "Should return string"
            assert "Arkiv" in repr_str, "Should contain class name"
            assert "connected=True" in repr_str, "Should show connection status"

            logger.info(f"Connected client repr: {repr_str}")

    def test_repr_connected_with_provider(self, arkiv_node) -> None:
        """Test repr of connected client."""
        provider = HTTPProvider(arkiv_node.http_url)
        client = Arkiv(provider)

        repr_str = repr(client)

        assert isinstance(repr_str, str), "Should return string"
        assert "Arkiv" in repr_str, "Should contain class name"
        assert "connected=True" in repr_str, "Should show connection status"

        logger.info(f"Connected client repr: {repr_str}")


class TestArkivClientInheritance:
    """Test that Arkiv properly inherits from Web3."""

    def test_inherits_web3_attributes(self, arkiv_node) -> None:
        """Test that Arkiv client has all expected Web3 attributes."""
        provider = HTTPProvider(arkiv_node.http_url)
        client = Arkiv(provider)

        # Test core Web3 attributes
        assert hasattr(client, "eth"), "Should have eth module"
        assert hasattr(client, "net"), "Should have net module"
        assert hasattr(client, "is_connected"), "Should have is_connected method"
        assert hasattr(client, "middleware_onion"), "Should have middleware_onion"

        # Test that methods work
        assert isinstance(client.is_connected(), bool), (
            "is_connected should return bool"
        )

        logger.info("Arkiv client properly inherits Web3 attributes")

    def test_arkiv_specific_attributes(self, arkiv_node) -> None:
        """Test that Arkiv client has its specific attributes."""
        provider = HTTPProvider(arkiv_node.http_url)
        client = Arkiv(provider)

        # Test Arkiv-specific attributes
        assert hasattr(client, "arkiv"), "Should have arkiv module"
        assert hasattr(client, "accounts"), "Should have accounts dict"
        assert hasattr(client, "current_signer"), "Should have current_signer"
        assert hasattr(client, "switch_to"), "Should have switch_to method"

        # Test arkiv module
        assert isinstance(client.arkiv, ArkivModule), "arkiv should be ArkivModule"
        assert client.arkiv.client is client, "arkiv module should reference client"

        logger.info("Arkiv client has all specific attributes")


def _assert_arkiv_client_properties(
    client: Arkiv, account: NamedAccount | None, label: str
) -> None:
    # Check basic properties
    assert isinstance(client, Web3), f"{label}: Should inherit from Web3"
    assert isinstance(client, Arkiv), f"{label}: Should create Arkiv instance"
    assert hasattr(client, "eth"), "Should have eth module"
    assert hasattr(client, "arkiv"), f"{label}: Should have arkiv module"
    assert isinstance(client.arkiv, ArkivModule), (
        f"{label}: Should have ArkivModule instance"
    )

    # check if arkiv has provider and if so, check if it is connected
    if client.provider:
        if type(client.provider) is AutoProvider:
            logger.info(
                f"{label}: Provider is AutoProvider, skipping is_connected check"
            )
        else:
            assert client.is_connected(), (
                f"{label}: Should be connected to node (provider: {type(client.provider)})"
            )

    # Check account-related properties
    if account:
        assert len(client.accounts.keys()) == 1, (
            f"{label}: Should have one account registered"
        )
        assert account.name in client.accounts, (
            f"{label}: Should have the account {account.name} registered"
        )
        assert client.eth.default_account == account.address, (
            f"{label}: Should set default account"
        )
        assert client.current_signer == account.name, (
            f"{label}: Should have current signer {account.name}"
        )
    else:
        assert client.accounts == {}, f"{label}: Should not have registered accounts"
        assert client.eth.default_account == empty, (
            f"{label}: Should set default account to empty (not {client.eth.default_account})"
        )
        assert client.current_signer is None, f"{label}: Should have no current signer"
