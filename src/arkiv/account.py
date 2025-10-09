"""Account management for Arkiv client."""

from __future__ import annotations

import getpass
import json
import sys
from pathlib import Path
from typing import Any

from eth_account import Account
from eth_account.hdaccount import ETHEREUM_DEFAULT_PATH
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress

from .exceptions import AccountNameException

# Enable unaudited HD wallet features for mnemonic support
Account.enable_unaudited_hdwallet_features()


class NamedAccount:
    """
    A LocalAccount wrapper with an associated name for easier management.

    Wraps eth_account's LocalAccount to include a human-readable name
    for better account organization and identification in multi-account scenarios.
    """

    def __init__(self, name: str, account: LocalAccount):
        """
        Initialize a named account.

        Args:
            name: Human-readable name for the account
            account: The LocalAccount instance to wrap
        """
        self.name = self._check_and_trim(name)
        self._account = account

    def __repr__(self) -> str:
        """String representation showing name and address."""
        return f"<NamedAccount name='{self.name}' address='{self.address}'>"

    def __str__(self) -> str:
        """String representation for display."""
        return f"{self.name} ({self.address})"

    @property
    def address(self) -> ChecksumAddress:
        """Get the account address."""
        return self._account.address

    @property
    def key(self) -> bytes:
        """Get the private key."""
        return self._account.key

    @property
    def local_account(self) -> LocalAccount:
        """Get the wrapped LocalAccount."""
        return self._account

    def __getattr__(self, name: str) -> Any:
        """Delegate any other attributes to the wrapped LocalAccount."""
        return getattr(self._account, name)

    @classmethod
    def create(cls, name: str) -> NamedAccount:
        """
        Create a new random account with a name.

        Args:
            name: Human-readable name for the account

        Returns:
            New NamedAccount instance with random private key
        """
        account = Account.create()
        return cls(name, account)

    @classmethod
    def from_private_key(cls, name: str, private_key: str | bytes) -> NamedAccount:
        """
        Create a NamedAccount from a private key.

        Args:
            name: Human-readable name for the account
            private_key: The private key (hex string or bytes)

        Returns:
            NamedAccount instance
        """
        account = Account.from_key(private_key)
        return cls(name, account)

    @classmethod
    def from_mnemonic(
        cls,
        name: str,
        mnemonic: str,
        passphrase: str = "",
        account_path: str = ETHEREUM_DEFAULT_PATH,
    ) -> NamedAccount:
        """
        Create a NamedAccount from an existing mnemonic phrase.

        Args:
            name: Human-readable name for the account
            mnemonic: The mnemonic phrase for the account
            passphrase: Optional passphrase used to encrypt the mnemonic (default: empty string)
            account_path: Optional HD path for key derivation (default: Ethereum standard path)

        Returns:
            NamedAccount instance
        """
        account = Account.from_mnemonic(
            mnemonic, passphrase=passphrase, account_path=account_path
        )
        return cls(name, account)

    @classmethod
    def from_wallet(cls, name: str, wallet_json: str, password: str) -> NamedAccount:
        """
        Create a NamedAccount from a JSON wallet.

        Args:
            name: Human-readable name for the account
            wallet_json: A JSON wallet string from eth_account
            password: The password to decrypt the wallet

        Returns:
            NamedAccount instance
        """
        private_key = Account.decrypt(wallet_json, password)
        account = Account.from_key(private_key)
        return cls(name, account)

    def export_wallet(self, password: str) -> str:
        """
        Export the account as an encrypted JSON wallet.

        Args:
            password: The password to encrypt the wallet

        Returns:
            Encrypted JSON wallet as a string
        """
        return json.dumps(Account.encrypt(self.key, password))

    def _check_and_trim(self, name: str) -> str:
        if name is None or len(name.strip()) == 0:
            raise AccountNameException("Account name must be a non-empty string.")
        return name.strip()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Create a new named account and write a JSON wallet file."
    )
    parser.add_argument("name", help="Name of the account (used in wallet_<name>.json)")
    args = parser.parse_args()

    # Sanitize name for filename (alphanumeric, dash, underscore only)
    import re

    account_name = re.sub(r"[^a-zA-Z0-9_-]", "_", args.name.strip())
    wallet_path = Path(f"wallet_{account_name}.json")

    if wallet_path.exists():
        print(f'File "{wallet_path}" already exists. Aborting.')
        sys.exit(1)

    account = NamedAccount(account_name, Account.create())
    password = getpass.getpass("Enter wallet password: ")
    encrypted = account.local_account.encrypt(password)

    # Ensure address has 0x prefix (eth_account.encrypt doesn't include it)
    if "address" in encrypted and not encrypted["address"].startswith("0x"):
        encrypted["address"] = "0x" + encrypted["address"]

    with wallet_path.open("w") as f:
        json.dump(encrypted, f)

    print(f"Named account: {account}")
    print(f"Wallet file: {wallet_path}")


# add main entry point
if __name__ == "__main__":
    main()
