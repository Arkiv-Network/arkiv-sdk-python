"""Constants used in the Arkiv SDK."""

from collections.abc import Sequence
from typing import Any, Final

from eth_typing import ChecksumAddress
from web3 import Web3
from web3.method import Method, default_root_munger
from web3.types import RPCEndpoint

ARKIV_ADDRESS: Final[ChecksumAddress] = Web3.to_checksum_address(
    "0x4400000000000000000000000000000000000044"
)

ENTITY_OPERATION_EVENT: Final[str] = "EntityOperation"
CHANGESET_HASH_UPDATE_EVENT: Final[str] = "ChangeSetHashUpdate"

ENTITY_KEY = "entityKey"
OPERATION_TYPE = "operationType"
OWNER = "owner"
EXPIRES_AT = "expiresAt"
ENTITY_HASH = "entityHash"

OP_TYPE_CREATE   = 1
OP_TYPE_UPDATE   = 2
OP_TYPE_EXTEND   = 3
OP_TYPE_TRANSFER = 4
OP_TYPE_DELETE   = 5
OP_TYPE_EXPIRE   = 6

ATTR_UINT       = 1
ATTR_STRING     = 2
ATTR_ENTITY_KEY = 3

# Maps EventType literal strings to operation type constants
EVENTS: dict[str, int] = {
    "created":      OP_TYPE_CREATE,
    "updated":      OP_TYPE_UPDATE,
    "extended":     OP_TYPE_EXTEND,
    "deleted":      OP_TYPE_DELETE,
    "owner_changed": OP_TYPE_TRANSFER,
    "expired":      OP_TYPE_EXPIRE,
}

TYPE_EVENT = "event"
TYPE_UINT8 = "uint8"
TYPE_UINT32 = "uint32"
TYPE_UINT256 = "uint256"
TYPE_BYTES32 = "bytes32"
TYPE_ADDRESS = "address"

EVENTS_ABI: Final[Sequence[dict[str, Any]]] = [
    {
        "anonymous": False,
        "type": TYPE_EVENT,
        "name": ENTITY_OPERATION_EVENT,
        "inputs": [
            {"indexed": True,  "name": ENTITY_KEY,     "type": TYPE_BYTES32},
            {"indexed": True,  "name": OPERATION_TYPE, "type": TYPE_UINT8},
            {"indexed": True,  "name": OWNER,          "type": TYPE_ADDRESS},
            {"indexed": False, "name": EXPIRES_AT,     "type": TYPE_UINT32},
            {"indexed": False, "name": ENTITY_HASH,    "type": TYPE_BYTES32},
        ],
    },
    {
        "anonymous": False,
        "type": TYPE_EVENT,
        "name": CHANGESET_HASH_UPDATE_EVENT,
        "inputs": [
            {"indexed": True,  "name": ENTITY_KEY,      "type": TYPE_BYTES32},
            {"indexed": True,  "name": "operationKey",  "type": TYPE_UINT256},
            {"indexed": False, "name": "changeSetHash", "type": TYPE_BYTES32},
        ],
    },
]

EXECUTE_FUNCTION_ABI: Final[dict[str, Any]] = {
    "type": "function",
    "name": "execute",
    "stateMutability": "nonpayable",
    "inputs": [
        {
            "name": "ops",
            "type": "tuple[]",
            "components": [
                {"name": "operationType", "type": TYPE_UINT8},
                {"name": "entityKey",     "type": TYPE_BYTES32},
                {"name": "payload",       "type": "bytes"},
                {
                    "name": "contentType",
                    "type": "tuple",
                    "components": [{"name": "data", "type": "bytes32[4]"}],
                },
                {
                    "name": "attributes",
                    "type": "tuple[]",
                    "components": [
                        {"name": "name",      "type": TYPE_BYTES32},
                        {"name": "valueType", "type": TYPE_UINT8},
                        {"name": "value",     "type": "bytes32[4]"},
                    ],
                },
                {"name": "expiresAt", "type": TYPE_UINT32},
                {"name": "newOwner",  "type": TYPE_ADDRESS},
            ],
        }
    ],
    "outputs": [],
}

FULL_ABI: Final[Sequence[dict[str, Any]]] = [*EVENTS_ABI, EXECUTE_FUNCTION_ABI]


FUNCTIONS_ABI: dict[str, Method[Any]] = {
    "get_entity_count": Method(
        json_rpc_method=RPCEndpoint("arkiv_getEntityCount"),
        mungers=[default_root_munger],
    ),
    "query": Method(
        json_rpc_method=RPCEndpoint("arkiv_query"),
        mungers=[default_root_munger],
    ),
    "get_block_timing": Method(
        json_rpc_method=RPCEndpoint("arkiv_getBlockTiming"),
        mungers=[default_root_munger],
    ),
    "estimate_costs": Method(
        json_rpc_method=RPCEndpoint("arkiv_estimateStorageCosts"),
        mungers=[default_root_munger],
    ),
}
