"""Async entity management module for Arkiv client."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any

from eth_typing import ChecksumAddress, HexStr
from web3.types import TxParams, TxReceipt

from .module_base import ArkivModuleBase
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
    UpdateOp,
)
from .utils import merge_annotations, to_tx_params

# Deal with potential circular imports between client.py and module_async.py
if TYPE_CHECKING:
    from .client import AsyncArkiv  # noqa: F401 - used in Generic type parameter

logger = logging.getLogger(__name__)


class AsyncArkivModule(ArkivModuleBase["AsyncArkiv"]):
    """Async Arkiv module for entity management operations."""

    async def execute(
        self, operations: Operations, tx_params: TxParams | None = None
    ) -> TransactionReceipt:
        """
        Execute operations on the Arkiv storage contract (async).

        Args:
            operations: Operations to execute (creates, updates, deletes, extensions)
            tx_params: Optional additional transaction parameters

        Returns:
            TransactionReceipt with details of all operations executed
        """
        # Convert to transaction parameters and send
        tx_params = to_tx_params(operations, tx_params)

        # Send transaction and get tx hash
        tx_hash_bytes = await self.client.eth.send_transaction(tx_params)
        tx_hash = TxHash(HexStr(tx_hash_bytes.to_0x_hex()))

        # Wait for transaction to complete and return receipt
        tx_receipt: TxReceipt = await self.client.eth.wait_for_transaction_receipt(
            tx_hash
        )
        return self._check_tx_and_get_receipt(tx_hash, tx_receipt)

    async def create_entity(
        self,
        payload: bytes | None = None,
        annotations: Annotations | None = None,
        btl: int | None = None,
        tx_params: TxParams | None = None,
    ) -> tuple[EntityKey, TxHash]:
        """
        Create a new entity on the Arkiv storage contract (async).

        Args:
            payload: Optional data payload for the entity
            annotations: Optional key-value annotations
            btl: Blocks to live (default: self.btl_default, ~30 minutes with 2s blocks)
            tx_params: Optional additional transaction parameters

        Returns:
            The entity key and transaction hash of the create operation
        """
        # Create the operation
        payload, annotations, btl = self._check_and_set_argument_defaults(
            payload, annotations, btl
        )
        create_op = CreateOp(payload=payload, annotations=annotations, btl=btl)

        # Wrap in Operations container and execute
        operations = Operations(creates=[create_op])
        receipt = await self.execute(operations, tx_params)

        # Verify we got at least one create
        creates = receipt.creates
        if len(creates) != 1:
            raise RuntimeError(
                f"Receipt should have exactly one entry in 'creates' but got {len(creates)}"
            )

        create = creates[0]
        entity_key = create.entity_key
        return entity_key, receipt.tx_hash

    async def update_entity(
        self,
        entity_key: EntityKey,
        payload: bytes | None = None,
        annotations: Annotations | None = None,
        btl: int | None = None,
        tx_params: TxParams | None = None,
    ) -> TxHash:
        """
        Update an existing entity on the Arkiv storage contract (async).

        Args:
            entity_key: The entity key of the entity to update
            payload: Optional new data payload for the entity, existing payload will be replaced
            annotations: Optional new key-value annotations, existing annotations will be replaced
            btl: Blocks to live (default: self.btl_default, ~30 minutes with 2s blocks)
            tx_params: Optional additional transaction parameters

        Returns:
            Transaction hash of the update operation
        """
        # Create the update operation
        payload, annotations, btl = self._check_and_set_argument_defaults(
            payload, annotations, btl
        )
        update_op = UpdateOp(
            entity_key=entity_key,
            payload=payload,
            annotations=annotations,
            btl=btl,
        )

        # Wrap in Operations container and execute
        operations = Operations(updates=[update_op])
        receipt = await self.execute(operations, tx_params)

        # Verify the update succeeded
        if len(receipt.updates) != 1:
            raise RuntimeError(
                f"Expected 1 update in receipt, got {len(receipt.updates)}"
            )

        return receipt.tx_hash

    async def entity_exists(self, entity_key: EntityKey) -> bool:
        """
        Check if an entity exists storage (async).

        Args:
            entity_key: The entity key to check

        Returns:
            True if the entity exists, False otherwise
        """
        try:
            # TODO self.client.eth.get_entity_metadata by itself does not guarantee existence
            await self._get_entity_metadata(entity_key)
            return True

        except Exception:
            return False

    async def get_entity(self, entity_key: EntityKey, fields: int = ALL) -> Entity:
        """
        Get an entity by its entity key (async).

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
                payload = await self._get_storage_value(entity_key)

            # get and decode annotations and/or metadata if requested
            if fields & METADATA or fields & ANNOTATIONS:
                metadata_all = await self._get_entity_metadata(entity_key)

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

    async def _get_storage_value(self, entity_key: EntityKey) -> bytes:
        """Get the storage value stored in the given entity (async)."""
        # EntityKey is automatically converted by arkiv_munger
        storage_value = base64.b64decode(
            await self.client.eth.get_storage_value(entity_key)
        )
        logger.debug(f"Storage value (decoded): {storage_value!r}")
        return storage_value

    async def _get_entity_metadata(self, entity_key: EntityKey) -> dict[str, Any]:
        """Get the metadata of the given entity (async)."""
        # EntityKey is automatically converted by arkiv_munger
        metadata: dict[str, Any] = await self.client.eth.get_entity_metadata(entity_key)
        return self._check_entity_metadata(entity_key, metadata)
