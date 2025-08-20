"""Wallet module for creating and decrypting Ethereum wallets."""

import getpass
import json
import sys
from pathlib import Path
from typing import cast

import anyio
from eth_account import Account
from xdg import BaseDirectory

WALLET_PATH = Path(BaseDirectory.xdg_config_home) / "golembase" / "wallet.json"

class WalletError(Exception):
    """Base class for wallet-related errors."""

    pass

async def decrypt_wallet() -> bytes:
    """Decrypts the wallet and returns the private key bytes."""
    if not WALLET_PATH.exists():
        raise WalletError(f"Expected wallet file to exist at '{WALLET_PATH}'")

    async with await anyio.open_file(
        WALLET_PATH,
        "r",
    ) as f:
        keyfile_json = json.loads(await f.read())

        if not sys.stdin.isatty():
            password = sys.stdin.read().rstrip()
        else:
            password = getpass.getpass("Enter password to decrypt wallet: ")

        try:
            print(f"Attempting to decrypt wallet at '{WALLET_PATH}'")
            private_key = Account.decrypt(keyfile_json, password)
            print("Successfully decrypted wallet")
        except ValueError as e:
            raise WalletError("Incorrect password or corrupted wallet file.") from e

        return cast(bytes, private_key)

