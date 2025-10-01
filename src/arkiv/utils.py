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
from .exceptions import EntityKeyException
from .types import (
    Annotation,
    AnnotationValue,
    CreateOp,
    CreateReceipt,
    DeleteReceipt,
    EntityKey,
    ExtendReceipt,
    Operations,
    TransactionReceipt,
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


def to_create_operation(
    payload: bytes | None = None,
    annotations: dict[str, AnnotationValue] | None = None,
    btl: int = 0,
) -> CreateOp:
    """
    Build a CreateOp for creating a single entity.

    Args:
        payload: Optional entity data payload
        annotations: Optional key-value annotations
        btl: Blocks to live (default: 0)

    Returns:
        CreateOp object ready to be used in Operations
    """
    # Ensure we have valid data
    if not payload:
        payload = b""

    # Separate string and numeric annotations
    string_annotations, numeric_annotations = split_annotations(annotations)

    # Build and return CreateOp
    return CreateOp(
        data=payload,
        btl=btl,
        string_annotations=string_annotations,
        numeric_annotations=numeric_annotations,
    )


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


def to_receipt(
    contract_: Contract, tx_hash: HexBytes, tx_receipt: TxReceipt
) -> TransactionReceipt:
    """Convert a tx hash and a raw transaction receipt to a typed receipt."""
    logger.debug(f"Transaction receipt: {tx_receipt}")

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
            expiration_block: int = event_args["expirationBlock"]

            match event_name:
                case contract.CREATED_EVENT:
                    creates.append(
                        CreateReceipt(
                            entity_key=entity_key,
                            expiration_block=expiration_block,
                        )
                    )
                case contract.UPDATED_EVENT:
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

    def format_annotation(annotation: Annotation) -> tuple[str, AnnotationValue]:
        return (annotation.key, annotation.value)

    # Turn the transaction into a list for RLP encoding
    payload = [
        # Create
        [
            [
                element.btl,
                element.data,
                list(map(format_annotation, element.string_annotations)),
                list(map(format_annotation, element.numeric_annotations)),
            ]
            for element in tx.creates
        ],
        # Update
        [
            [
                entity_key_to_bytes(element.entity_key),
                element.btl,
                element.data,
                list(map(format_annotation, element.string_annotations)),
                list(map(format_annotation, element.numeric_annotations)),
            ]
            for element in tx.updates
        ],
        # Delete
        [
            [
                entity_key_to_bytes(element.entity_key),
            ]
            for element in tx.deletes
        ],
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
    annotations: dict[str, AnnotationValue] | None = None,
) -> tuple[list[Annotation], list[Annotation]]:
    """Helper to split mixed annotations into string and numeric lists."""
    string_annotations = []
    numeric_annotations = []

    if annotations:
        for key, value in annotations.items():
            annotation = Annotation(key=key, value=value)
            if isinstance(value, str):
                string_annotations.append(annotation)
            elif isinstance(value, int):
                numeric_annotations.append(annotation)

    return string_annotations, numeric_annotations


def merge_annotations(
    string_annotations: list[Annotation] | None = None,
    numeric_annotations: list[Annotation] | None = None,
) -> dict[str, AnnotationValue]:
    """Helper to merge string and numeric annotations into a single dictionary."""
    annotations: dict[str, AnnotationValue] = {}

    if string_annotations:
        for annotation in string_annotations:
            annotations[annotation.key] = annotation.value

    if numeric_annotations:
        for annotation in numeric_annotations:
            annotations[annotation.key] = annotation.value

    return annotations
