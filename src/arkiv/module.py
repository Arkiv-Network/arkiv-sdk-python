"""Basic entity management module for Arkiv client."""

import base64
import logging
from typing import TYPE_CHECKING, Any

from hexbytes import HexBytes
from web3 import Web3
from web3.types import TxParams, TxReceipt

from .contract import EVENTS_ABI, FUNCTIONS_ABI, STORAGE_ADDRESS
from .types import (
    AnnotationValue,
    Entity,
    EntityKey,
    Metadata,
    Operations,
    TransactionReceipt,
)
from .utils import merge_annotations, to_create_operation, to_receipt, to_tx_params

# Deal with potential circular imports between client.py and module.py
if TYPE_CHECKING:
    from .client import Arkiv

logger = logging.getLogger(__name__)

PAYLOAD = 1
ANNOTATIONS = 2
METADATA = 4
ALL = PAYLOAD | ANNOTATIONS | METADATA

TX_SUCCESS = 1


class ArkivModule:
    """Basic Arkiv module for entity management operations."""

    def __init__(self, client: "Arkiv") -> None:
        """Initialize Arkiv module with client reference."""
        self.client = client

        # Attach custom Arkiv RPC methods to the eth object
        self.client.eth.attach_methods(FUNCTIONS_ABI)
        for method_name in FUNCTIONS_ABI.keys():
            logger.info(f"Custom RPC method: eth.{method_name}")

        # Create contract instance for events (using EVENTS_ABI)
        self.contract = client.eth.contract(address=STORAGE_ADDRESS, abi=EVENTS_ABI)
        for event in self.contract.all_events():
            logger.info(f"Entity event {event.topic}: {event.signature}")

    def is_available(self) -> bool:
        """Check if Arkiv functionality is available."""
        return True

    def create_entity(
        self,
        payload: bytes | None = None,
        annotations: dict[str, AnnotationValue] | None = None,
        btl: int = 0,
        tx_params: TxParams | None = None,
    ) -> tuple[EntityKey, HexBytes]:
        """
        Create a new entity on the Arkiv storage contract.

        Args:
            payload: Optional data payload for the entity
            annotations: Optional key-value annotations
            btl: Blocks to live (default: 0)
            tx_params: Optional additional transaction parameters

        Returns:
            Transaction hash of the create operation
        """
        # Create the operation
        create_op = to_create_operation(
            payload=payload, annotations=annotations, btl=btl
        )

        # Wrap in Operations container
        operations = Operations(creates=[create_op])

        # Convert to transaction parameters and send
        client: Arkiv = self.client
        tx_params = to_tx_params(operations, tx_params)
        tx_hash = client.eth.send_transaction(tx_params)

        tx_receipt: TxReceipt = client.eth.wait_for_transaction_receipt(tx_hash)
        tx_status: int = tx_receipt["status"]
        if tx_status != TX_SUCCESS:
            raise RuntimeError(f"Transaction failed with status {tx_status}")

        # assert that receipt has a creates field
        receipt: TransactionReceipt = to_receipt(
            client.arkiv.contract, tx_hash, tx_receipt
        )
        creates = receipt.creates
        if len(creates) == 0:
            raise RuntimeError("Receipt should have at least one entry in 'creates'")

        create = creates[0]
        entity_key = create.entity_key
        return entity_key, tx_hash

    def get_entity(self, entity_key: EntityKey, fields: int = ALL) -> Entity:
        """
        Get an entity by its entity key.

        Args:
            entity_key: The entity key to retrieve
            fields: Bitfield indicating which fields to retrieve
                   PAYLOAD (1) = retrieve payload
                   METADATA (2) = retrieve metadata
                   ANNOTATIONS (4) = retrieve annotations

        Returns:
            Entity object with the requested fields
        """
        # Gather the requested data
        payload = None
        metadata = None
        annotations = None

        # HINT: rpc methods to fetch entity content might change this is the place to adapt
        # get and decode payload if requested
        if fields & PAYLOAD:
            payload = self._get_storage_value(entity_key)

        # get and decode annotations and/or metadata if requested
        if fields & METADATA or fields & ANNOTATIONS:
            metadata_all = self._get_entity_metadata(entity_key)

            if fields & METADATA:
                # Convert owner address to checksummed format
                owner_address = metadata_all.get("owner")
                if not owner_address:
                    raise ValueError("Entity metadata missing required owner field")
                checksummed_owner = Web3.to_checksum_address(owner_address)

                expires_at_block = metadata_all.get("expiresAtBlock")
                if expires_at_block is None:
                    raise ValueError(
                        "Entity metadata missing required expiresAtBlock field"
                    )

                metadata = Metadata(
                    owner=checksummed_owner,
                    expires_at_block=int(expires_at_block),
                )

            if fields & ANNOTATIONS:
                annotations = merge_annotations(
                    string_annotations=metadata_all.get("stringAnnotations", []),
                    numeric_annotations=metadata_all.get("numericAnnotations", []),
                )

        # Create and return entity
        return Entity(
            entity_key=entity_key,
            payload=payload,
            metadata=metadata,
            annotations=annotations,
        )

    def _get_storage_value(self, entity_key: EntityKey) -> bytes:
        """Get the storage value stored in the given entity."""
        # EntityKey is automatically converted by arkiv_munger
        storage_value = base64.b64decode(self.client.eth.get_storage_value(entity_key))  # type: ignore[attr-defined]
        logger.info(f"Storage value (decoded): {storage_value!r}")
        return storage_value

    def _get_entity_metadata(self, entity_key: EntityKey) -> dict[str, Any]:
        """Get the metadata of the given entity."""
        # EntityKey is automatically converted by arkiv_munger
        metadata: dict[str, Any] = self.client.eth.get_entity_metadata(entity_key)  # type: ignore[attr-defined]
        logger.info(f"Raw metadata: {metadata}")
        return metadata
