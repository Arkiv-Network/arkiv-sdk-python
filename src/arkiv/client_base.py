"""Base class for Arkiv clients with shared node and account management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

from web3.providers.async_base import AsyncBaseProvider
from web3.providers.base import BaseProvider

from .account import NamedAccount
from .exceptions import NamedAccountNotFoundException

if TYPE_CHECKING:
    from web3.types import Wei

    from .node import ArkivNode

logger = logging.getLogger(__name__)


class ArkivBase:
    """
    Base class for Arkiv clients with shared node and account management.

    This class contains all the common logic for both sync (Arkiv) and async (AsyncArkiv)
    clients, including node creation, account management, and cleanup.

    Subclasses must implement the abstract methods for provider-specific operations.
    """

    # Default account name for auto-created accounts
    ACCOUNT_NAME_DEFAULT = "default"

    # These will be set by the Web3/AsyncWeb3 parent class
    eth: Any
    from_wei: Any

    def __init__(self) -> None:
        """Initialize base Arkiv client state.

        Note: This is called by subclasses after their parent Web3 init.
        """
        # Self managed node instance
        self.node: ArkivNode | None = None

        # Account management
        self.accounts: dict[str, NamedAccount] = {}
        self.current_signer: str | None = None

    def __del__(self) -> None:
        """Warn user if node is still running when object is garbage collected."""
        # Determine client type from class name
        client_type = self.__class__.__name__
        self._warn_if_node_running(client_type)

    def __repr__(self) -> str:
        """String representation of Arkiv client."""
        client_type = self.__class__.__name__
        connected = self._is_connected()
        return f"<{client_type} connected={connected}>"

    @staticmethod
    def _create_managed_node_and_provider(
        transport: Literal["http", "ws"] = "http",
    ) -> tuple[ArkivNode, BaseProvider | AsyncBaseProvider]:
        """
        Create a managed ArkivNode and provider for Arkiv clients.

        Used by both Arkiv (sync) and AsyncArkiv (async) when no provider is given.

        Args:
            transport: "http" for sync Arkiv, "ws" for async AsyncArkiv

        Returns:
            Tuple of (ArkivNode, Provider) where provider type matches transport:
            - "http" → (ArkivNode, HTTPProvider)
            - "ws" → (ArkivNode, WebSocketProvider)
        """
        from .node import ArkivNode
        from .provider import ProviderBuilder

        logger.info("No provider given, creating managed ArkivNode...")
        node = ArkivNode()

        # Build provider based on transport
        if transport == "ws":
            logger.info(f"Transport '{transport}': creating WebSocketProvider")
            provider = ProviderBuilder().node(node).ws().build()
        else:  # http
            logger.info(f"Transport '{transport}': creating HTTPProvider")
            provider = ProviderBuilder().node(node).build()

        return node, provider

    @staticmethod
    def _create_default_account(account_name: str = "default") -> NamedAccount:
        """
        Create a default named account for local node prototyping.

        Used by both Arkiv (sync) and AsyncArkiv (async) when no account is provided
        and a local node is auto-created.

        Args:
            account_name: Name for the account (default: "default")

        Returns:
            NamedAccount with the specified name
        """
        logger.info(f"Creating default account '{account_name}' for local node...")
        return NamedAccount.create(account_name)

    def _setup_node_and_account(
        self,
        provider: Any | None,
        account: NamedAccount | None,
        transport: Literal["http", "ws"],
    ) -> tuple[ArkivNode | None, Any, NamedAccount | None]:
        """
        Set up managed node and default account if needed.

        Args:
            provider: Web3 provider or None to auto-create
            account: NamedAccount or None to auto-create
            transport: "http" or "ws" for provider type

        Returns:
            Tuple of (node, provider, account)
        """
        node = None
        if provider is None:
            node, provider = self._create_managed_node_and_provider(transport)

            # Create default account if none provided (for local node prototyping)
            if account is None:
                account = self._create_default_account()

        return node, provider, account

    def _initialize_account(self, account: NamedAccount) -> None:
        """
        Initialize account management for the client.

        Args:
            account: NamedAccount to set up
        """
        logger.debug(f"Initializing Arkiv client with account: {account.name}")
        self.accounts[account.name] = account
        self.switch_to(account.name)

        # If client has node and account has zero balance, fund the account with test ETH
        if self.node is not None:
            balance = self._get_balance(account.address)
            if balance == 0:
                logger.info(
                    f"Funding account {account.name} ({account.address}) with test ETH..."
                )
                self.node.fund_account(account)

        balance = self._get_balance(account.address)
        balance_eth = self.from_wei(balance, "ether")
        logger.info(
            f"Account balance for {account.name} ({account.address}): {balance_eth} ETH"
        )

    def switch_to(self, account_name: str) -> None:
        """
        Switch signer account to specified named account.

        Args:
            account_name: Name of the account to switch to

        Raises:
            NamedAccountNotFoundException: If account name not found
        """
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
                self._middleware_remove(self.current_signer)
            except ValueError:
                logger.warning(
                    "Middleware might have been removed elsewhere, continuing"
                )

        # Inject signer account
        account = self.accounts[account_name]
        logger.debug(f"Injecting signing middleware for account: {account.address}")
        self._middleware_inject(account, account_name)

        # Configure default account
        self._set_default_account(account.address)
        self.current_signer = account_name
        logger.info(
            f"Successfully switched to account '{account_name}' ({account.address})"
        )

    def _cleanup_node(self) -> None:
        """Stop the managed node if present."""
        if self.node:
            logger.debug("Stopping managed ArkivNode...")
            self.node.stop()

    def _warn_if_node_running(self, client_type: str) -> None:
        """
        Warn if node is still running when client is destroyed.

        Args:
            client_type: "Arkiv" or "AsyncArkiv" for the warning message
        """
        if self.node and self.node.is_running:
            context_mgr = (
                "with Arkiv() as arkiv:"
                if client_type == "Arkiv"
                else "async with AsyncArkiv() as arkiv:"
            )
            logger.warning(
                f"{client_type} client with managed node is being destroyed but node is still running. "
                f"Call arkiv.node.stop() or use context manager: '{context_mgr}'"
            )

    # Abstract methods to be implemented by subclasses
    def _is_connected(self) -> bool:
        """
        Check if client is connected to provider (implemented by subclass).

        Returns:
            True if connected, False otherwise
        """
        raise NotImplementedError("Subclass must implement _is_connected")

    def _get_balance(self, address: str) -> Wei:
        """
        Get account balance (implemented by subclass).

        For sync clients (Arkiv), this is a regular method returning Wei.
        For async clients (AsyncArkiv), override _initialize_account to handle async.

        Args:
            address: Account address

        Returns:
            Account balance in Wei
        """
        raise NotImplementedError("Subclass must implement _get_balance")

    def _middleware_remove(self, name: str) -> None:
        """
        Remove middleware by name (implemented by subclass).

        Args:
            name: Middleware name
        """
        raise NotImplementedError("Subclass must implement _middleware_remove")

    def _middleware_inject(self, account: NamedAccount, name: str) -> None:
        """
        Inject signing middleware for account (implemented by subclass).

        Args:
            account: Account to inject middleware for
            name: Middleware name
        """
        raise NotImplementedError("Subclass must implement _middleware_inject")

    def _set_default_account(self, address: str) -> None:
        """
        Set the default account address (implemented by subclass).

        Args:
            address: Account address
        """
        raise NotImplementedError("Subclass must implement _set_default_account")
