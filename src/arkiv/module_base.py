"""Base class for Arkiv module with shared functionality."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from eth_typing import ChecksumAddress
from web3 import Web3
from web3.types import TxReceipt

from arkiv.types import Annotations, TransactionReceipt, TxHash
from arkiv.utils import to_receipt

from .contract import EVENTS_ABI, FUNCTIONS_ABI, STORAGE_ADDRESS

if TYPE_CHECKING:
    from .events import EventFilter

TX_SUCCESS = 1

logger = logging.getLogger(__name__)

# Generic type variable for the client (Arkiv or AsyncArkiv)
ClientT = TypeVar("ClientT")


class ArkivModuleBase(Generic[ClientT]):  # noqa: UP046 - Generic syntax for Python 3.10+ compat
    """Base class for Arkiv modules with shared functionality.

    This class contains the common initialization and utility methods
    shared between sync (ArkivModule) and async (AsyncArkivModule) implementations.
    """

    BTL_DEFAULT = (
        1000  # Default blocks to live for created entities (~30 mins with 2s blocks)
    )

    def __init__(self, client: ClientT, btl_default: int = BTL_DEFAULT) -> None:
        """Initialize Arkiv module with client reference.

        Args:
            client: Arkiv or AsyncArkiv client instance
        """
        self.client = client
        self.btl_default = btl_default

        # Attach custom Arkiv RPC methods to the eth object
        # Type checking: client has 'eth' attribute from Web3/AsyncWeb3
        client.eth.attach_methods(FUNCTIONS_ABI)  # type: ignore[attr-defined]
        for method_name in FUNCTIONS_ABI.keys():
            logger.debug(f"Custom RPC method: eth.{method_name}")

        # Create contract instance for events (using EVENTS_ABI)
        self.contract = client.eth.contract(address=STORAGE_ADDRESS, abi=EVENTS_ABI)  # type: ignore[attr-defined]
        for event in self.contract.all_events():
            logger.debug(f"Entity event {event.topic}: {event.signature}")

        # Track active event filters for cleanup
        self._active_filters: list[EventFilter] = []

    def is_available(self) -> bool:
        """Check if Arkiv functionality is available. Should always be true for Arkiv clients."""
        return True

    def _check_and_set_argument_defaults(
        self,
        payload: bytes | None,
        annotations: Annotations | None,
        btl: int | None,
    ) -> tuple[bytes, Annotations, int]:
        """Check and set defaults for entity management arguments."""
        if btl is None:
            btl = self.btl_default
        if not payload:
            payload = b""
        if not annotations:
            annotations = Annotations({})

        return payload, annotations, btl

    def _check_tx_and_get_receipt(
        self, tx_hash: TxHash, tx_receipt: TxReceipt
    ) -> TransactionReceipt:
        """Check transaction status and return Arkiv transaction receipt."""
        tx_status: int = tx_receipt["status"]
        if tx_status != TX_SUCCESS:
            raise RuntimeError(f"Transaction failed with status {tx_status}")

        # Parse and return receipt
        receipt: TransactionReceipt = to_receipt(self.contract, tx_hash, tx_receipt)

        logger.debug(f"Arkiv receipt: {receipt}")
        return receipt

    def _check_entity_metadata(
        self, entity_key: str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Check and validate entity metadata structure."""
        logger.debug(f"Raw metadata: {metadata}")

        # Basic validation of metadata content
        if not metadata:
            raise ValueError(f"Entity metadata is empty for entity key {entity_key}")

        if "owner" not in metadata or "expiresAtBlock" not in metadata:
            raise ValueError(
                f"Entity metadata missing required fields for entity key {entity_key}: {metadata}"
            )

        return metadata

    def _get_owner(self, metadata: dict[str, Any]) -> ChecksumAddress:
        """Get the owner address of the given entity."""
        owner_metadata = metadata.get("owner")
        if not owner_metadata:
            raise ValueError("Entity metadata missing required 'owner' field")
        return Web3.to_checksum_address(owner_metadata)

    def _get_expires_at_block(self, metadata: dict[str, Any]) -> int:
        """Get the expiration block of the given entity."""
        expires_at_block_metadata = metadata.get("expiresAtBlock")
        if expires_at_block_metadata is None:
            raise ValueError("Entity metadata missing required 'expiresAtBlock' field")
        return int(expires_at_block_metadata)
