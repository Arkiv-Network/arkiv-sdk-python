"""Utility methods."""

import logging
from typing import Any

import rlp  # type: ignore[import-untyped]
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from web3.contract.base_contract import BaseContractEvent
from web3.types import EventData, LogReceipt, TxParams, TxReceipt

from . import contract
from .contract import STORAGE_ADDRESS
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

            match event_name:
                case contract.CREATED_EVENT:
                    creates.append(
                        CreateReceipt(
                            entity_key=EntityKey(event_args["entityKey"]),
                            expiration_block=int(event_args["expirationBlock"]),
                        )
                    )
                case contract.UPDATED_EVENT:
                    updates.append(
                        UpdateReceipt(
                            entity_key=EntityKey(event_args["entityKey"]),
                            expiration_block=int(event_args["expirationBlock"]),
                        )
                    )
                case contract.DELETED_EVENT:
                    deletes.append(
                        DeleteReceipt(
                            entity_key=EntityKey(event_args["entityKey"]),
                        )
                    )
                case contract.EXTENDED_EVENT:
                    extensions.append(
                        ExtendReceipt(
                            entity_key=EntityKey(event_args["entityKey"]),
                            old_expiration_block=int(event_args["oldExpirationBlock"]),
                            new_expiration_block=int(event_args["newExpirationBlock"]),
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
                element.entity_key.to_bytes(),
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
                element.entity_key.to_bytes(),
            ]
            for element in tx.deletes
        ],
        # Extend
        [
            [
                element.entity_key.to_bytes(),
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
