"""Basic entity management module for Arkiv client."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any

from eth_typing import ChecksumAddress, HexStr
from web3 import Web3
from web3.types import TxParams, TxReceipt

from arkiv.account import NamedAccount

from .events import EventFilter
from .module_base import ArkivModuleBase
from .query import QueryIterator
from .types import (
    ALL,
    NONE,
    QUERY_OPTIONS_DEFAULT,
    Annotations,
    CreateCallback,
    CreateOp,
    DeleteOp,
    Entity,
    EntityKey,
    EventType,
    ExtendCallback,
    ExtendOp,
    Operations,
    QueryOptions,
    QueryResult,
    TransactionReceipt,
    TxHash,
    UpdateCallback,
    UpdateOp,
)
from .utils import to_query_result, to_rpc_query_options, to_tx_params

# Deal with potential circular imports between client.py and module.py
if TYPE_CHECKING:
    from .client import Arkiv  # noqa: F401 - used in Generic type parameter

logger = logging.getLogger(__name__)

TX_SUCCESS = 1


class ArkivModule(ArkivModuleBase["Arkiv"]):
    """Basic Arkiv module for entity management operations."""

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
        tx_params = to_tx_params(operations, tx_params)

        # Send transaction and get tx hash
        tx_hash_bytes = self.client.eth.send_transaction(tx_params)
        tx_hash = TxHash(HexStr(tx_hash_bytes.to_0x_hex()))

        # Wait for transaction to complete and return receipt
        tx_receipt: TxReceipt = self.client.eth.wait_for_transaction_receipt(tx_hash)
        return self._check_tx_and_get_receipt(tx_hash, tx_receipt)

    def create_entity(
        self,
        payload: bytes | None = None,
        content_type: str | None = None,
        annotations: Annotations | None = None,
        btl: int | None = None,
        tx_params: TxParams | None = None,
    ) -> tuple[EntityKey, TxHash]:
        """
        Create a new entity on the Arkiv storage contract.

        Args:
            payload: Optional data payload for the entity
            content_type: Optional content type for the entity
            annotations: Optional key-value annotations
            btl: Blocks to live (default: self.btl_default, ~30 minutes with 2s blocks)
            tx_params: Optional additional transaction parameters

        Returns:
            The entity key and transaction hash of the create operation
        """
        # Create the operation
        payload, content_type, annotations, btl = self._check_and_set_argument_defaults(
            payload, content_type, annotations, btl
        )
        create_op = CreateOp(
            payload=payload, content_type=content_type, annotations=annotations, btl=btl
        )
        logger.info(f"Creating entity:{create_op}")

        # Wrap in Operations container and execute
        operations = Operations(creates=[create_op])
        receipt = self.execute(operations, tx_params)

        # Verify we got at least one create
        creates = receipt.creates
        if len(creates) != 1:
            raise RuntimeError(
                f"Receipt should have exactly one entry in 'creates' but got {len(creates)}"
            )

        create = creates[0]
        entity_key = create.entity_key
        return entity_key, receipt.tx_hash

    def update_entity(
        self,
        entity_key: EntityKey,
        payload: bytes | None = None,
        content_type: str | None = None,
        annotations: Annotations | None = None,
        btl: int | None = None,
        tx_params: TxParams | None = None,
    ) -> TxHash:
        """
        Update an existing entity on the Arkiv storage contract.

        Args:
            entity_key: The entity key of the entity to update
            payload: Optional new data payload for the entity, existing payload will be replaced
            content_type: Optional new content type for the entity, existing content type will be replaced
            annotations: Optional new key-value annotations, existing annotations will be replaced
            btl: Blocks to live (default: self.btl_default, ~30 minutes with 2s blocks)
            tx_params: Optional additional transaction parameters

        Returns:
            Transaction hash of the update operation
        """
        # Create the update operation
        payload, content_type, annotations, btl = self._check_and_set_argument_defaults(
            payload, content_type, annotations, btl
        )
        update_op = UpdateOp(
            entity_key=entity_key,
            payload=payload,
            content_type=content_type,
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

    def entity_exists(self, entity_key: EntityKey, at_block: int | None = None) -> bool:
        """
        Check if an entity exists storage.

        Args:
            entity_key: The entity key to check
            at_block: Block number to pin query to specific block, or None to use latest block available

        Returns:
            True if the entity exists, False otherwise
        """
        try:
            options = QueryOptions(fields=NONE, at_block=at_block)
            query_result: QueryResult = self.query_entities(
                f"$key = {entity_key}", options=options
            )
            return len(query_result.entities) > 0
        except Exception:
            return False

    def get_entity(
        self, entity_key: EntityKey, fields: int = ALL, at_block: int | None = None
    ) -> Entity:
        """
        Get an entity by its entity key.

        Args:
            entity_key: The entity key to retrieve
            fields: Bitfield indicating which fields to retrieve. See file types.py
            at_block: Block number to pin query to specific block, or None to use latest block available

        Returns:
            Entity object with the requested fields
        """

        options = QueryOptions(fields=fields, at_block=at_block)
        query_result: QueryResult = self.query_entities(
            f"$key = {entity_key}", options=options
        )

        if not query_result:
            raise ValueError(f"Entity not found: {entity_key}")

        if len(query_result.entities) != 1:
            raise ValueError(f"Expected 1 entity, got {len(query_result.entities)}")

        result_entity = query_result.entities[0]
        return result_entity

    def query_entities(
        self,
        query: str | None = None,
        options: QueryOptions = QUERY_OPTIONS_DEFAULT,
    ) -> QueryResult:
        """
        Execute a query against entity storage.

        Args:
            query: SQL-like query string
            options: QueryOptions for the query execution

        Raises:
            ValueError: if invalid query options are provided.

        Returns:
            QueryResult with entities, block number, and an optional cursor to fetch the next page
        """

        options.validate(query)
        rpc_options = to_rpc_query_options(options)
        raw_results = self.client.eth.query(query, rpc_options)

        return to_query_result(options.fields, raw_results)

    def query_all_entities(
        self,
        query: str,
        *,
        limit: int = 100,
        at_block: int | str = "latest",
    ) -> QueryIterator:
        """
        Query entities with automatic pagination.

        Returns an iterator that automatically fetches all pages of results,
        allowing you to seamlessly process all matching entities without
        manual pagination.

        Args:
            query: SQL-like query string to filter and order entities.
                Example: "SELECT * FROM entities WHERE owner = '0x...' ORDER BY created_at DESC"
            limit: Number of entities to fetch per page (default: 100).
                Server may enforce a maximum limit.
            at_block: Block number or "latest" at which to execute query.
                Ensures all pages are fetched from the same blockchain state.

        Returns:
            QueryIterator that yields Entity objects across all pages.

        Examples:
            Process all matching entities:
                >>> for entity in arkiv.arkiv.query_all_entities(
                ...     "SELECT * WHERE owner = '0x1234...'",
                ...     limit=100
                ... ):
                ...     process(entity)

            Collect all results:
                >>> entities = list(arkiv.arkiv.query_all_entities(
                ...     "SELECT * ORDER BY created_at DESC",
                ...     limit=50
                ... ))
                >>> print(f"Total: {len(entities)}")

            Check which block was queried:
                >>> iterator = arkiv.arkiv.query_all_entities("SELECT *")
                >>> first_entity = next(iterator)
                >>> print(f"Queried at block: {iterator.block_number}")

        Warning:
            This method may make many network requests to fetch all pages.
            Use appropriate limit values to control API usage.
            For manual pagination control, use query_entities() instead.

        Note:
            - All pages maintain consistency by querying the same block
            - The iterator cannot be reused once exhausted
            - Results reflect state at a specific point in time
        """
        return QueryIterator(
            client=self.client,
            query=query,
            limit=limit,
            at_block=at_block,
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

        Creates an event filter that monitors entity creation events. The callback
        receives (CreateEvent, TxHash) for each created entity.

        See `_watch_entity_event` for detailed documentation on parameters, return
        value, error handling, and usage examples.
        """
        return self._watch_entity_event(
            "created", callback, from_block=from_block, auto_start=auto_start
        )

    def watch_entity_updated(
        self,
        callback: UpdateCallback,
        *,
        from_block: str | int = "latest",
        auto_start: bool = True,
    ) -> EventFilter:
        """
        Watch for entity update events.

        Creates an event filter that monitors entity update events. The callback
        receives (UpdateEvent, TxHash) for each updated entity.

        See `_watch_entity_event` for detailed documentation on parameters, return
        value, error handling, and usage examples.
        """
        return self._watch_entity_event(
            "updated", callback, from_block=from_block, auto_start=auto_start
        )

    def watch_entity_extended(
        self,
        callback: ExtendCallback,
        *,
        from_block: str | int = "latest",
        auto_start: bool = True,
    ) -> EventFilter:
        """
        Watch for entity extension events.

        Creates an event filter that monitors entity lifetime extension events. The
        callback receives (ExtendEvent, TxHash) for each extended entity.

        See `_watch_entity_event` for detailed documentation on parameters, return
        value, error handling, and usage examples.
        """
        return self._watch_entity_event(
            "extended", callback, from_block=from_block, auto_start=auto_start
        )

    def watch_entity_deleted(
        self,
        callback: ExtendCallback,
        *,
        from_block: str | int = "latest",
        auto_start: bool = True,
    ) -> EventFilter:
        """
        Watch for entity deletion events.

        Creates an event filter that monitors entity deletion events. The
        callback receives (DeleteEvent, TxHash) for each deleted entity.

        See `_watch_entity_event` for detailed documentation on parameters, return
        value, error handling, and usage examples.
        """
        return self._watch_entity_event(
            "deleted", callback, from_block=from_block, auto_start=auto_start
        )

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

    @property
    def active_filters(self) -> list[EventFilter]:
        """Get a copy of currently active event filters."""
        return list(self._active_filters)

    def _watch_entity_event(
        self,
        event_type: EventType,
        callback: CreateCallback | UpdateCallback | ExtendCallback,
        *,
        from_block: str | int = "latest",
        auto_start: bool = True,
    ) -> EventFilter:
        """
        Internal method to watch for entity events.

        This method creates an event filter that monitors for entity events on the
        Arkiv storage contract. The callback is invoked each time the specified event
        occurs, receiving details about the event and the transaction hash.

        Args:
            event_type: Type of event to watch for ("created", "updated", "extended", "deleted")
            callback: Function to call when an event is detected.
                     Receives (Event, TxHash) as arguments where Event is one of:
                     CreateEvent, UpdateEvent, ExtendEvent, or DeleteEvent depending on event_type.
            from_block: Starting block for the filter. Can be:
                       - "latest": Only watch for new events (default)
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
                >>> def on_event(event: CreateEvent, tx_hash: TxHash) -> None:
                ...     print(f"Event occurred: {event.entity_key}")
                ...
                >>> filter = arkiv._watch_entity_event("created", on_event)
                >>> # Filter is now running and will call on_event for each event
                >>> # ... later ...
                >>> filter.stop()  # Pause watching
                >>> filter.uninstall()  # Cleanup resources

            Manual start/stop control:
                >>> def on_event(event: UpdateEvent, tx_hash: TxHash) -> None:
                ...     print(f"Event occurred: {event.entity_key}")
                ...
                >>> filter = arkiv._watch_entity_event("updated", on_event, auto_start=False)
                >>> # Do some setup work...
                >>> filter.start()  # Begin watching
                >>> # ... later ...
                >>> filter.stop()  # Stop watching
                >>> filter.uninstall()  # Cleanup

            Historical events from specific block:
                >>> filter = arkiv._watch_entity_event(
                ...     "extended",
                ...     on_event,
                ...     from_block=1000  # Start from block 1000
                ... )

        Note:
            - Only captures the specified event type (not other lifecycle events)
            - With from_block="latest", misses events before filter creation
            - Filter must be uninstalled via filter.uninstall() to free resources
            - All active filters are automatically cleaned up when Arkiv client
              context exits
            - Callback exceptions are caught and logged but don't stop the filter
        """
        event_filter = EventFilter(
            contract=self.contract,
            event_type=event_type,
            callback=callback,
            from_block=from_block,
            auto_start=auto_start,
        )

        # Track the filter for cleanup
        self._active_filters.append(event_filter)
        return event_filter

    def _get_storage_value(self, entity_key: EntityKey) -> bytes:
        """Get the storage value stored in the given entity."""
        # EntityKey is automatically converted by arkiv_munger
        storage_value = base64.b64decode(self.client.eth.get_storage_value(entity_key))
        logger.debug(f"Storage value (decoded): {storage_value!r}")
        return storage_value

    def _get_entity_metadata(self, entity_key: EntityKey) -> dict[str, Any]:
        """Get the metadata of the given entity."""
        # EntityKey is automatically converted by arkiv_munger
        metadata: dict[str, Any] = self.client.eth.get_entity_metadata(entity_key)
        return self._check_entity_metadata(entity_key, metadata)
