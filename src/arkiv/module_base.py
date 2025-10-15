"""Base class for Arkiv module with shared functionality."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Generic, TypeVar

from .contract import EVENTS_ABI, FUNCTIONS_ABI, STORAGE_ADDRESS

if TYPE_CHECKING:
    from .events import EventFilter

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
