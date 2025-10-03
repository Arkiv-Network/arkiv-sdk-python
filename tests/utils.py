import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from arkiv.account import NamedAccount
from arkiv.types import CreateOp, EntityKey, Operations, TxHash

if TYPE_CHECKING:
    from arkiv.client import Arkiv

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


def bulk_create_entities(
    client: "Arkiv", create_ops: list[CreateOp], label: str = "bulk_create"
) -> list[EntityKey]:
    """Create multiple entities in a single bulk transaction.

    Args:
        client: Arkiv client instance
        create_ops: List of CreateOp operations to execute
        label: Label for transaction hash validation logging

    Returns:
        List of entity keys created

    Raises:
        RuntimeError: If the number of creates in receipt doesn't match operations
    """
    # Use execute() for bulk creation
    create_operations = Operations(creates=create_ops)
    create_receipt = client.arkiv.execute(create_operations)

    # Check transaction hash of bulk create
    check_tx_hash(label, create_receipt.tx_hash)

    # Verify all creates succeeded
    if len(create_receipt.creates) != len(create_ops):
        raise RuntimeError(
            f"Expected {len(create_ops)} creates in receipt, got {len(create_receipt.creates)}"
        )

    # Extract and return entity keys from receipt
    entity_keys = [create.entity_key for create in create_receipt.creates]
    logger.info(f"{label}: Created {len(entity_keys)} entities in bulk transaction")

    return entity_keys


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
