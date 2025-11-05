"""Constants used in the Arkiv SDK."""

from collections.abc import Sequence
from typing import Any, Final

from eth_typing import ChecksumAddress
from web3 import Web3
from web3.method import Method, default_root_munger
from web3.types import RPCEndpoint

# ArkivProcessorAddress
STORAGE_ADDRESS: Final[ChecksumAddress] = Web3.to_checksum_address(
    "0x00000000000000000000000000000061726B6976"
)


CREATED_EVENT: Final[str] = "ArkivEntityCreated"
UPDATED_EVENT: Final[str] = "ArkivEntityUpdated"
EXPIRED_EVENT: Final[str] = "ArkivEntityExpired"
DELETED_EVENT: Final[str] = "ArkivEntityDeleted"
EXTENDED_EVENT: Final[str] = "ArkivEntityBTLExtended"
OWNER_CHANGED_EVENT: Final[str] = "ArkivEntityOwnerChanged"

CREATED_EVENT_LEGACY: Final[str] = "GolemBaseStorageEntityCreated"
UPDATED_EVENT_LEGACY: Final[str] = "GolemBaseStorageEntityUpdated"
EXTENDED_EVENT_LEGACY: Final[str] = "GolemBaseStorageEntityBTLExtended"
DELETED_EVENT_LEGACY: Final[str] = "GolemBaseStorageEntityDeleted"


EVENTS: dict[str, str] = {
    "created_legacy": CREATED_EVENT_LEGACY,
    "updated_legacy": UPDATED_EVENT_LEGACY,
    "extended_legacy": EXTENDED_EVENT_LEGACY,
    "deleted_legacy": DELETED_EVENT_LEGACY,
    "created": CREATED_EVENT,
    "updated": UPDATED_EVENT,
    "extended": EXTENDED_EVENT,
    "deleted": DELETED_EVENT,
    "expired": EXPIRED_EVENT,
    "owner_changed": OWNER_CHANGED_EVENT,
}

TYPE_EVENT = "event"
TYPE_UINT = "uint256"
TYPE_ADDRESS = "address"

ENTITY_KEY = "entityKey"

OWNER_ADDRESS = "ownerAddress"
OLD_OWNER_ADDRESS = "oldOwnerAddress"
NEW_OWNER_ADDRESS = "newOwnerAddress"

EXPIRATION_BLOCK = "expirationBlock"
OLD_EXPIRATION_BLOCK = "oldExpirationBlock"
NEW_EXPIRATION_BLOCK = "newExpirationBlock"

COST = "cost"

EVENTS_ABI: Final[Sequence[dict[str, Any]]] = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": ENTITY_KEY, "type": TYPE_UINT},
            {"indexed": False, "name": EXPIRATION_BLOCK, "type": TYPE_UINT},
        ],
        "name": CREATED_EVENT_LEGACY,
        "type": TYPE_EVENT,
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": ENTITY_KEY, "type": TYPE_UINT},
            {"indexed": False, "name": EXPIRATION_BLOCK, "type": TYPE_UINT},
        ],
        "name": UPDATED_EVENT_LEGACY,
        "type": TYPE_EVENT,
    },
    {
        "anonymous": False,
        "inputs": [{"indexed": True, "name": ENTITY_KEY, "type": TYPE_UINT}],
        "name": DELETED_EVENT_LEGACY,
        "type": TYPE_EVENT,
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": ENTITY_KEY, "type": TYPE_UINT},
            {"indexed": False, "name": OLD_EXPIRATION_BLOCK, "type": TYPE_UINT},
            {"indexed": False, "name": NEW_EXPIRATION_BLOCK, "type": TYPE_UINT},
        ],
        "name": EXTENDED_EVENT_LEGACY,
        "type": TYPE_EVENT,
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": ENTITY_KEY, "type": TYPE_UINT},
            {"indexed": True, "name": OWNER_ADDRESS, "type": TYPE_ADDRESS},
            {"indexed": False, "name": EXPIRATION_BLOCK, "type": TYPE_UINT},
            {"indexed": False, "name": COST, "type": TYPE_UINT},
        ],
        "name": CREATED_EVENT,
        "type": TYPE_EVENT,
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": ENTITY_KEY, "type": TYPE_UINT},
            {"indexed": True, "name": OWNER_ADDRESS, "type": TYPE_ADDRESS},
            {"indexed": False, "name": OLD_EXPIRATION_BLOCK, "type": TYPE_UINT},
            {"indexed": False, "name": NEW_EXPIRATION_BLOCK, "type": TYPE_UINT},
            {"indexed": False, "name": COST, "type": TYPE_UINT},
        ],
        "name": UPDATED_EVENT,
        "type": TYPE_EVENT,
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": ENTITY_KEY, "type": TYPE_UINT},
            {"indexed": True, "name": OWNER_ADDRESS, "type": TYPE_ADDRESS},
        ],
        "name": EXPIRED_EVENT,
        "type": TYPE_EVENT,
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": ENTITY_KEY, "type": TYPE_UINT},
            {"indexed": True, "name": OWNER_ADDRESS, "type": TYPE_ADDRESS},
        ],
        "name": DELETED_EVENT,
        "type": TYPE_EVENT,
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": ENTITY_KEY, "type": TYPE_UINT},
            {"indexed": True, "name": OWNER_ADDRESS, "type": TYPE_ADDRESS},
            {"indexed": False, "name": OLD_EXPIRATION_BLOCK, "type": TYPE_UINT},
            {"indexed": False, "name": NEW_EXPIRATION_BLOCK, "type": TYPE_UINT},
            {"indexed": False, "name": COST, "type": TYPE_UINT},
        ],
        "name": EXTENDED_EVENT,
        "type": TYPE_EVENT,
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": ENTITY_KEY, "type": TYPE_UINT},
            {"indexed": True, "name": OLD_OWNER_ADDRESS, "type": TYPE_ADDRESS},
            {"indexed": True, "name": NEW_OWNER_ADDRESS, "type": TYPE_ADDRESS},
        ],
        "name": OWNER_CHANGED_EVENT,
        "type": TYPE_EVENT,
    },
]


FUNCTIONS_ABI: dict[str, Method[Any]] = {
    "get_storage_value": Method(
        json_rpc_method=RPCEndpoint("golembase_getStorageValue"),
        mungers=[default_root_munger],
    ),
    "get_entity_metadata": Method(
        json_rpc_method=RPCEndpoint("golembase_getEntityMetaData"),
        mungers=[default_root_munger],
    ),
    "get_entities_to_expire_at_block": Method(
        json_rpc_method=RPCEndpoint("golembase_getEntitiesToExpireAtBlock"),
        mungers=[default_root_munger],
    ),
    "get_entity_count": Method(
        json_rpc_method=RPCEndpoint("golembase_getEntityCount"),
        mungers=[default_root_munger],
    ),
    "get_all_entity_keys": Method(
        json_rpc_method=RPCEndpoint("golembase_getAllEntityKeys"),
        mungers=[default_root_munger],
    ),
    "get_entities_of_owner": Method(
        json_rpc_method=RPCEndpoint("golembase_getEntitiesOfOwner"),
        mungers=[default_root_munger],
    ),
    "query_entities": Method(
        # TODO figure out why endpoint has the prefix "golembase_"
        json_rpc_method=RPCEndpoint("golembase_queryEntities"),
        mungers=[default_root_munger],
    ),
    "query": Method(
        json_rpc_method=RPCEndpoint("arkiv_query"),
        mungers=[default_root_munger],
    ),
}
