"""Arkiv client - extends Web3 with entity management."""

from __future__ import annotations

import logging
from typing import Any, cast

from web3 import AsyncWeb3, Web3
from web3.middleware import SignAndSendRawMiddlewareBuilder
from web3.providers import WebSocketProvider
from web3.providers.async_base import AsyncBaseProvider
from web3.providers.base import BaseProvider
from web3.types import Wei

from .account import NamedAccount
from .client_base import ArkivBase
from .module import ArkivModule
from .module_async import AsyncArkivModule

# Set up logger for Arkiv client
logger = logging.getLogger(__name__)


class Arkiv(ArkivBase, Web3):
    """
    Arkiv client that extends Web3 with entity management capabilities.

    Provides the familiar client Web3.py interface plus client.arkiv.* methods for entity operations.
    """

    def __init__(
        self,
        provider: BaseProvider | None = None,
        account: NamedAccount | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Arkiv client with Web3 provider.

        If no Web3 provider is provided, a local development node is automatically created and started
        with a funded default account for rapid prototyping.
        Remember to call arkiv.node.stop() for cleanup, or use context manager:

        Examples:
            Simplest setup (auto-managed node + default account):
                >>> with Arkiv() as arkiv:
                ...     # Default account created, funded with test ETH
                ...     print(arkiv.eth.default_account)
                ...     print(arkiv.eth.chain_id)

            With custom account (auto-funded on local node):
                >>> account = NamedAccount.create("alice")
                >>> with Arkiv(account=account) as arkiv:
                ...     balance = arkiv.eth.get_balance(account.address)

            Custom provider (no auto-node or account):
                >>> provider = ProviderBuilder().kaolin().build()
                >>> account = NamedAccount.from_wallet("alice", wallet_json, password)
                >>> arkiv = Arkiv(provider, account=account)

        Args:
            provider: Web3 provider instance (e.g., HTTPProvider).
                If None, creates local ArkivNode with default account (requires Docker and testcontainers).
            account: Optional NamedAccount to use as the default signer.
                If None and provider is None, creates 'default' account.
                Auto-funded with test ETH if using local node and balance is zero.
            **kwargs: Additional arguments passed to Web3 constructor

        Note:
            Auto-node creation requires testcontainers: pip install arkiv-sdk[dev]
        """
        # Initialize base class first
        ArkivBase.__init__(self)

        # Setup node and account using base class helper
        self.node, provider, account = self._setup_node_and_account(
            provider, account, "http"
        )

        # Validate provider compatibility
        if provider is not None:
            self._validate_provider(provider)

        # Initialize Web3 parent
        Web3.__init__(self, provider, **kwargs)

        # Initialize entity management module
        self.arkiv = ArkivModule(self)

        # Set account if provided
        if account:
            self._initialize_account(account)
        else:
            logger.debug("Initializing Arkiv client without default account")

    def __enter__(self) -> Arkiv:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        # Cleanup event filters first
        logger.debug("Cleaning up event filters...")
        self.arkiv.cleanup_filters()

        # Then stop the node if managed
        self._cleanup_node()

    # Implement abstract methods from ArkivBase
    def _is_connected(self) -> bool:
        """Check if client is connected to provider."""
        return self.is_connected()

    def _get_balance(self, address: str) -> Wei:
        """Get account balance."""
        return cast(Wei, self.eth.get_balance(address))

    def _middleware_remove(self, name: str) -> None:
        """Remove middleware by name."""
        self.middleware_onion.remove(name)

    def _middleware_inject(self, account: NamedAccount, name: str) -> None:
        """Inject signing middleware for account."""
        self.middleware_onion.inject(
            SignAndSendRawMiddlewareBuilder.build(account.local_account),
            name=name,
            layer=0,
        )

    def _set_default_account(self, address: str) -> None:
        """Set the default account address."""
        self.eth.default_account = address

    def _validate_provider(self, provider: BaseProvider) -> None:
        """
        Validate that the provider is compatible with the sync Arkiv client.

        Args:
            provider: Web3 provider to validate

        Raises:
            ValueError: If provider is not compatible with sync operations
        """
        if isinstance(provider, WebSocketProvider):
            raise ValueError(
                "WebSocket providers are not supported by the sync Arkiv client. "
                "Use HTTP provider instead:\n\n"
                "  # Instead of:\n"
                "  provider = ProviderBuilder().localhost().ws().build()\n"
                "  \n"
                "  # Use:\n"
                "  provider = ProviderBuilder().localhost().http().build()\n"
                "  \n"
                "For near real-time updates, consider using HTTP polling."
            )


class AsyncArkiv(ArkivBase, AsyncWeb3):
    """
    Async Arkiv client that extends AsyncWeb3 with entity management capabilities.

    Provides async client Web3.py interface plus client.arkiv.* methods for entity operations.
    """

    def __init__(
        self,
        provider: AsyncBaseProvider | None = None,
        account: NamedAccount | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize AsyncArkiv client with async Web3 provider.

        If no Web3 provider is provided, a local development node is automatically created and started
        with a funded default account for rapid prototyping.
        Remember to call arkiv.node.stop() for cleanup, or use context manager:

        Examples:
            Simplest setup (auto-managed node + default account):
                >>> async with AsyncArkiv() as arkiv:
                ...     # Default account created, funded with test ETH
                ...     print(arkiv.eth.default_account)
                ...     print(await arkiv.eth.chain_id)

            With custom account (auto-funded on local node):
                >>> account = NamedAccount.create("alice")
                >>> async with AsyncArkiv(account=account) as arkiv:
                ...     balance = await arkiv.eth.get_balance(account.address)

            Custom provider (no auto-node or account):
                >>> provider = ProviderBuilder().kaolin().ws().build()
                >>> account = NamedAccount.from_wallet("alice", wallet_json, password)
                >>> arkiv = AsyncArkiv(provider, account=account)

        Args:
            provider: Async Web3 provider instance (e.g., AsyncHTTPProvider).
                If None, creates local ArkivNode with default account (requires Docker and testcontainers).
            account: Optional NamedAccount to use as the default signer.
                If None and provider is None, creates 'default' account.
                Auto-funded with test ETH if using local node and balance is zero.
            **kwargs: Additional arguments passed to AsyncWeb3 constructor

        Note:
            Auto-node creation requires testcontainers: pip install arkiv-sdk[dev]
        """
        # Initialize base class first
        ArkivBase.__init__(self)

        # Setup node and account using base class helper
        self.node, provider, account = self._setup_node_and_account(
            provider, account, "ws"
        )

        # Validate provider compatibility
        if provider is not None:
            self._validate_provider(provider)

        # Initialize AsyncWeb3 parent
        AsyncWeb3.__init__(self, provider, **kwargs)

        # Initialize async entity management module
        self.arkiv = AsyncArkivModule(self)

        # Cache for connection status (used by __repr__)
        self._cached_connected: bool | None = None

        # Store account for deferred initialization (must happen in __aenter__)
        self._pending_account: NamedAccount | None = account if account else None

        if not account:
            logger.debug("Initializing AsyncArkiv client without default account")

    async def is_connected(self, show_traceback: bool = False) -> bool:
        """Check if connected to provider and update connection cache.

        Args:
            show_traceback: Whether to show traceback on connection errors

        Returns:
            True if connected, False otherwise
        """
        result = await super().is_connected(show_traceback)
        self._cached_connected = result
        return result

    async def __aenter__(self) -> AsyncArkiv:
        """Enter async context manager."""
        # Initialize pending account if provided
        if self._pending_account:
            await self._initialize_account_async(self._pending_account)
            self._pending_account = None

        # Populate connection cache
        await self.is_connected()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager."""
        # Note: Event filter cleanup not yet implemented (needs async ArkivModule)

        # Disconnect provider if it has disconnect method
        if hasattr(self.provider, "disconnect"):
            await self.provider.disconnect()

        # Then stop the node if managed and update cache
        self._cleanup_node()

    async def _initialize_account_async(self, account: NamedAccount) -> None:
        """Initialize account asynchronously.

        Args:
            account: The named account to initialize
        """
        logger.debug(f"Initializing AsyncArkiv client with account: {account.name}")
        self.accounts[account.name] = account
        self.switch_to(account.name)

        # If client has node and account has zero balance, fund the account with test ETH
        if self.node is not None:
            balance = await self.eth.get_balance(account.address)
            if balance == 0:
                logger.info(
                    f"Funding account {account.name} ({account.address}) with test ETH..."
                )
                self.node.fund_account(account)

        balance = await self.eth.get_balance(account.address)
        balance_eth = self.from_wei(balance, "ether")
        logger.info(
            f"Account balance for {account.name} ({account.address}): {balance_eth} ETH"
        )

    def _cleanup_node(self) -> None:
        """Cleanup node and update connection cache."""
        super()._cleanup_node()
        self._cached_connected = False

    # Implement abstract methods from ArkivBase
    def _is_connected(self) -> bool:
        """Check if client is connected (uses cache to avoid async issues)."""
        return self._cached_connected if self._cached_connected is not None else False

    def _get_balance(self, address: str) -> Wei:
        """Get account balance - not used in async client (raises error)."""
        raise RuntimeError(
            "_get_balance should not be called directly on AsyncArkiv. "
            "Use 'await client.eth.get_balance(address)' instead."
        )

    def _middleware_remove(self, name: str) -> None:
        """Remove middleware by name."""
        self.middleware_onion.remove(name)

    def _middleware_inject(self, account: NamedAccount, name: str) -> None:
        """Inject signing middleware for account."""
        self.middleware_onion.inject(
            SignAndSendRawMiddlewareBuilder.build(account.local_account),
            name=name,
            layer=0,
        )

    def _set_default_account(self, address: str) -> None:
        """Set the default account address."""
        self.eth.default_account = address

    def _validate_provider(self, provider: AsyncBaseProvider) -> None:
        """
        Validate that the provider is compatible with the async Arkiv client.

        Args:
            provider: Async Web3 provider to validate

        Raises:
            ValueError: If provider is not compatible with async operations
        """
        if not isinstance(provider, AsyncBaseProvider):
            raise ValueError(
                "AsyncArkiv requires an async provider. "
                "Use AsyncHTTPProvider or other async-compatible providers:\n\n"
                "  # For async operations:\n"
                "  provider = ProviderBuilder().localhost().ws().build()\n"
                "  async with AsyncArkiv(provider) as arkiv:\n"
                "      balance = await arkiv.eth.get_balance(address)\n"
                "  \n"
                "  # For sync operations, use Arkiv instead:\n"
                "  provider = ProviderBuilder().localhost().http().build()\n"
                "  with Arkiv(provider) as arkiv:\n"
                "      balance = arkiv.eth.get_balance(address)"
            )
