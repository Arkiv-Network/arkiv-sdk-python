"""Basic entity management module for Arkiv client."""

import base64
import logging
from typing import TYPE_CHECKING, Any

from eth_typing import ChecksumAddress, HexStr
from web3 import Web3
from web3.types import TxParams, TxReceipt

from .contract import EVENTS_ABI, FUNCTIONS_ABI, STORAGE_ADDRESS
from .types import (
    ALL,
    ANNOTATIONS,
    METADATA,
    PAYLOAD,
    Annotations,
    CreateOp,
    Entity,
    EntityKey,
    Operations,
    TransactionReceipt,
    TxHash,
)
from .utils import merge_annotations, to_receipt, to_tx_params

# Deal with potential circular imports between client.py and module.py
if TYPE_CHECKING:
    from .client import Arkiv

logger = logging.getLogger(__name__)

TX_SUCCESS = 1


class ArkivModule:
    """Basic Arkiv module for entity management operations."""

    def __init__(self, client: "Arkiv") -> None:
        """Initialize Arkiv module with client reference."""
        self.client = client

        # Attach custom Arkiv RPC methods to the eth object
        self.client.eth.attach_methods(FUNCTIONS_ABI)
        for method_name in FUNCTIONS_ABI.keys():
            logger.debug(f"Custom RPC method: eth.{method_name}")

        # Create contract instance for events (using EVENTS_ABI)
        self.contract = client.eth.contract(address=STORAGE_ADDRESS, abi=EVENTS_ABI)
        for event in self.contract.all_events():
            logger.debug(f"Entity event {event.topic}: {event.signature}")

    def is_available(self) -> bool:
        """Check if Arkiv functionality is available."""
        return True

    def execute(
        self, operations: Operations, tx_params: TxParams | None = None
    ) -> TransactionReceipt:
        """
        Execute operations on the Arkiv storage contract.

        Args:
            operations: Operations to execute (creates, updates, deletes, extensions)
            tx_params: Optional additional transaction parameters

        Returns:
            TransactionReceipt with details of all operations executed
        """
        # Convert to transaction parameters and send
        client: Arkiv = self.client
        tx_params = to_tx_params(operations, tx_params)
        tx_hash_bytes = client.eth.send_transaction(tx_params)
        tx_hash = TxHash(HexStr(tx_hash_bytes.to_0x_hex()))

        tx_receipt: TxReceipt = client.eth.wait_for_transaction_receipt(tx_hash)
        tx_status: int = tx_receipt["status"]
        if tx_status != TX_SUCCESS:
            raise RuntimeError(f"Transaction failed with status {tx_status}")

        # Parse and return receipt
        receipt: TransactionReceipt = to_receipt(
            client.arkiv.contract, tx_hash, tx_receipt
        )
        logger.debug(f"Arkiv receipt: {receipt}")
        return receipt

    def create_entity(
        self,
        payload: bytes | None = None,
        annotations: Annotations | None = None,
        btl: int = 0,
        tx_params: TxParams | None = None,
    ) -> tuple[EntityKey, TxHash]:
        """
        Create a new entity on the Arkiv storage contract.

        Args:
            payload: Optional data payload for the entity
            annotations: Optional key-value annotations
            btl: Blocks to live (default: 0)
            tx_params: Optional additional transaction parameters

        Returns:
            The entity key and transaction hash of the create operation
        """
        # Check and set defaults
        if not payload:
            payload = b""
        if not annotations:
            annotations = Annotations({})

        # Create the operation
        create_op = CreateOp(payload=payload, annotations=annotations, btl=btl)

        # Wrap in Operations container and execute
        operations = Operations(creates=[create_op])
        receipt = self.execute(operations, tx_params)

        # Verify we got at least one create
        creates = receipt.creates
        if len(creates) == 0:
            raise RuntimeError("Receipt should have at least one entry in 'creates'")

        create = creates[0]
        entity_key = create.entity_key
        return entity_key, receipt.tx_hash

    def create_entities(
        self,
        create_ops: list[CreateOp],
        tx_params: TxParams | None = None,
    ) -> tuple[list[EntityKey], TxHash]:
        """
        Create multiple entities in a single transaction (bulk create).

        Args:
            create_ops: List of CreateOp objects to create
            tx_params: Optional additional transaction parameters

        Returns:
            An array of all created entity keys and transaction hash of the operation
        """
        if not create_ops or len(create_ops) == 0:
            raise ValueError("create_ops must contain at least one CreateOp")

        # Wrap in Operations container and execute
        operations = Operations(creates=create_ops)
        receipt = self.execute(operations, tx_params)

        # Verify all creates succeeded
        if len(receipt.creates) != len(create_ops):
            raise RuntimeError(
                f"Expected {len(create_ops)} creates in receipt, got {len(receipt.creates)}"
            )

        entity_keys = [create.entity_key for create in receipt.creates]
        return entity_keys, receipt.tx_hash

    def entity_exists(self, entity_key: EntityKey) -> bool:
        """
        Check if an entity exists storage.

        Args:
            entity_key: The entity key to check

        Returns:
            True if the entity exists, False otherwise
        """
        try:
            self.client.eth.get_entity_metadata(entity_key)  # type: ignore[attr-defined]
            return True

        except Exception:
            return False

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
        owner: ChecksumAddress | None = None
        expires_at_block: int | None = None
        payload: bytes | None = None
        annotations: Annotations | None = None

        # HINT: rpc methods to fetch entity content might change this is the place to adapt
        # get and decode payload if requested
        try:
            if fields & PAYLOAD:
                payload = self._get_storage_value(entity_key)

            # get and decode annotations and/or metadata if requested
            if fields & METADATA or fields & ANNOTATIONS:
                metadata_all = self._get_entity_metadata(entity_key)

                if fields & METADATA:
                    # Convert owner address to checksummed format
                    owner = self._get_owner(metadata_all)
                    expires_at_block = self._get_expires_at_block(metadata_all)

                if fields & ANNOTATIONS:
                    annotations = merge_annotations(
                        string_annotations=metadata_all.get("stringAnnotations", []),
                        numeric_annotations=metadata_all.get("numericAnnotations", []),
                    )
        except Exception as e:
            logger.warning(f"Error fetching entity[{entity_key}]: {e}")

        # Create and return entity
        return Entity(
            entity_key=entity_key,
            fields=fields,
            owner=owner,
            expires_at_block=expires_at_block,
            payload=payload,
            annotations=annotations,
        )

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

    def _get_storage_value(self, entity_key: EntityKey) -> bytes:
        """Get the storage value stored in the given entity."""
        # EntityKey is automatically converted by arkiv_munger
        storage_value = base64.b64decode(self.client.eth.get_storage_value(entity_key))  # type: ignore[attr-defined]
        logger.debug(f"Storage value (decoded): {storage_value!r}")
        return storage_value

    def _get_entity_metadata(self, entity_key: EntityKey) -> dict[str, Any]:
        """Get the metadata of the given entity."""
        # EntityKey is automatically converted by arkiv_munger
        metadata: dict[str, Any] = self.client.eth.get_entity_metadata(entity_key)  # type: ignore[attr-defined]
        logger.debug(f"Raw metadata: {metadata}")
        return metadata
