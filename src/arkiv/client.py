"""Arkiv client - extends Web3 with entity management."""

from __future__ import annotations

import logging
from typing import Any

from web3 import Web3
from web3.middleware import SignAndSendRawMiddlewareBuilder
from web3.providers import WebSocketProvider
from web3.providers.base import BaseProvider

from arkiv.exceptions import NamedAccountNotFoundException

from .account import NamedAccount
from .module import ArkivModule

# Set up logger for Arkiv client
logger = logging.getLogger(__name__)


class Arkiv(Web3):
    """
    Arkiv client that extends Web3 with entity management capabilities.

    Provides the familiar client Web3.py interface plus client.arkiv.* methods for entity operations.
    """

    ACCOUNT_NAME_DEFAULT = "default"

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
        # Self managed node instance (only created/used if no provider is provided)
        self.node: ArkivNode | None = None
        if provider is None:
            from .node import ArkivNode

            logger.info("No provider given, creating managed ArkivNode...")
            self.node = ArkivNode()

            from .provider import ProviderBuilder

            provider = ProviderBuilder().node(self.node).build()

            # Create default account if none provided (for local node prototyping)
            if account is None:
                logger.info(
                    f"Creating default account '{self.ACCOUNT_NAME_DEFAULT}' for local node..."
                )
                account = NamedAccount.create(self.ACCOUNT_NAME_DEFAULT)

        # Validate provider compatibility
        if provider is not None:
            self._validate_provider(provider)

        super().__init__(provider, **kwargs)

        # Initialize entity management module
        self.arkiv = ArkivModule(self)

        # Initialize account management
        self.accounts: dict[str, NamedAccount] = {}
        self.current_signer: str | None = None

        # Set account if provided
        if account:
            logger.debug(f"Initializing Arkiv client with account: {account.name}")
            self.accounts[account.name] = account
            self.switch_to(account.name)

            # If client has node and account a zero balance, also fund the account with test ETH
            if self.node is not None and self.eth.get_balance(account.address) == 0:
                logger.info(
                    f"Funding account {account.name} ({account.address}) with test ETH..."
                )
                self.node.fund_account(account)

            balance = self.eth.get_balance(account.address)
            balance_eth = self.from_wei(balance, "ether")
            logger.info(
                f"Account balance for {account.name} ({account.address}): {balance_eth} ETH"
            )
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
        if self.node:
            logger.debug("Stopping managed ArkivNode...")
            self.node.stop()

    def __del__(self) -> None:
        if self.node and self.node.is_running:
            logger.warning(
                "Arkiv client with managed node is being destroyed but node is still running. "
                "Call arkiv.node.stop() or use context manager: 'with Arkiv() as arkiv:'"
            )

    def __repr__(self) -> str:
        """String representation of Arkiv client."""
        return f"<Arkiv connected={self.is_connected()}>"

    def switch_to(self, account_name: str) -> None:
        """Switch signer account to specified named account."""
        logger.info(f"Switching to account: {account_name}")

        if account_name not in self.accounts:
            logger.error(
                f"Account '{account_name}' not found. Available accounts: {list(self.accounts.keys())}"
            )
            raise NamedAccountNotFoundException(
                f"Unknown account name: '{account_name}'"
            )

        # Remove existing signing middleware if present
        if self.current_signer is not None:
            logger.debug(f"Removing existing signing middleware: {self.current_signer}")
            try:
                self.middleware_onion.remove(self.current_signer)
            except ValueError:
                logger.warning(
                    "Middleware might have been removed elsewhere, continuing"
                )
                pass

        # Inject signer account
        account = self.accounts[account_name]
        logger.debug(f"Injecting signing middleware for account: {account.address}")
        self.middleware_onion.inject(
            SignAndSendRawMiddlewareBuilder.build(account.local_account),
            name=account_name,
            layer=0,
        )

        # Configure default account
        self.eth.default_account = account.address
        self.current_signer = account_name
        logger.info(
            f"Successfully switched to account '{account_name}' ({account.address})"
        )

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
