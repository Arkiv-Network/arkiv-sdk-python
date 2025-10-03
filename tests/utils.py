import logging
import os
from pathlib import Path

from arkiv.account import NamedAccount
from arkiv.types import TxHash

WALLET_FILE_ENV_PREFIX = "WALLET_FILE"
WALLET_PASSWORD_ENV_PREFIX = "WALLET_PASSWORD"

logger = logging.getLogger(__name__)


def check_tx_hash(label: str, tx_hash: TxHash) -> None:
    """Check transaction hash validity."""
    logger.info(f"{label}: Checking transaction hash {tx_hash}")
    assert tx_hash is not None, f"{label}: Transaction hash should not be None"
    assert isinstance(tx_hash, str), (
        f"{label}: Transaction hash should be a string (TxHash)"
    )
    assert len(tx_hash) == 66, (
        f"{label}: Transaction hash should be 66 characters long (0x + 64 hex)"
    )
    assert tx_hash.startswith("0x"), f"{label}: Transaction hash should start with 0x"


def create_account(index: int, name: str) -> NamedAccount:
    """Create a named account from env vars or generate a new one."""
    wallet_file = os.getenv(f"{WALLET_FILE_ENV_PREFIX}_{index}")
    wallet_password = os.getenv(f"{WALLET_PASSWORD_ENV_PREFIX}_{index}")

    if not wallet_file or not wallet_password:
        return NamedAccount.create(name)

    logger.info(f"Using existing wallet: {wallet_file}")
    wallet_json = load_wallet_json(wallet_file)
    return NamedAccount.from_wallet(name, wallet_json, wallet_password)


def load_wallet_json(wallet_file: str) -> str:
    """Load account from encrypted wallet file."""
    wallet_path = Path(wallet_file)
    with wallet_path.open() as f:
        return f.read()
