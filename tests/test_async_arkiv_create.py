"""Tests for AsyncArkiv client creation and initialization scenarios."""

import logging

import pytest
from web3 import AsyncWeb3
from web3._utils.empty import empty
from web3.providers.async_base import AsyncBaseProvider
from web3.providers.base import BaseProvider

from arkiv import AsyncArkiv
from arkiv.account import NamedAccount
from arkiv.exceptions import NamedAccountNotFoundException
from arkiv.provider import ProviderBuilder

logger = logging.getLogger(__name__)


class TestAsyncArkivClientCreation:
    """Test various AsyncArkiv client creation scenarios."""

    @pytest.mark.asyncio
    async def test_create_asyncarkiv_with_async_http_provider(self, arkiv_node) -> None:
        """Test creating AsyncArkiv client with async HTTP provider."""
        provider = ProviderBuilder().node(arkiv_node).async_mode().build()
        assert isinstance(provider, AsyncBaseProvider)

        async with AsyncArkiv(provider) as client:
            await _assert_asyncarkiv_client_properties(
                client, None, "With Async HTTP Provider"
            )
            logger.info("Created AsyncArkiv client with async HTTP provider")

    @pytest.mark.asyncio
    async def test_create_asyncarkiv_with_account(self, arkiv_node) -> None:
        """Test creating AsyncArkiv client with default account."""
        provider = ProviderBuilder().node(arkiv_node).async_mode().build()
        account = NamedAccount.create("test_account")

        async with AsyncArkiv(provider, account=account) as client:
            await _assert_asyncarkiv_client_properties(client, account, "With Account")
            logger.info("Created AsyncArkiv client with default account")

    @pytest.mark.asyncio
    async def test_create_asyncarkiv_with_kwargs(self, arkiv_node) -> None:
        """Test creating AsyncArkiv client with additional kwargs."""
        provider = ProviderBuilder().node(arkiv_node).async_mode().build()

        # Test with middleware parameter (empty list is a valid kwarg)
        async with AsyncArkiv(provider, middleware=[]) as client:
            await _assert_asyncarkiv_client_properties(client, None, "With kwargs")
            logger.info("Created AsyncArkiv client with additional kwargs")

    @pytest.mark.asyncio
    async def test_asyncarkiv_rejects_sync_provider(self) -> None:
        """Test that AsyncArkiv rejects synchronous providers."""
        provider = ProviderBuilder().localhost().build()  # HTTPProvider (sync)
        assert isinstance(provider, BaseProvider)
        assert not isinstance(provider, AsyncBaseProvider)

        with pytest.raises(ValueError, match="AsyncArkiv requires an async provider"):
            AsyncArkiv(provider)

        logger.info("AsyncArkiv properly rejects sync provider")


class TestAsyncArkivClientAccountManagement:
    """Test account management in AsyncArkiv client."""

    @pytest.mark.asyncio
    async def test_switch_to_existing_account(self, arkiv_node) -> None:
        """Test switching to an existing account."""
        provider = ProviderBuilder().node(arkiv_node).async_mode().build()
        account1 = NamedAccount.create("account1")

        async with AsyncArkiv(provider, account=account1) as client:
            await _assert_asyncarkiv_client_properties(
                client, account1, "Switch accounts"
            )

            # Add accounts manually
            account2 = NamedAccount.create("account2")
            client.accounts["account2"] = account2
            assert len(client.accounts.keys()) == 2, (
                "Should have two accounts registered"
            )

            # Switch to account2
            client.switch_to(account2.name)
            assert client.current_signer == account2.name, "Should switch to account2"
            assert client.eth.default_account == account2.address, (
                "Should set default account"
            )

            # Switch back to account1
            client.switch_to(account1.name)
            assert client.current_signer == account1.name, (
                "Should switch back to account1"
            )
            assert client.eth.default_account == account1.address, (
                "Should set default account"
            )

            logger.info("Successfully switched between accounts")

    @pytest.mark.asyncio
    async def test_switch_to_nonexistent_account(self, arkiv_node) -> None:
        """Test switching to a non-existent account raises exception."""
        provider = ProviderBuilder().node(arkiv_node).async_mode().build()

        async with AsyncArkiv(provider) as client:
            with pytest.raises(NamedAccountNotFoundException) as exc_info:
                client.switch_to("nonexistent")

            assert "nonexistent" in str(exc_info.value), (
                "Should mention the account name"
            )
            assert client.current_signer is None, "Should not change current signer"

            logger.info("Properly handled non-existent account switch")

    @pytest.mark.asyncio
    async def test_switch_account_removes_old_middleware(self, arkiv_node) -> None:
        """Test that switching accounts properly removes old middleware."""
        provider = ProviderBuilder().node(arkiv_node).async_mode().build()
        account = NamedAccount.create("initial_account")

        async with AsyncArkiv(provider, account=account) as client:
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


class TestAsyncArkivClientRepr:
    """Test AsyncArkiv client string representation."""

    @pytest.mark.asyncio
    async def test_repr_shows_class_name(self, arkiv_node) -> None:
        """Test repr contains AsyncArkiv class name."""
        provider = ProviderBuilder().node(arkiv_node).async_mode().build()

        async with AsyncArkiv(provider) as client:
            repr_str = repr(client)

            assert isinstance(repr_str, str), "Should return string"
            assert "AsyncArkiv" in repr_str, "Should contain class name"
            assert "connected=" in repr_str, "Should show connection status"

            logger.info(f"AsyncArkiv repr: {repr_str}")

    @pytest.mark.asyncio
    async def test_repr_after_is_connected_call(self, arkiv_node) -> None:
        """Test repr shows accurate status after calling is_connected()."""
        provider = ProviderBuilder().node(arkiv_node).async_mode().build()

        async with AsyncArkiv(provider) as client:
            # is_connected() is called in __aenter__, cache should be populated
            connected = await client.is_connected()
            repr_str = repr(client)

            assert "connected=True" in repr_str, (
                f"Should show connected=True after is_connected(), got: {repr_str}"
            )
            assert connected is True, "Should be connected to node"

            logger.info(f"AsyncArkiv repr after is_connected: {repr_str}")

    @pytest.mark.asyncio
    async def test_repr_after_cleanup(self, arkiv_node) -> None:
        """Test repr shows disconnected after cleanup."""
        provider = ProviderBuilder().node(arkiv_node).async_mode().build()

        client = AsyncArkiv(provider)
        async with client:
            pass  # Exit context

        # After cleanup, cache should be False
        repr_str = repr(client)
        assert "connected=False" in repr_str, (
            f"Should show connected=False after cleanup, got: {repr_str}"
        )

        logger.info(f"AsyncArkiv repr after cleanup: {repr_str}")


class TestAsyncArkivClientInheritance:
    """Test that AsyncArkiv properly inherits from AsyncWeb3."""

    @pytest.mark.asyncio
    async def test_inherits_asyncweb3_attributes(self, arkiv_node) -> None:
        """Test that AsyncArkiv client has all expected AsyncWeb3 attributes."""
        provider = ProviderBuilder().node(arkiv_node).async_mode().build()

        async with AsyncArkiv(provider) as client:
            # Test core AsyncWeb3 attributes
            assert hasattr(client, "eth"), "Should have eth module"
            assert hasattr(client, "net"), "Should have net module"
            assert hasattr(client, "is_connected"), "Should have is_connected method"
            assert hasattr(client, "middleware_onion"), "Should have middleware_onion"

            # Test that async methods work
            connected = await client.is_connected()
            assert isinstance(connected, bool), "is_connected should return bool"

            logger.info("AsyncArkiv client properly inherits AsyncWeb3 attributes")

    @pytest.mark.asyncio
    async def test_asyncarkiv_specific_attributes(self, arkiv_node) -> None:
        """Test that AsyncArkiv client has its specific attributes."""
        provider = ProviderBuilder().node(arkiv_node).async_mode().build()

        async with AsyncArkiv(provider) as client:
            # Test AsyncArkiv-specific attributes
            assert hasattr(client, "accounts"), "Should have accounts dict"
            assert hasattr(client, "current_signer"), "Should have current_signer"
            assert hasattr(client, "switch_to"), "Should have switch_to method"
            assert hasattr(client, "_cached_connected"), (
                "Should have _cached_connected for connection status caching"
            )

            # Test connection cache
            assert isinstance(client._cached_connected, bool), (
                "Cache should be populated after context entry"
            )

            logger.info("AsyncArkiv client has all specific attributes")


async def _assert_asyncarkiv_client_properties(
    client: AsyncArkiv, account: NamedAccount | None, label: str
) -> None:
    """Helper to assert AsyncArkiv client properties."""
    # Check basic properties
    assert isinstance(client, AsyncWeb3), f"{label}: Should inherit from AsyncWeb3"
    assert isinstance(client, AsyncArkiv), f"{label}: Should create AsyncArkiv instance"
    assert hasattr(client, "eth"), "Should have eth module"

    # Check connection
    if client.provider:
        connected = await client.is_connected()
        assert connected, (
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


class TestAsyncArkivModuleBasics:
    """Test basic AsyncArkivModule functionality."""

    @pytest.mark.asyncio
    async def test_module_exists(self, arkiv_node) -> None:
        """Test that arkiv module is attached to AsyncArkiv client."""
        provider = ProviderBuilder().node(arkiv_node).async_mode().build()

        async with AsyncArkiv(provider) as client:
            assert hasattr(client, "arkiv"), "Should have arkiv module"
            assert client.arkiv is not None, "Arkiv module should be initialized"
            logger.info("AsyncArkiv module is attached to client")

    @pytest.mark.asyncio
    async def test_module_is_available(self, arkiv_node) -> None:
        """Test that arkiv module reports as available."""
        provider = ProviderBuilder().node(arkiv_node).async_mode().build()

        async with AsyncArkiv(provider) as client:
            available = client.arkiv.is_available()
            assert available is True, "Arkiv module should be available"
            logger.info("AsyncArkiv module is available")

    @pytest.mark.asyncio
    async def test_module_has_contract(self, arkiv_node) -> None:
        """Test that arkiv module has contract instance."""
        provider = ProviderBuilder().node(arkiv_node).async_mode().build()

        async with AsyncArkiv(provider) as client:
            assert hasattr(client.arkiv, "contract"), "Should have contract attribute"
            assert client.arkiv.contract is not None, "Contract should be initialized"
            logger.info("AsyncArkiv module has contract instance")
