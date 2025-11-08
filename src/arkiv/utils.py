"""Utility methods."""

from __future__ import annotations

import logging
from typing import Any

import brotli  # type: ignore[import-untyped]
import rlp  # type: ignore[import-untyped]
from eth_typing import BlockNumber, ChecksumAddress, HexStr
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from web3.contract.base_contract import BaseContractEvent
from web3.types import EventData, LogReceipt, TxParams, TxReceipt

from . import contract
from .contract import (
    COST,
    ENTITY_KEY,
    EXPIRATION_BLOCK,
    NEW_EXPIRATION_BLOCK,
    NEW_OWNER_ADDRESS,
    OLD_EXPIRATION_BLOCK,
    OLD_OWNER_ADDRESS,
    OWNER_ADDRESS,
    STORAGE_ADDRESS,
)
from .exceptions import AttributeException, EntityKeyException
from .types import (
    ALL,
    ATTRIBUTES,
    CONTENT_TYPE,
    CREATED_AT,
    EXPIRATION,
    KEY,
    LAST_MODIFIED_AT,
    MAX_RESULTS_PER_PAGE_DEFAULT,
    OP_INDEX_IN_TX,
    OWNER,
    PAYLOAD,
    TX_INDEX_IN_BLOCK,
    Attributes,
    ChangeOwnerEvent,
    CreateEvent,
    CreateOp,
    Cursor,
    DeleteEvent,
    Entity,
    EntityKey,
    ExpiryEvent,
    ExtendEvent,
    NumericAttributes,
    NumericAttributesRlp,
    Operations,
    QueryOptions,
    QueryPage,
    StringAttributes,
    StringAttributesRlp,
    TransactionReceipt,
    TxHash,
    UpdateEvent,
    UpdateOp,
)

CONTENT_TYPE_DEFAULT = "application/octet-stream"
BTL_DEFAULT = (
    1000  # Default blocks to live for created entities (~30 mins with 2s blocks)
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


def to_create_op(
    payload: bytes | None = None,
    content_type: str | None = None,
    attributes: Attributes | None = None,
    btl: int | None = None,
) -> CreateOp:
    payload, content_type, attributes, btl = check_and_set_entity_op_defaults(
        payload, content_type, attributes, btl
    )
    return CreateOp(
        payload=payload, content_type=content_type, attributes=attributes, btl=btl
    )


def to_update_op(
    entity_key: EntityKey,
    payload: bytes | None = None,
    content_type: str | None = None,
    attributes: Attributes | None = None,
    btl: int | None = None,
) -> UpdateOp:
    payload, content_type, attributes, btl = check_and_set_entity_op_defaults(
        payload, content_type, attributes, btl
    )
    return UpdateOp(
        key=entity_key,
        content_type=content_type,
        btl=btl,
        payload=payload,
        attributes=attributes,
    )


def check_and_set_entity_op_defaults(
    payload: bytes | None,
    content_type: str | None,
    attributes: Attributes | None,
    btl: int | None,
) -> tuple[bytes, str, Attributes, int]:
    """Check and set defaults for entity management arguments."""
    if btl is None:
        btl = BTL_DEFAULT
    if not payload:
        payload = b""
    if not content_type:
        content_type = CONTENT_TYPE_DEFAULT
    if not attributes:
        attributes = Attributes({})

    return payload, content_type, attributes, btl


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
    data = rlp_encode_transaction(operations)
    data_compressed = brotli.compress(data)

    tx_params |= {
        "to": STORAGE_ADDRESS,
        "value": Web3.to_wei(0, "ether"),
        "data": data_compressed,
    }

    return tx_params


def to_query_options(
    fields: int = ALL,  # Bitmask of fields to populate
    max_results_per_page: int = MAX_RESULTS_PER_PAGE_DEFAULT,
    at_block: int | None = None,
    cursor: Cursor | None = None,
) -> QueryOptions:
    """
    Validates query options and returns them as QueryOptions.

    Args:
        fields: Bitmask of fields to populate
        max_results_per_page: Maximum number of results to return
        at_block: Block number for the query or None for latest available block
        cursor: Cursor for pagination

    Returns:
        QueryOptions instance
    """

    logger.info(
        f"max_results_per_page={max_results_per_page}, at_block={at_block}, cursor={cursor}"
    )

    # Validations
    if fields is not None and fields < 0:
        raise ValueError(f"Fields bitmask cannot be negative: {fields}")

    if fields is not None and fields > ALL:
        raise ValueError(f"Fields bitmask contains unknown field flags: {fields}")

    if max_results_per_page is not None and max_results_per_page <= 0:
        raise ValueError(
            f"max_results_per_page cannot be negative or zero: {max_results_per_page}"
        )

    if at_block is not None and at_block < 0:
        raise ValueError(f"at_block cannot be negative: {at_block}")

    return QueryOptions(
        fields=fields,
        max_results_per_page=max_results_per_page,
        at_block=at_block,
        cursor=cursor,
    )


def to_rpc_query_options(
    options: QueryOptions | None = None,
) -> dict[str, Any]:
    """
    Convert QueryOptions to a dictionary for RPC calls.

    Args:
        options: QueryOptions instance

    Returns:
        Dictionary representation of the query options
    """
    if not options:
        options = QueryOptions()

    # see https://github.com/Golem-Base/golembase-op-geth/blob/main/eth/api_arkiv.go
    rpc_query_options: dict[str, Any] = {
        "includeData": {
            "key": options.fields & KEY != 0,
            "attributes": options.fields & ATTRIBUTES != 0,
            "payload": options.fields & PAYLOAD != 0,
            "contentType": options.fields & CONTENT_TYPE != 0,
            "expiration": options.fields & EXPIRATION != 0,
            "owner": options.fields & OWNER != 0,
            "createdAtBlock": options.fields & CREATED_AT != 0,
            "lastModifiedAtBlock": options.fields & LAST_MODIFIED_AT != 0,
            "transactionIndexInBlock": options.fields & TX_INDEX_IN_BLOCK != 0,
            "operationIndexInTransaction": options.fields & OP_INDEX_IN_TX != 0,
        }
    }

    if options.at_block is not None:
        rpc_query_options["atBlock"] = options.at_block
    else:
        rpc_query_options["atBlock"] = None

    if options.max_results_per_page is not None:
        rpc_query_options["resultsPerPage"] = options.max_results_per_page

    if options.cursor is not None:
        rpc_query_options["cursor"] = options.cursor

    return rpc_query_options


def to_entity(fields: int, response_item: dict[str, Any]) -> Entity:
    """Convert a low-level RPC query response to a high-level Entity."""

    logger.debug(f"Item: {response_item}")

    # Set defaults
    entity_key: EntityKey | None = None
    owner: ChecksumAddress | None = None
    created_at_block: int | None = None
    last_modified_at_block: int | None = None
    expires_at_block: int | None = None
    transaction_index: int | None = None
    operation_index: int | None = None
    payload: bytes | None = None
    content_type: str | None = None
    attributes: Attributes | None = None

    # Extract entity key if present
    if fields & KEY != 0:
        if not hasattr(response_item, "key"):
            raise ValueError("RPC query response item missing 'key' field")
        entity_key = EntityKey(response_item.key)

    # Extract owner if present
    if fields & OWNER != 0:
        if not hasattr(response_item, "owner"):
            raise ValueError("RPC query response item missing 'owner' field")
        owner = Web3.to_checksum_address(response_item.owner)

    # Extract created_at if present
    if fields & CREATED_AT != 0:
        if not hasattr(response_item, "createdAtBlock"):
            raise ValueError("RPC query response item missing 'createdAtBlock' field")
        created_at_block = int(response_item.createdAtBlock)

    # Extract last_modified_at if present
    if fields & LAST_MODIFIED_AT != 0:
        if not hasattr(response_item, "lastModifiedAtBlock"):
            raise ValueError(
                "RPC query response item missing 'lastModifiedAtBlock' field"
            )
        last_modified_at_block = int(response_item.lastModifiedAtBlock)

    # Extract expiration if present
    if fields & EXPIRATION != 0:
        if not hasattr(response_item, "expiresAt"):
            raise ValueError("RPC query response item missing 'expiresAt' field")
        expires_at_block = int(response_item.expiresAt)

    # Extract transaction index if present
    if fields & TX_INDEX_IN_BLOCK != 0:
        if not hasattr(response_item, "transactionIndexInBlock"):
            raise ValueError(
                "RPC query response item missing 'transactionIndexInBlock' field"
            )
        transaction_index = int(response_item.transactionIndexInBlock)

    # Extract operation index if present
    if fields & OP_INDEX_IN_TX != 0:
        if not hasattr(response_item, "operationIndexInTransaction"):
            raise ValueError(
                "RPC query response item missing 'operationIndexInTransaction' field"
            )
        operation_index = int(response_item.operationIndexInTransaction)

    # Extract payload if present
    if fields & PAYLOAD != 0:
        if not hasattr(response_item, "value"):
            payload = b""
        else:
            payload = bytes.fromhex(
                response_item.value[2:]
                if response_item.value.startswith("0x")
                else response_item.value
            )

    # Extract content type if present
    if fields & CONTENT_TYPE != 0:
        if not hasattr(response_item, "contentType"):
            raise ValueError("RPC query response item missing 'contentType' field")
        content_type = response_item.contentType

    # Extract and merge attributes if present
    if fields & ATTRIBUTES != 0:
        string_attributes = (
            response_item.stringAttributes
            if hasattr(response_item, "stringAttributes")
            else None
        )
        numeric_attributes = (
            response_item.numericAttributes
            if hasattr(response_item, "numericAttributes")
            else None
        )
        attributes = merge_attributes(string_attributes, numeric_attributes)

    entity = Entity(
        key=entity_key,
        fields=fields,
        owner=owner,
        created_at_block=created_at_block,
        last_modified_at_block=last_modified_at_block,
        expires_at_block=expires_at_block,
        transaction_index=transaction_index,
        operation_index=operation_index,
        payload=payload,
        content_type=content_type,
        attributes=attributes,
    )

    return entity


def to_query_result(fields: int, rpc_query_response: dict[str, Any]) -> QueryPage:
    """Convert a low-level RPC query response to a high-level QueryResult."""

    logger.info(f"Raw query result(s): {rpc_query_response}")
    if not rpc_query_response:
        raise ValueError("RPC query response is empty")

    # Get and check response (element) data
    if not hasattr(rpc_query_response, "data"):
        raise ValueError("RPC query response missing 'data' field")

    response_data = rpc_query_response["data"]
    if not isinstance(response_data, list):
        raise ValueError("RPC query response 'data' field is not an array")

    entities: list[Entity] = []
    for item in response_data:
        entity = to_entity(fields, item)
        entities.append(entity)

    # Extract block number from rpc_query_response. Raises exception when element is missing.
    if not hasattr(rpc_query_response, "blockNumber"):
        raise ValueError("RPC query response missing 'blockNumber' field")

    block_number: int = rpc_query_response["blockNumber"]

    # Extracts cursor from rpc_query_response. Sets cursor to None if element is missing.
    cursor: Cursor | None = (
        rpc_query_response["cursor"] if "cursor" in rpc_query_response else None
    )

    query_result = QueryPage(
        entities=entities, block_number=block_number, cursor=cursor
    )

    logger.debug(f"Query result: {query_result}")
    return query_result


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


def get_tx_hash(log: LogReceipt) -> TxHash:
    """
    Extract the TxHash from a log receipt.

    Args:
        log: Log receipt from which to extract the transaction hash

    Returns:
        Transaction hash as TxHash
    """
    tx_hash_raw = log["transactionHash"]

    if isinstance(tx_hash_raw, bytes):
        return TxHash(HexStr("0x" + tx_hash_raw.hex()))

    return TxHash(HexStr(tx_hash_raw))


def to_event(
    contract_: Contract, log: LogReceipt
) -> (
    CreateEvent
    | UpdateEvent
    | ExpiryEvent
    | DeleteEvent
    | ExtendEvent
    | ChangeOwnerEvent
    | None
):
    """Convert a log receipt to event object."""
    logger.debug(f"Log: {log}")

    # Check if this is already processed EventData (has 'event' and 'args' keys)
    # or a raw log that needs processing
    if "event" in log and "args" in log:
        # Already an EventData structure
        event_data: EventData = log  # type: ignore[assignment]
    else:
        # Raw log - process it
        logger.debug("Processing raw log for event conversion")
        event_data = get_event_data(contract_, log)

    event_args: dict[str, Any] = event_data["args"]
    event_name = event_data["event"]

    entity_key: EntityKey = to_entity_key(event_args[ENTITY_KEY])
    logger.debug(
        f"Processing event: {event_name}, entity_key: {entity_key}, owner_address: {event_args.get('ownerAddress')}"
    )

    match event_name:
        case contract.CREATED_EVENT:
            return CreateEvent(
                key=entity_key,
                owner_address=ChecksumAddress(event_args[OWNER_ADDRESS]),
                expiration_block=event_args[EXPIRATION_BLOCK],
                cost=int(event_args[COST]),
            )
        case contract.UPDATED_EVENT:
            return UpdateEvent(
                key=entity_key,
                owner_address=ChecksumAddress(event_args[OWNER_ADDRESS]),
                old_expiration_block=event_args[OLD_EXPIRATION_BLOCK],
                new_expiration_block=event_args[NEW_EXPIRATION_BLOCK],
                cost=int(event_args[COST]),
            )
        case contract.EXPIRED_EVENT:
            return ExpiryEvent(
                key=entity_key,
                owner_address=ChecksumAddress(event_args[OWNER_ADDRESS]),
            )
        case contract.DELETED_EVENT:
            return DeleteEvent(
                key=entity_key,
                owner_address=ChecksumAddress(event_args[OWNER_ADDRESS]),
            )
        case contract.EXTENDED_EVENT:
            return ExtendEvent(
                key=entity_key,
                owner_address=ChecksumAddress(event_args[OWNER_ADDRESS]),
                old_expiration_block=event_args[OLD_EXPIRATION_BLOCK],
                new_expiration_block=event_args[NEW_EXPIRATION_BLOCK],
                cost=int(event_args[COST]),
            )
        case contract.OWNER_CHANGED_EVENT:
            return ChangeOwnerEvent(
                key=entity_key,
                old_owner_address=event_args[OLD_OWNER_ADDRESS],
                new_owner_address=event_args[NEW_OWNER_ADDRESS],
            )
        # Legacy events - skip with info log
        case contract.CREATED_EVENT_LEGACY:
            logger.debug(f"Skipping legacy event: {event_name}")
            return None
        case contract.UPDATED_EVENT_LEGACY:
            logger.debug(f"Skipping legacy event: {event_name}")
            return None
        case contract.DELETED_EVENT_LEGACY:
            logger.debug(f"Skipping legacy event: {event_name}")
            return None
        case contract.EXTENDED_EVENT_LEGACY:
            logger.debug(f"Skipping legacy event: {event_name}")
            return None
        # Unknown events - return None with warning log
        case _:
            logger.warning(f"Unknown event type: {event_name}")
            return None


def to_receipt(
    contract_: Contract, tx_hash_: TxHash | HexBytes, tx_receipt: TxReceipt
) -> TransactionReceipt:
    """Convert a tx hash and a raw transaction receipt to a typed receipt."""
    logger.debug(f"Transaction receipt: {tx_receipt}")

    # Extract block number
    block_number_raw = tx_receipt.get("blockNumber")
    if block_number_raw is None:
        raise ValueError("Transaction receipt missing blockNumber")
    block_number: BlockNumber = BlockNumber(block_number_raw)

    # normalize tx_hash to TxHash if needed
    tx_hash: TxHash = (
        tx_hash_
        if isinstance(tx_hash_, str)
        else TxHash(HexStr(HexBytes(tx_hash_).to_0x_hex()))
    )

    # Initialize receipt with tx hash and empty event collections
    creates: list[CreateEvent] = []
    updates: list[UpdateEvent] = []
    extensions: list[ExtendEvent] = []
    deletes: list[DeleteEvent] = []
    change_owners: list[ChangeOwnerEvent] = []

    receipt = TransactionReceipt(
        block_number=block_number,
        tx_hash=tx_hash,
        creates=creates,
        updates=updates,
        extensions=extensions,
        deletes=deletes,
        change_owners=change_owners,
    )

    logs: list[LogReceipt] = tx_receipt["logs"]
    for log in logs:
        try:
            event_data: EventData = get_event_data(contract_, log)
            event_name = event_data["event"]
            event = to_event(contract_, log)
            if event is None:
                continue
            match event_name:
                case contract.CREATED_EVENT:
                    if isinstance(event, CreateEvent):
                        creates.append(event)
                case contract.UPDATED_EVENT:
                    if isinstance(event, UpdateEvent):
                        updates.append(event)
                case contract.EXPIRED_EVENT:
                    logger.warning(f"Not yet implemented: {event_name}")
                case contract.DELETED_EVENT:
                    if isinstance(event, DeleteEvent):
                        deletes.append(event)
                case contract.EXTENDED_EVENT:
                    if isinstance(event, ExtendEvent):
                        extensions.append(event)
                case contract.OWNER_CHANGED_EVENT:
                    if isinstance(event, ChangeOwnerEvent):
                        change_owners.append(event)
                case contract.CREATED_EVENT_LEGACY:
                    logger.debug(f"Skipping legacy event: {event_name}")
                case contract.UPDATED_EVENT_LEGACY:
                    logger.debug(f"Skipping legacy event: {event_name}")
                case contract.DELETED_EVENT_LEGACY:
                    logger.debug(f"Skipping legacy event: {event_name}")
                case contract.EXTENDED_EVENT_LEGACY:
                    logger.debug(f"Skipping legacy event: {event_name}")
                # Unknown events - skip with warning log
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
        # Handle both HexBytes and string topics
        topic_value = topics[0]
        if isinstance(topic_value, str):
            topic = topic_value
        else:
            topic = topic_value.to_0x_hex()

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
                element.content_type,
                element.payload,
                *split_attributes(element.attributes),
            ]
            for element in tx.creates
        ],
        # Update
        [
            [
                entity_key_to_bytes(element.key),
                element.content_type,
                element.btl,
                element.payload,
                *split_attributes(element.attributes),
            ]
            for element in tx.updates
        ],
        # Delete
        [entity_key_to_bytes(element.key) for element in tx.deletes],
        # Extend
        [
            [
                entity_key_to_bytes(element.key),
                element.number_of_blocks,
            ]
            for element in tx.extensions
        ],
        # ChangeOwner
        [
            [
                entity_key_to_bytes(element.key),
                bytes.fromhex(element.new_owner[2:]),  # Convert address to bytes
            ]
            for element in tx.change_owners
        ],
    ]
    logger.debug("Payload: %s", payload)
    encoded: bytes = rlp.encode(payload)
    logger.debug("Encoded payload: %s", encoded)
    return encoded


def split_attributes(
    attributes: Attributes | None = None,
) -> tuple[StringAttributesRlp, NumericAttributesRlp]:
    """Helper to split mixed attributes into string and numeric lists."""
    string_attributes: StringAttributesRlp = StringAttributesRlp([])
    numeric_attributes: NumericAttributesRlp = NumericAttributesRlp([])

    if attributes:
        for key, value in attributes.items():
            if isinstance(value, int):
                if value < 0:
                    raise AttributeException(
                        f"Numeric attributes must be non-negative but found '{value}' for key '{key}'"
                    )

                numeric_attributes.append((key, value))
            else:
                string_attributes.append((key, value))

    logger.debug(f"Split attributes into {string_attributes} and {numeric_attributes}")
    return string_attributes, numeric_attributes


def merge_attributes(
    string_attributes: StringAttributes | None = None,
    numeric_attributes: NumericAttributes | None = None,
) -> Attributes:
    """Helper to merge string and numeric attributes into mixed attributes."""
    attributes: Attributes = Attributes({})

    if string_attributes:
        # example: [AttributeDict({'key': 'type', 'value': 'Greeting'})]
        for element in string_attributes:
            logger.debug(f"String attribute element: {element}")
            # Filter out system attributes
            if element.key.startswith("$"):
                continue

            if isinstance(element.value, str):
                attributes[element.key] = element.value
            else:
                logger.warning(
                    f"Unexpected string attribute, expected (str, str) but found: {element}, skipping ..."
                )

    if numeric_attributes:
        # example: [AttributeDict({'key': 'version', 'value': 1})]
        for element in numeric_attributes:
            logger.debug(f"Numeric attribute element: {element}")
            # Filter out system attributes
            if element.key.startswith("$"):
                continue

            if isinstance(element.value, int):
                attributes[element.key] = element.value
            else:
                logger.warning(
                    f"Unexpected numeric attribute, expected (str, int) but found: {element}, skipping ..."
                )

    return attributes
