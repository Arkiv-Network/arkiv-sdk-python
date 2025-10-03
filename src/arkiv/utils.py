"""Utility methods."""

import logging
from typing import Any

import rlp  # type: ignore[import-untyped]
from eth_typing import HexStr
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from web3.contract.base_contract import BaseContractEvent
from web3.types import EventData, LogReceipt, TxParams, TxReceipt

from . import contract
from .contract import STORAGE_ADDRESS
from .exceptions import AnnotationException, EntityKeyException
from .types import (
    Annotations,
    CreateReceipt,
    DeleteReceipt,
    EntityKey,
    ExtendReceipt,
    NumericAnnotations,
    NumericAnnotationsRlp,
    Operations,
    StringAnnotations,
    StringAnnotationsRlp,
    TransactionReceipt,
    TxHash,
    UpdateReceipt,
)

logger = logging.getLogger(__name__)


def to_entity_key(entity_key_int: int) -> EntityKey:
    hex_value = Web3.to_hex(entity_key_int)
    # ensure lenth is 66 (0x + 64 hex)
    if len(hex_value) < 66:
        hex_value = HexStr("0x" + hex_value[2:].zfill(64))
    return EntityKey(hex_value)


def entity_key_to_bytes(entity_key: EntityKey) -> bytes:
    return bytes.fromhex(entity_key[2:])  # Strip '0x' prefix and convert to bytes


def check_entity_key(entity_key: Any | None, label: str | None = None) -> None:
    """Validates entity key."""
    prefix = ""
    if label:
        prefix = f"{label}: "

    logger.info(f"{prefix}Checking entity key {entity_key}")

    if entity_key is None:
        raise EntityKeyException("Entity key should not be None")
    if not isinstance(entity_key, str):
        raise EntityKeyException(
            f"Entity key type should be str but is: {type(entity_key)}"
        )
    if len(entity_key) != 66:
        raise EntityKeyException(
            f"Entity key should be 66 characters long (0x + 64 hex) but is: {len(entity_key)}"
        )
    if not is_hex_str(entity_key):
        raise EntityKeyException("Entity key should be a valid hex string")


def is_entity_key(entity_key: Any | None) -> bool:
    """Check if the provided value is a valid EntityKey."""
    try:
        check_entity_key(entity_key)
        return True
    except EntityKeyException:
        return False


def is_hex_str(value: str) -> bool:
    if not isinstance(value, str):
        return False
    if value.startswith("0x"):
        value = value[2:]
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def to_tx_params(
    operations: Operations,
    tx_params: TxParams | None = None,
) -> TxParams:
    """
    Convert Operations to TxParams for Arkiv contract interaction.

    Args:
        operations: Arkiv operations to encode
        tx_params: Optional additional transaction parameters

    Returns:
        TxParams ready for Web3.py transaction sending to Arkiv storage contract

    Note: 'to', 'value', and 'data' from tx_params will be overridden.
    """
    if not tx_params:
        tx_params = {}

    # Merge provided tx_params with encoded transaction data
    tx_params |= {
        "to": STORAGE_ADDRESS,
        "value": Web3.to_wei(0, "ether"),
        "data": rlp_encode_transaction(operations),
    }

    return tx_params


def to_hex_bytes(tx_hash: TxHash) -> HexBytes:
    """
    Convert a TxHash to HexBytes for Web3.py methods that require it.

    Args:
        tx_hash: Transaction hash as TxHash

    Returns:
        Transaction hash as HexBytes with utility methods

    Example:
        tx_hash: TxHash = client.arkiv.create_entity(...)
        hex_bytes = to_hex_bytes(tx_hash)
    """
    return HexBytes(tx_hash)


def to_receipt(
    contract_: Contract, tx_hash_: TxHash | HexBytes, tx_receipt: TxReceipt
) -> TransactionReceipt:
    """Convert a tx hash and a raw transaction receipt to a typed receipt."""
    logger.debug(f"Transaction receipt: {tx_receipt}")

    # normalize tx_hash to TxHash if needed
    tx_hash: TxHash = (
        tx_hash_
        if isinstance(tx_hash_, str)
        else TxHash(HexStr(HexBytes(tx_hash_).to_0x_hex()))
    )

    # Initialize receipt with tx hash and empty receipt collections
    creates: list[CreateReceipt] = []
    updates: list[UpdateReceipt] = []
    extensions: list[ExtendReceipt] = []
    deletes: list[DeleteReceipt] = []

    receipt = TransactionReceipt(
        tx_hash=tx_hash,
        creates=creates,
        updates=updates,
        extensions=extensions,
        deletes=deletes,
    )

    logs: list[LogReceipt] = tx_receipt["logs"]
    for log in logs:
        try:
            event_data: EventData = get_event_data(contract_, log)
            event_args: dict[str, Any] = event_data["args"]
            event_name = event_data["event"]

            entity_key: EntityKey = to_entity_key(event_args["entityKey"])

            match event_name:
                case contract.CREATED_EVENT:
                    expiration_block: int = event_args["expirationBlock"]
                    creates.append(
                        CreateReceipt(
                            entity_key=entity_key,
                            expiration_block=expiration_block,
                        )
                    )
                case contract.UPDATED_EVENT:
                    expiration_block = event_args["expirationBlock"]
                    updates.append(
                        UpdateReceipt(
                            entity_key=entity_key,
                            expiration_block=expiration_block,
                        )
                    )
                case contract.DELETED_EVENT:
                    deletes.append(
                        DeleteReceipt(
                            entity_key=entity_key,
                        )
                    )
                case contract.EXTENDED_EVENT:
                    extensions.append(
                        ExtendReceipt(
                            entity_key=entity_key,
                            old_expiration_block=event_args["oldExpirationBlock"],
                            new_expiration_block=event_args["newExpirationBlock"],
                        )
                    )
                case _:
                    logger.warning(f"Unknown event type: {event_name}")
        except Exception:
            # Skip logs that don't match our contract events
            continue

    return receipt


def get_event_data(contract: Contract, log: LogReceipt) -> EventData:
    """Extract the event data from a log receipt (Web3 standard)."""
    logger.debug(f"Log: {log}")

    # Get log topic if present
    topics = log.get("topics", [])
    if len(topics) > 0:
        topic = topics[0].to_0x_hex()

        # Get event data for topic
        event: BaseContractEvent = contract.get_event_by_topic(topic)
        event_data: EventData = event.process_log(log)
        logger.debug(f"Event data: {event_data}")

        return event_data

    # No topic -> no event data
    raise ValueError("No topic/event data found in log")


def rlp_encode_transaction(tx: Operations) -> bytes:
    """Encode a transaction in RLP."""

    # Turn the transaction into a list for RLP encoding
    payload = [
        # Create
        [
            [
                element.btl,
                element.payload,
                *split_annotations(element.annotations),
            ]
            for element in tx.creates
        ],
        # Update
        [
            [
                entity_key_to_bytes(element.entity_key),
                element.btl,
                element.payload,
                *split_annotations(element.annotations),
            ]
            for element in tx.updates
        ],
        # Delete
        [entity_key_to_bytes(element.entity_key) for element in tx.deletes],
        # Extend
        [
            [
                entity_key_to_bytes(element.entity_key),
                element.number_of_blocks,
            ]
            for element in tx.extensions
        ],
    ]
    logger.debug("Payload: %s", payload)
    encoded: bytes = rlp.encode(payload)
    logger.debug("Encoded payload: %s", encoded)
    return encoded


def split_annotations(
    annotations: Annotations | None = None,
) -> tuple[StringAnnotationsRlp, NumericAnnotationsRlp]:
    """Helper to split mixed annotations into string and numeric lists."""
    string_annotations: StringAnnotationsRlp = StringAnnotationsRlp([])
    numeric_annotations: NumericAnnotationsRlp = NumericAnnotationsRlp([])

    if annotations:
        for key, value in annotations.items():
            if isinstance(value, int):
                if value < 0:
                    raise AnnotationException(
                        f"Numeric annotations must be non-negative but found '{value}' for key '{key}'"
                    )

                numeric_annotations.append((key, value))
            else:
                string_annotations.append((key, value))

    logger.debug(
        f"Split annotations into {string_annotations} and {numeric_annotations}"
    )
    return string_annotations, numeric_annotations


def merge_annotations(
    string_annotations: StringAnnotations | None = None,
    numeric_annotations: NumericAnnotations | None = None,
) -> Annotations:
    """Helper to merge string and numeric annotations into mixed annotations."""
    annotations: Annotations = Annotations({})

    if string_annotations:
        # example: [AttributeDict({'key': 'type', 'value': 'Greeting'})]
        for element in string_annotations:
            logger.debug(f"String annotation element: {element}")
            if isinstance(element.value, str):
                annotations[element.key] = element.value
            else:
                logger.warning(
                    f"Unexpected string annotation, expected (str, str) but found: {element}, skipping ..."
                )

    if numeric_annotations:
        # example: [AttributeDict({'key': 'version', 'value': 1})]
        for element in numeric_annotations:
            logger.debug(f"Numeric annotation element: {element}")
            if isinstance(element.value, int):
                annotations[element.key] = element.value
            else:
                logger.warning(
                    f"Unexpected numeric annotation, expected (str, int) but found: {element}, skipping ..."
                )

    return annotations
