import getpass
import json
from pathlib import Path
from xdg import BaseDirectory
from eth_account import Account

WALLET_PATH = Path(BaseDirectory.xdg_config_home) / "golembase" / "wallet.json"

class WalletError(Exception):
    """Base class for wallet-related errors."""
    pass

def decrypt_wallet() -> bytes:
    """Decrypts the wallet and returns the private key bytes."""
    if not WALLET_PATH.exists():
        raise WalletError(f"Expected wallet file to exist at '{WALLET_PATH}'")

    with WALLET_PATH.open("r") as f:
        keyfile_json = json.load(f)
        try:
            print(f"Attempting to decrypt wallet at '{WALLET_PATH}'")
            private_key = Account.decrypt(keyfile_json, getpass.getpass("Enter wallet password: "))
        except ValueError as e:
            raise WalletError("Incorrect password or corrupted wallet file.") from e

        return private_key

def create_wallet() -> None:
    """Creates a new wallet if one does not already exist."""
    if WALLET_PATH.exists():
        print(f"WARNING: A wallet already exists at '{WALLET_PATH}'")
        return None

    password = getpass.getpass("Enter wallet password: ")
    confirm = getpass.getpass("Confirm wallet password: ")
    if password != confirm:
        raise WalletError("Passwords do not match.")

    account = Account.create()
    encrypted = account.encrypt(password)

    WALLET_PATH.parent.mkdir(parents=True, exist_ok=True)
    with WALLET_PATH.open("w") as f:
        json.dump(encrypted, f)

    print(f"Wallet created at '{WALLET_PATH}'")
