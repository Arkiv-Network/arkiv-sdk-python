"""Utility methods."""

from __future__ import annotations

import logging
from typing import Any

from eth_typing import BlockNumber, ChecksumAddress, HexStr
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from web3.contract.base_contract import BaseContractEvent
from web3.types import EventData, LogReceipt, TxReceipt

from . import contract
from .contract import (
    ARKIV_ADDRESS,
    ATTR_STRING,
    ATTR_UINT,
    CHANGESET_HASH_UPDATE_EVENT,
    ENTITY_KEY,
    ENTITY_OPERATION_EVENT,
    EXPIRES_AT,
    OPERATION_TYPE,
    OWNER as OWNER_FIELD,
    OP_TYPE_CREATE,
    OP_TYPE_DELETE,
    OP_TYPE_EXPIRE,
    OP_TYPE_EXTEND,
    OP_TYPE_TRANSFER,
    OP_TYPE_UPDATE,
)
from .exceptions import AttributeException, EntityKeyException
from .types import (
    ALL,
    ATTRIBUTES,
    CONTENT_TYPE,
    CREATED_AT,
    DESC,
    EXPIRATION,
    KEY,
    LAST_MODIFIED_AT,
    MAX_RESULTS_PER_PAGE_DEFAULT,
    OP_INDEX_IN_TX,
    OWNER,
    PAYLOAD,
    STR,
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
    Operations,
    QueryOptions,
    QueryPage,
    StringAttributes,
    NumericAttributes,
    TransactionReceipt,
    TxHash,
    UpdateEvent,
    UpdateOp,
)

logger = logging.getLogger(__name__)

_ZERO_BYTES32 = bytes(32)
_ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
_EMPTY_MIME128 = {"data": [_ZERO_BYTES32] * 4}


def to_seconds(
    seconds: int = 0, minutes: int = 0, hours: int = 0, days: int = 0
) -> int:
    """
    Convert a time duration to number of seconds.

    Useful for calculating expires_in parameters based on
    desired entity lifetime.

    Args:
        seconds: Number of seconds
        minutes: Number of minutes
        hours: Number of hours
        days: Number of days

    Returns:
        Number of seconds corresponding to the time duration
    """
    total_seconds = seconds + minutes * 60 + hours * 3600 + days * 86400
    return total_seconds


def to_blocks(seconds: int = 0, minutes: int = 0, hours: int = 0, days: int = 0) -> int:
    """
    Convert a time duration to number of blocks.

    Args:
        seconds: Number of seconds
        minutes: Number of minutes
        hours: Number of hours
        days: Number of days

    Returns:
        Number of blocks corresponding to the time duration
    """
    # Import here to avoid circular dependency
    from arkiv.module_base import ArkivModuleBase

    total_seconds = ArkivModuleBase.to_seconds(
        seconds=seconds, minutes=minutes, hours=hours, days=days
    )
    return total_seconds // ArkivModuleBase.BLOCK_TIME_SECONDS


def to_entity_key(entity_key_int: int) -> EntityKey:
    hex_value = Web3.to_hex(entity_key_int)
    # ensure length is 66 (0x + 64 hex)
    if len(hex_value) < 66:
        hex_value = HexStr("0x" + hex_value[2:].zfill(64))
    return EntityKey(hex_value)


def entity_key_to_bytes(entity_key: EntityKey) -> bytes:
    return bytes.fromhex(entity_key[2:])  # Strip '0x' prefix and convert to bytes


def to_create_op(
    payload: bytes | None = None,
    content_type: str | None = None,
    attributes: Attributes | None = None,
    expires_in: int | None = None,
) -> CreateOp:
    payload, content_type, attributes, expires_in = check_and_set_entity_op_defaults(
        payload, content_type, attributes, expires_in
    )
    return CreateOp(
        payload=payload,
        content_type=content_type,
        attributes=attributes,
        expires_in=expires_in,
    )


def to_update_op(
    entity_key: EntityKey,
    payload: bytes | None = None,
    content_type: str | None = None,
    attributes: Attributes | None = None,
    expires_in: int | None = None,
) -> UpdateOp:
    payload, content_type, attributes, expires_in = check_and_set_entity_op_defaults(
        payload, content_type, attributes, expires_in
    )
    return UpdateOp(
        key=entity_key,
        content_type=content_type,
        expires_in=expires_in,
        payload=payload,
        attributes=attributes,
    )


def check_and_set_entity_op_defaults(
    payload: bytes | None,
    content_type: str | None,
    attributes: Attributes | None,
    expires_in: int | None,
) -> tuple[bytes, str, Attributes, int]:
    """Check and set defaults for entity management arguments."""
    if expires_in is None:
        raise ValueError("expires_in must be provided")

    if not payload:
        payload = b""

    if not content_type:
        # Import here to avoid circular dependency
        from arkiv.module_base import ArkivModuleBase

        content_type = ArkivModuleBase.CONTENT_TYPE_DEFAULT

    if not attributes:
        attributes = Attributes({})

    return payload, content_type, attributes, expires_in


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


def _mime128_encode(content_type: str) -> dict[str, Any]:
    """Encode a MIME type string into Mime128 struct (bytes32[4])."""
    raw = content_type.encode("ascii")[:128].ljust(128, b"\x00")
    return {"data": [raw[i * 32 : (i + 1) * 32] for i in range(4)]}


def _ident32_encode(name: str) -> bytes:
    """Encode attribute name as Ident32 (bytes32, ASCII left-aligned, zero-padded)."""
    raw = name.encode("ascii")
    if len(raw) > 32:
        raise AttributeException(f"Attribute name too long (max 32 chars): {name}")
    return raw.ljust(32, b"\x00")


def _attr_value_encode(value: str | int) -> list[bytes]:
    """Encode attribute value into bytes32[4] container."""
    if isinstance(value, int):
        raw = value.to_bytes(32, "big").ljust(128, b"\x00")
    else:
        raw = value.encode("utf-8")[:128].ljust(128, b"\x00")
    return [raw[i * 32 : (i + 1) * 32] for i in range(4)]


def _encode_attributes(attributes: Attributes | None) -> list[dict[str, Any]]:
    """Convert Attributes dict to sorted list of Attribute structs for ABI encoding."""
    if not attributes:
        return []
    result = []
    for key, value in sorted(attributes.items()):
        if isinstance(value, int):
            if value < 0:
                raise AttributeException(
                    f"Numeric attributes must be non-negative but found '{value}' for key '{key}'"
                )
            value_type = ATTR_UINT
        else:
            value_type = ATTR_STRING
        result.append({
            "name": _ident32_encode(key),
            "valueType": value_type,
            "value": _attr_value_encode(value),
        })
    return result


def to_contract_ops(operations: Operations, current_block: int) -> list[dict[str, Any]]:
    """Convert Operations to ABI-encoded ops list for EntityRegistry.execute()."""
    ops: list[dict[str, Any]] = []

    for op in operations.creates:
        ops.append({
            "operationType": OP_TYPE_CREATE,
            "entityKey":     _ZERO_BYTES32,
            "payload":       op.payload,
            "contentType":   _mime128_encode(op.content_type),
            "attributes":    _encode_attributes(op.attributes),
            "expiresAt":     current_block + to_blocks(seconds=op.expires_in),
            "newOwner":      _ZERO_ADDRESS,
        })

    for op in operations.updates:
        ops.append({
            "operationType": OP_TYPE_UPDATE,
            "entityKey":     entity_key_to_bytes(op.key),
            "payload":       op.payload,
            "contentType":   _mime128_encode(op.content_type),
            "attributes":    _encode_attributes(op.attributes),
            "expiresAt":     0,
            "newOwner":      _ZERO_ADDRESS,
        })

    for op in operations.deletes:
        ops.append({
            "operationType": OP_TYPE_DELETE,
            "entityKey":     entity_key_to_bytes(op.key),
            "payload":       b"",
            "contentType":   _EMPTY_MIME128,
            "attributes":    [],
            "expiresAt":     0,
            "newOwner":      _ZERO_ADDRESS,
        })

    for op in operations.extensions:
        ops.append({
            "operationType": OP_TYPE_EXTEND,
            "entityKey":     entity_key_to_bytes(op.key),
            "payload":       b"",
            "contentType":   _EMPTY_MIME128,
            "attributes":    [],
            "expiresAt":     current_block + to_blocks(seconds=op.extend_by),
            "newOwner":      _ZERO_ADDRESS,
        })

    for op in operations.change_owners:
        ops.append({
            "operationType": OP_TYPE_TRANSFER,
            "entityKey":     entity_key_to_bytes(op.key),
            "payload":       b"",
            "contentType":   _EMPTY_MIME128,
            "attributes":    [],
            "expiresAt":     0,
            "newOwner":      op.new_owner,
        })

    return ops


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
        attributes=fields,
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

    # see https://github.com/Arkiv-Network/arkiv-op-geth/blob/main/eth/api_arkiv.go
    rpc_query_options: dict[str, Any] = {
        "includeData": {
            "key": options.attributes & KEY != 0,
            "attributes": options.attributes & ATTRIBUTES != 0,
            "payload": options.attributes & PAYLOAD != 0,
            "contentType": options.attributes & CONTENT_TYPE != 0,
            "expiration": options.attributes & EXPIRATION != 0,
            "owner": options.attributes & OWNER != 0,
            "createdAtBlock": options.attributes & CREATED_AT != 0,
            "lastModifiedAtBlock": options.attributes & LAST_MODIFIED_AT != 0,
            "transactionIndexInBlock": options.attributes & TX_INDEX_IN_BLOCK != 0,
            "operationIndexInTransaction": options.attributes & OP_INDEX_IN_TX != 0,
        }
    }

    if options.at_block is not None:
        rpc_query_options["atBlock"] = Web3.to_hex(options.at_block)
    else:
        rpc_query_options["atBlock"] = None

    # Determine effective page size: use smaller of max_results_per_page and max_results
    # This avoids requesting more entities than needed when max_results is small
    effective_page_size = options.max_results_per_page
    if options.max_results is not None:
        effective_page_size = min(effective_page_size, options.max_results)

    if effective_page_size is not None:
        rpc_query_options["resultsPerPage"] = Web3.to_hex(effective_page_size)

    if options.cursor is not None:
        rpc_query_options["cursor"] = options.cursor

    if options.order_by is not None:
        rpc_query_options["orderBy"] = [
            {
                "name": ob.attribute,
                "type": "string" if ob.type == STR else "numeric",
                "desc": ob.direction == DESC,
            }
            for ob in options.order_by
        ]

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
        if hasattr(response_item, "createdAtBlock"):
            created_at_block = int(response_item.createdAtBlock)
        else:
            # TODO revert to raise pattern once available
            # raise ValueError("RPC query response item missing 'createdAtBlock' field")
            logger.info("RPC query response item missing 'createdAtBlock' field")

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
        entities=entities, block_number=int(block_number, 16), cursor=cursor
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
        event_data: EventData = log  # type: ignore[assignment]
    else:
        logger.debug("Processing raw log for event conversion")
        event_data = get_event_data(contract_, log)

    event_args: dict[str, Any] = event_data["args"]
    event_name = event_data["event"]

    match event_name:
        case contract.ENTITY_OPERATION_EVENT:
            key = EntityKey(HexStr("0x" + HexBytes(event_args[ENTITY_KEY]).hex()))
            owner = ChecksumAddress(event_args[OWNER_FIELD])
            expires_at = int(event_args[EXPIRES_AT])
            logger.debug(
                f"Processing EntityOperation: op_type={event_args[OPERATION_TYPE]}, "
                f"key={key}, owner={owner}"
            )
            match int(event_args[OPERATION_TYPE]):
                case contract.OP_TYPE_CREATE:
                    return CreateEvent(
                        key=key, owner_address=owner, expiration_block=expires_at
                    )
                case contract.OP_TYPE_UPDATE:
                    return UpdateEvent(
                        key=key, owner_address=owner, expiration_block=expires_at
                    )
                case contract.OP_TYPE_EXTEND:
                    return ExtendEvent(
                        key=key, owner_address=owner, expiration_block=expires_at
                    )
                case contract.OP_TYPE_DELETE:
                    return DeleteEvent(key=key, owner_address=owner)
                case contract.OP_TYPE_TRANSFER:
                    return ChangeOwnerEvent(key=key, new_owner_address=owner)
                case contract.OP_TYPE_EXPIRE:
                    return ExpiryEvent(key=key, owner_address=owner)
                case _:
                    logger.warning(
                        f"Unknown operationType: {event_args[OPERATION_TYPE]}"
                    )
                    return None
        case contract.CHANGESET_HASH_UPDATE_EVENT:
            return None
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
            event = to_event(contract_, log)
            if event is None:
                continue
            if isinstance(event, CreateEvent):
                creates.append(event)
            elif isinstance(event, UpdateEvent):
                updates.append(event)
            elif isinstance(event, DeleteEvent):
                deletes.append(event)
            elif isinstance(event, ExtendEvent):
                extensions.append(event)
            elif isinstance(event, ChangeOwnerEvent):
                change_owners.append(event)
            elif isinstance(event, ExpiryEvent):
                logger.warning("Expiry event received in receipt (not yet handled)")
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
