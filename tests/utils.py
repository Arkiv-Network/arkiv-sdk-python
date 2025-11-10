import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from web3.types import TxParams

from arkiv.account import NamedAccount
from arkiv.types import (
    Attributes,
    CreateOp,
    DeleteOp,
    Entity,
    EntityKey,
    ExtendOp,
    Operations,
    TransactionReceipt,
    TxHash,
    UpdateOp,
)

if TYPE_CHECKING:
    from arkiv.client import Arkiv

WALLET_FILE_ENV_PREFIX = "WALLET_FILE"
WALLET_PASSWORD_ENV_PREFIX = "WALLET_PASSWORD"

BTL = 100
CONTENT_TYPE = "text/plain"

logger = logging.getLogger(__name__)


def to_create(
    payload: bytes = b"",
    content_type: str = CONTENT_TYPE,
    attributes: dict[str, str | int] | None = None,
    btl: int = BTL,
) -> CreateOp:
    return CreateOp(
        payload=payload,
        content_type=content_type,
        attributes=Attributes(attributes),
        btl=btl,
    )


def get_custom_attributes(entity: Entity) -> Attributes:
    """Extract custom attributes from an entity, excluding standard fields."""
    custom_attributes = {
        key: value for key, value in entity.attributes.items() if key[0] != "$"
    }
    return Attributes(custom_attributes)


def check_tx_hash(label: str, tx_receipt: TransactionReceipt) -> None:
    """Check transaction hash validity."""
    logger.debug(f"{label}: Checking tx hash in tx receipt: {tx_receipt}")
    assert tx_receipt.tx_hash is not None, (
        f"{label}: Transaction hash should not be None"
    )
    assert isinstance(tx_receipt.tx_hash, str), (
        f"{label}: Transaction hash should be a string (TxHash)"
    )
    assert len(tx_receipt.tx_hash) == 66, (
        f"{label}: Transaction hash should be 66 characters long (0x + 64 hex)"
    )
    assert tx_receipt.tx_hash.startswith("0x"), (
        f"{label}: Transaction hash should start with 0x"
    )


def check_entity_key(label: str, entity_key: EntityKey) -> None:
    """Check entity key validity."""
    logger.info(f"{label}: Checking entity key {entity_key}")
    assert entity_key is not None, f"{label}: Entity key should not be None"
    assert isinstance(entity_key, str), f"{label}: Entity key should be a string"
    assert len(entity_key) == 66, (
        f"{label}: Entity key should be 66 characters long (0x + 64 hex)"
    )
    assert entity_key.startswith("0x"), f"{label}: Entity key should start with 0x"


def check_entity(label: str, client: "Arkiv", expected: Entity) -> None:
    """Fetch an entity and compare it with expected values.

    Args:
        label: Label for logging and assertion messages
        client: Arkiv client instance
        expected: The expected entity object to compare against

    Assertions:
        - entity_key must be equal
        - owner must be equal
        - payload must be equal
        - attributes must be equal
        - actual expires_at_block must be >= expected expires_at_block
    """
    logger.info(f"{label}: Fetching and comparing entity {expected.key}")

    # Fetch the actual entity from storage
    actual = client.arkiv.get_entity(expected.key)

    # Check entity_key
    assert actual.key == expected.key, (
        f"{label}: Entity keys do not match - "
        f"actual: {actual.key}, expected: {expected.key}"
    )

    # Check owner
    assert actual.owner == expected.owner, (
        f"{label}: Owners do not match - "
        f"actual: {actual.owner}, expected: {expected.owner}"
    )

    # Check payload
    assert actual.payload == expected.payload, (
        f"{label}: Payloads do not match - "
        f"actual: {actual.payload!r}, expected: {expected.payload!r}"
    )

    # Check attributes
    assert actual.attributes == expected.attributes, (
        f"{label}: Attributes do not match - "
        f"actual: {actual.attributes}, expected: {expected.attributes}"
    )

    # Check expires_at_block (actual must be >= expected)
    if expected.expires_at_block is not None:
        assert actual.expires_at_block is not None, (
            f"{label}: Actual expires_at_block is None but expected is {expected.expires_at_block}"
        )
        assert actual.expires_at_block >= expected.expires_at_block, (
            f"{label}: Actual expires_at_block ({actual.expires_at_block}) "
            f"is less than expected ({expected.expires_at_block})"
        )

    logger.info(f"{label}: Entity comparison successful")


def create_entities(
    client: "Arkiv",
    create_ops: list[CreateOp],
    tx_params: TxParams | None = None,
) -> tuple[list[EntityKey], TxHash]:
    """
    Create multiple entities in a single transaction (bulk create).

    Args:
        client: Arkiv client instance
        create_ops: List of CreateOp objects to create
        tx_params: Optional additional transaction parameters

    Returns:
        An array of all created entity keys and transaction hash of the operation
    """
    if not create_ops or len(create_ops) == 0:
        raise ValueError("create_ops must contain at least one CreateOp")

    # Wrap in Operations container and execute
    operations = Operations(creates=create_ops)
    receipt = client.arkiv.execute(operations, tx_params)

    # Verify all creates succeeded
    if len(receipt.creates) != len(create_ops):
        raise RuntimeError(
            f"Expected {len(create_ops)} creates in receipt, got {len(receipt.creates)}"
        )

    entity_keys = [create.key for create in receipt.creates]
    return entity_keys, receipt.tx_hash


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
    check_tx_hash(label, create_receipt)

    # Verify all creates succeeded
    if len(create_receipt.creates) != len(create_ops):
        raise RuntimeError(
            f"Expected {len(create_ops)} creates in receipt, got {len(create_receipt.creates)}"
        )

    # Extract and return entity keys from receipt
    entity_keys = [create.key for create in create_receipt.creates]
    logger.info(f"{label}: Created {len(entity_keys)} entities in bulk transaction")

    return entity_keys


def bulk_update_entities(
    client: "Arkiv", update_ops: list[UpdateOp], label: str = "bulk_update"
) -> TxHash:
    """Update multiple entities in a single bulk transaction.

    Args:
        client: Arkiv client instance
        update_ops: List of UpdateOp operations to execute
        label: Label for transaction hash validation logging

    Returns:
        Transaction hash of the bulk update operation

    Raises:
        RuntimeError: If the number of updates in receipt doesn't match operations
    """
    # Use execute() for bulk update
    update_operations = Operations(updates=update_ops)
    update_receipt = client.arkiv.execute(update_operations)

    # Check transaction hash of bulk update
    check_tx_hash(label, update_receipt)

    # Verify all updates succeeded
    if len(update_receipt.updates) != len(update_ops):
        raise RuntimeError(
            f"Expected {len(update_ops)} updates in receipt, got {len(update_receipt.updates)}"
        )

    logger.info(f"{label}: Updated {len(update_ops)} entities in bulk transaction")

    return update_receipt.tx_hash


def bulk_extend_entities(
    client: "Arkiv", extend_ops: list[ExtendOp], label: str = "bulk_extend"
) -> TransactionReceipt:
    """Extend multiple entities in a single bulk transaction.

    Args:
        client: Arkiv client instance
        extend_ops: List of ExtendOp operations to execute
        label: Label for transaction hash validation logging

    Returns:
        Transaction hash of the bulk extend operation

    Raises:
        RuntimeError: If the number of extensions in receipt doesn't match operations
    """
    # Use execute() for bulk extend
    extend_operations = Operations(extensions=extend_ops)
    extend_receipt = client.arkiv.execute(extend_operations)

    # Check transaction hash of bulk extend
    check_tx_hash(label, extend_receipt)

    # Verify all extensions succeeded
    if len(extend_receipt.extensions) != len(extend_ops):
        raise RuntimeError(
            f"Expected {len(extend_ops)} extensions in receipt, got {len(extend_receipt.extensions)}"
        )

    logger.info(f"{label}: Extended {len(extend_ops)} entities in bulk transaction")

    return extend_receipt


def bulk_delete_entities(
    client: "Arkiv", delete_ops: list[DeleteOp], label: str = "bulk_delete"
) -> TransactionReceipt:
    """Delete multiple entities in a single bulk transaction.

    Args:
        client: Arkiv client instance
        delete_ops: List of DeleteOp operations to execute
        label: Label for transaction hash validation logging

    Returns:
        Transaction hash of the bulk delete operation

    Raises:
        RuntimeError: If the number of deletes in receipt doesn't match operations
    """
    # Use execute() for bulk delete
    delete_operations = Operations(deletes=delete_ops)
    delete_receipt = client.arkiv.execute(delete_operations)

    # Check transaction hash of bulk delete
    check_tx_hash(label, delete_receipt)

    # Verify all deletes succeeded
    if len(delete_receipt.deletes) != len(delete_ops):
        raise RuntimeError(
            f"Expected {len(delete_ops)} deletes in receipt, got {len(delete_receipt.deletes)}"
        )

    logger.info(f"{label}: Deleted {len(delete_ops)} entities in bulk transaction")

    return delete_receipt


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
