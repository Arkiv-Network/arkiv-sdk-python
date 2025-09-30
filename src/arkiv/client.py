"""Arkiv client - extends Web3 with entity management."""

import logging
from typing import Any

from web3 import Web3
from web3.middleware import SignAndSendRawMiddlewareBuilder
from web3.providers.base import BaseProvider

from arkiv.exceptions import NamedAccountNotFoundException

from .account import NamedAccount
from .module import ArkivModule

# Set up logger for Arkiv client
logger = logging.getLogger(__name__)


class Arkiv(Web3):
    """
    Arkiv client that extends Web3 with entity management capabilities.

    Provides the familiar Web3.py interface plus arkiv.* methods for entity operations.
    """

    ACCOUNT_NAME_DEFAULT = "default"

    def __init__(
        self,
        provider: BaseProvider | None = None,
        account: NamedAccount | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Arkiv client with Web3 provider.
        Args:
            provider: Web3 provider instance (e.g., HTTPProvider)
            account: Optional NamedAccount to use as the default signer
            **kwargs: Additional arguments passed to Web3 constructor
        """
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
        else:
            logger.debug("Initializing Arkiv client without default account")

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
