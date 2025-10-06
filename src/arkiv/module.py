"""Basic entity management module for Arkiv client."""

import base64
import logging
from typing import TYPE_CHECKING, Any

from eth_typing import ChecksumAddress, HexStr
from web3 import Web3
from web3.types import TxParams, TxReceipt

from arkiv.account import NamedAccount

from .contract import EVENTS_ABI, FUNCTIONS_ABI, STORAGE_ADDRESS
from .events import EventFilter
from .types import (
    ALL,
    ANNOTATIONS,
    METADATA,
    PAYLOAD,
    Annotations,
    CreateCallback,
    CreateOp,
    DeleteOp,
    Entity,
    EntityKey,
    ExtendOp,
    Operations,
    TransactionReceipt,
    TxHash,
    UpdateCallback,
    UpdateOp,
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

        # Track active event filters for cleanup
        self._active_filters: list[EventFilter] = []

    def is_available(self) -> bool:
        """Check if Arkiv functionality is available. Should always be true for Arkiv clients."""
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

    def update_entity(
        self,
        entity_key: EntityKey,
        payload: bytes | None = None,
        annotations: Annotations | None = None,
        btl: int = 0,
        tx_params: TxParams | None = None,
    ) -> TxHash:
        """
        Update an existing entity on the Arkiv storage contract.

        Args:
            entity_key: The entity key of the entity to update
            payload: Optional new data payload for the entity, existing payload will be replaced
            annotations: Optional new key-value annotations, existing annotations will be replaced
            btl: Blocks to live (default: 0)
            tx_params: Optional additional transaction parameters

        Returns:
            Transaction hash of the update operation
        """
        # Check and set defaults
        if payload is None:
            payload = b""
        if annotations is None:
            annotations = Annotations({})

        # Create the update operation
        update_op = UpdateOp(
            entity_key=entity_key,
            payload=payload,
            annotations=annotations,
            btl=btl,
        )

        # Wrap in Operations container and execute
        operations = Operations(updates=[update_op])
        receipt = self.execute(operations, tx_params)

        # Verify the update succeeded
        if len(receipt.updates) != 1:
            raise RuntimeError(
                f"Expected 1 update in receipt, got {len(receipt.updates)}"
            )

        return receipt.tx_hash

    def extend_entity(
        self,
        entity_key: EntityKey,
        number_of_blocks: int,
        tx_params: TxParams | None = None,
    ) -> TxHash:
        """
        Extend the lifetime of an entity by a specified number of blocks.

        Args:
            entity_key: The entity key to extend
            number_of_blocks: Number of blocks to extend the entity's lifetime
            tx_params: Optional additional transaction parameters

        Returns:
            Transaction hash of the extend operation
        """
        # Create the extend operation
        extend_op = ExtendOp(entity_key=entity_key, number_of_blocks=number_of_blocks)

        # Wrap in Operations container and execute
        operations = Operations(extensions=[extend_op])
        receipt = self.execute(operations, tx_params)

        # Verify the extend succeeded
        if len(receipt.extensions) != 1:
            raise RuntimeError(
                f"Expected 1 extension in receipt, got {len(receipt.extensions)}"
            )

        return receipt.tx_hash

    def delete_entity(
        self,
        entity_key: EntityKey,
        tx_params: TxParams | None = None,
    ) -> TxHash:
        """
        Delete an entity from the Arkiv storage contract.

        Args:
            entity_key: The entity key to delete
            tx_params: Optional additional transaction parameters

        Returns:
            Transaction hash of the delete operation
        """
        # Create the delete operation
        delete_op = DeleteOp(entity_key=entity_key)

        # Wrap in Operations container and execute
        operations = Operations(deletes=[delete_op])
        receipt = self.execute(operations, tx_params)

        # Verify the delete succeeded
        if len(receipt.deletes) != 1:
            raise RuntimeError(
                f"Expected 1 delete in receipt, got {len(receipt.deletes)}"
            )

        return receipt.tx_hash

    def transfer_eth(
        self,
        to: NamedAccount | ChecksumAddress,
        amount_wei: int,
        wait_for_confirmation: bool = True,
    ) -> TxHash:
        """
        Transfer ETH to the given address.

        Args:
            to: The recipient address or a named account
            amount_wei: The amount of ETH to transfer in wei

        Returns:
            Transaction hash of the transfer
        """
        to_address: ChecksumAddress = to.address if isinstance(to, NamedAccount) else to
        tx_hash_bytes = self.client.eth.send_transaction(
            {
                "to": to_address,
                "value": Web3.to_wei(amount_wei, "wei"),
                "gas": 21000,  # Standard gas for ETH transfer
            }
        )
        tx_hash = TxHash(HexStr(tx_hash_bytes.to_0x_hex()))
        logger.info(f"TX sent: Transferring {amount_wei} wei to {to}: {tx_hash}")

        if wait_for_confirmation:
            logger.info("Waiting for TX confirmation ...")
            tx_receipt: TxReceipt = self.client.eth.wait_for_transaction_receipt(
                tx_hash
            )
            tx_status: int = tx_receipt["status"]
            if tx_status != TX_SUCCESS:
                raise RuntimeError(f"Transaction failed with status {tx_status}")

            logger.info(f"TX confirmed: {tx_receipt}")

        return tx_hash

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

    def watch_entity_created(
        self,
        callback: CreateCallback,
        *,
        from_block: str | int = "latest",
        auto_start: bool = True,
    ) -> EventFilter:
        """
        Watch for entity creation events.

        Args:
            callback: Function to call when a creation event is detected.
                     Receives (CreateEvent, TxHash) as arguments.
            from_block: Starting block for the filter ('latest' or block number)
            auto_start: If True, starts polling immediately

        Returns:
            EventFilter instance for controlling the watch

        Example:
            def on_create(event: CreateEvent, tx_hash: TxHash) -> None:
                print(f"Entity created: {event.entity_key}")

            filter = arkiv.watch_entity_created(on_create)
            # ... later ...
            filter.stop()
        """
        event_filter = EventFilter(
            contract=self.contract,
            event_type="created",
            callback=callback,
            from_block=from_block,
            auto_start=auto_start,
        )

        # Track the filter for cleanup
        self._active_filters.append(event_filter)
        return event_filter

    def watch_entity_updated(
        self,
        callback: UpdateCallback,
        *,
        from_block: str | int = "latest",
        auto_start: bool = True,
    ) -> EventFilter:
        """
        Watch for entity update events.

        This method creates an event filter that monitors for entity updates on the
        Arkiv storage contract. The callback is invoked each time an entity is updated,
        receiving details about the update event and the transaction hash.

        Args:
            callback: Function to call when an update event is detected.
                     Receives (UpdateEvent, TxHash) as arguments.
            from_block: Starting block for the filter. Can be:
                       - "latest": Only watch for new updates (default)
                       - Block number (int): Watch from a specific historical block
            auto_start: If True, starts polling immediately (default: True).
                       If False, you must manually call filter.start()

        Returns:
            EventFilter instance for controlling the watch. Use this to:
            - Stop polling: filter.stop()
            - Resume polling: filter.start()
            - Check status: filter.is_running
            - Cleanup: filter.uninstall()

        Raises:
            ValueError: If callback is not callable
            RuntimeError: If filter creation fails

        Example:
            Basic usage with automatic start:
                >>> def on_update(event: UpdateEvent, tx_hash: TxHash) -> None:
                ...     print(f"Entity updated: {event.entity_key}")
                ...     print(f"New expiration: {event.expiration_block}")
                ...
                >>> filter = arkiv.watch_entity_updated(on_update)
                >>> # Filter is now running and will call on_update for each update
                >>> # ... later ...
                >>> filter.stop()  # Pause watching
                >>> filter.uninstall()  # Cleanup resources

            Manual start/stop control:
                >>> def on_update(event: UpdateEvent, tx_hash: TxHash) -> None:
                ...     print(f"Updated: {event.entity_key}")
                ...
                >>> filter = arkiv.watch_entity_updated(on_update, auto_start=False)
                >>> # Do some setup work...
                >>> filter.start()  # Begin watching
                >>> # ... later ...
                >>> filter.stop()  # Stop watching
                >>> filter.uninstall()  # Cleanup

            Historical updates from specific block:
                >>> filter = arkiv.watch_entity_updated(
                ...     on_update,
                ...     from_block=1000  # Start from block 1000
                ... )

        Note:
            - Only captures UPDATE events (not creates, deletes, or extends)
            - With from_block="latest", misses updates before filter creation
            - Filter must be uninstalled via filter.uninstall() to free resources
            - All active filters are automatically cleaned up when Arkiv client
              context exits
            - Callback exceptions are caught and logged but don't stop the filter
        """
        event_filter = EventFilter(
            contract=self.contract,
            event_type="updated",
            callback=callback,
            from_block=from_block,
            auto_start=auto_start,
        )

        # Track the filter for cleanup
        self._active_filters.append(event_filter)
        return event_filter

    @property
    def active_filters(self) -> list[EventFilter]:
        """Get a copy of currently active event filters."""
        return list(self._active_filters)

    def cleanup_filters(self) -> None:
        """
        Stop and uninstall all active event filters.

        This is automatically called when the Arkiv client exits its context,
        but can be called manually if needed.
        """
        if not self._active_filters:
            logger.debug("No active filters to cleanup")
            return

        logger.info(
            f"Cleaning up {len(self._active_filters)} active event filter(s)..."
        )

        for event_filter in self._active_filters:
            try:
                event_filter.uninstall()
            except Exception as e:
                logger.warning(f"Error cleaning up filter: {e}")

        self._active_filters.clear()
        logger.info("All event filters cleaned up")

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
