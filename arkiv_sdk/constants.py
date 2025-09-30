"""Constants used in the Arkiv SDK."""

from collections.abc import Sequence
from typing import Any, Final

from .types import (
    Address,
    GenericBytes,
)

STORAGE_ADDRESS: Final[Address] = Address(
    GenericBytes.from_hex_string("0x0000000000000000000000000000000060138453")
)

ARKIV_ABI: Final[Sequence[dict[str, Any]]] = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "entityKey", "type": "uint256"},
            {"indexed": False, "name": "expirationBlock", "type": "uint256"},
        ],
        "name": "GolemBaseStorageEntityCreated",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "entityKey", "type": "uint256"},
            {"indexed": False, "name": "expirationBlock", "type": "uint256"},
        ],
        "name": "GolemBaseStorageEntityUpdated",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [{"indexed": True, "name": "entityKey", "type": "uint256"}],
        "name": "GolemBaseStorageEntityDeleted",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "entityKey", "type": "uint256"},
            {"indexed": False, "name": "oldExpirationBlock", "type": "uint256"},
            {"indexed": False, "name": "newExpirationBlock", "type": "uint256"},
        ],
        "name": "GolemBaseStorageEntityBTLExtended",
        "type": "event",
    },
]
