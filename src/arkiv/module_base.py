"""Base class for Arkiv module with shared functionality."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Generic, TypeVar

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
