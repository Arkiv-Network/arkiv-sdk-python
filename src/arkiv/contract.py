"""Constants used in the Arkiv SDK."""

from collections.abc import Sequence
from typing import Any, Final

from eth_typing import ChecksumAddress
from web3 import Web3
from web3.method import Method, default_root_munger
from web3.types import RPCEndpoint

# Import EntityKey for munger type checking

STORAGE_ADDRESS: Final[ChecksumAddress] = Web3.to_checksum_address(
    "0x0000000000000000000000000000000060138453"
)


CREATED_EVENT: Final[str] = "GolemBaseStorageEntityCreated"
UPDATED_EVENT: Final[str] = "GolemBaseStorageEntityUpdated"
EXTENDED_EVENT: Final[str] = "GolemBaseStorageEntityBTLExtended"
DELETED_EVENT: Final[str] = "GolemBaseStorageEntityDeleted"

EVENTS: dict[str, str] = {
    "created": CREATED_EVENT,
    "updated": UPDATED_EVENT,
    "extended": EXTENDED_EVENT,
    "deleted": DELETED_EVENT,
}

TYPE_EVENT = "event"
TYPE_UINT = "uint256"
EVENTS_ABI: Final[Sequence[dict[str, Any]]] = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "entityKey", "type": TYPE_UINT},
            {"indexed": False, "name": "expirationBlock", "type": TYPE_UINT},
        ],
        "name": CREATED_EVENT,
        "type": TYPE_EVENT,
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "entityKey", "type": TYPE_UINT},
            {"indexed": False, "name": "expirationBlock", "type": TYPE_UINT},
        ],
        "name": UPDATED_EVENT,
        "type": TYPE_EVENT,
    },
    {
        "anonymous": False,
        "inputs": [{"indexed": True, "name": "entityKey", "type": TYPE_UINT}],
        "name": DELETED_EVENT,
        "type": TYPE_EVENT,
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "entityKey", "type": TYPE_UINT},
            {"indexed": False, "name": "oldExpirationBlock", "type": TYPE_UINT},
            {"indexed": False, "name": "newExpirationBlock", "type": TYPE_UINT},
        ],
        "name": EXTENDED_EVENT,
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
        json_rpc_method=RPCEndpoint("golembase_queryEntities"),
        mungers=[default_root_munger],
    ),
}
