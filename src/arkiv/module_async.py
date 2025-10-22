"""Async entity management module for Arkiv client."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any

from eth_typing import ChecksumAddress, HexStr
from web3.types import TxParams, TxReceipt

from .events_async import AsyncEventFilter
from .module_base import ArkivModuleBase
from .types import (
    ALL,
    ANNOTATIONS,
    METADATA,
    PAYLOAD,
    Annotations,
    AsyncCreateCallback,
    AsyncDeleteCallback,
    AsyncExtendCallback,
    AsyncUpdateCallback,
    CreateOp,
    Cursor,
    DeleteOp,
    Entity,
    EntityKey,
    EventType,
    ExtendOp,
    Operations,
    QueryResult,
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

    async def extend_entity(
        self,
        entity_key: EntityKey,
        number_of_blocks: int,
        tx_params: TxParams | None = None,
    ) -> TxHash:
        """
        Extend the lifetime of an entity by a specified number of blocks (async).

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
        receipt = await self.execute(operations, tx_params)

        # Verify the extend succeeded
        if len(receipt.extensions) != 1:
            raise RuntimeError(
                f"Expected 1 extension in receipt, got {len(receipt.extensions)}"
            )

        return receipt.tx_hash

    async def delete_entity(
        self,
        entity_key: EntityKey,
        tx_params: TxParams | None = None,
    ) -> TxHash:
        """
        Delete an entity from the Arkiv storage contract (async).

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
        receipt = await self.execute(operations, tx_params)

        # Verify the delete succeeded
        if len(receipt.deletes) != 1:
            raise RuntimeError(
                f"Expected 1 delete in receipt, got {len(receipt.deletes)}"
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

    async def query_entities(
        self,
        query: str | None = None,
        *,
        limit: int | None = None,
        at_block: int | str = "latest",
        cursor: Cursor | None = None,
    ) -> QueryResult:
        """
        Query entities with manual pagination control (async).

        Execute a query against entity storage and return a single page of results.
        Use the returned cursor to fetch subsequent pages.

        Args:
            query: SQL-like query string for the first page. Mutually exclusive with cursor.
                Example: "SELECT * WHERE owner = '0x...' ORDER BY created_at DESC"
            limit: Maximum number of entities to return per page.
                Server may enforce a maximum limit. Can be modified between pagination requests.
            at_block: Block number or "latest" at which to execute query.
                Ensures consistency across paginated results. Ignored when using cursor
                (cursor already contains the block number).
            cursor: Cursor from previous QueryResult to fetch next page.
                Mutually exclusive with query. The cursor encodes the query and block number.

        Returns:
            QueryResult with entities, block number, and optional next cursor.

        Raises:
            ValueError: If both query and cursor are provided, or if neither is provided.
            NotImplementedError: This method is not yet implemented.

        Examples:
            First page:
                >>> result = await arkiv.arkiv.query_entities(
                ...     "SELECT * WHERE owner = '0x1234...'",
                ...     limit=100
                ... )
                >>> for entity in result:
                ...     print(entity.entity_key)

            Next page:
                >>> if result.has_more():
                ...     next_page = await arkiv.arkiv.query_entities(cursor=result.next_cursor)

        Note:
            For automatic pagination across all pages, use query_all_entities() instead.
        """
        # Validate parameters using base class helper
        self._validate_query_entities_params(query, limit, at_block, cursor)

        if query:
            # Fetch raw results from RPC
            raw_results = await self.client.eth.query_entities(query)
            block_number = await self.client.eth.get_block_number()

            # Transform raw results into QueryResult using base class helper
            return self._build_query_result(raw_results, block_number)

        # Cursor based pagination not implemented yet
        raise NotImplementedError("query_entities is not yet implemented for cursors")

    async def watch_entity_created(
        self,
        callback: AsyncCreateCallback,
        *,
        from_block: str | int = "latest",
        auto_start: bool = True,
    ) -> AsyncEventFilter:
        """
        Watch for entity creation events (async).

        Creates an async event filter that monitors entity creation events. The callback
        receives (CreateEvent, TxHash) for each created entity.

        See `_watch_entity_event` for detailed documentation on parameters, return
        value, error handling, and usage examples.

        Note:
            If auto_start=True, you should await the filter's start() method
            to ensure it has started before continuing.
        """
        return await self._watch_entity_event(
            "created", callback, from_block=from_block, auto_start=auto_start
        )

    async def watch_entity_updated(
        self,
        callback: AsyncUpdateCallback,
        *,
        from_block: str | int = "latest",
        auto_start: bool = True,
    ) -> AsyncEventFilter:
        """
        Watch for entity update events (async).

        Creates an async event filter that monitors entity update events. The callback
        receives (UpdateEvent, TxHash) for each updated entity.

        See `_watch_entity_event` for detailed documentation on parameters, return
        value, error handling, and usage examples.

        Note:
            If auto_start=True, you should await the filter's start() method
            to ensure it has started before continuing.
        """
        return await self._watch_entity_event(
            "updated", callback, from_block=from_block, auto_start=auto_start
        )

    async def watch_entity_extended(
        self,
        callback: AsyncExtendCallback,
        *,
        from_block: str | int = "latest",
        auto_start: bool = True,
    ) -> AsyncEventFilter:
        """
        Watch for entity extension events (async).

        Creates an async event filter that monitors entity lifetime extension events. The
        callback receives (ExtendEvent, TxHash) for each extended entity.

        See `_watch_entity_event` for detailed documentation on parameters, return
        value, error handling, and usage examples.

        Note:
            If auto_start=True, you should await the filter's start() method
            to ensure it has started before continuing.
        """
        return await self._watch_entity_event(
            "extended", callback, from_block=from_block, auto_start=auto_start
        )

    async def watch_entity_deleted(
        self,
        callback: AsyncDeleteCallback,
        *,
        from_block: str | int = "latest",
        auto_start: bool = True,
    ) -> AsyncEventFilter:
        """
        Watch for entity deletion events (async).

        Creates an async event filter that monitors entity deletion events. The
        callback receives (DeleteEvent, TxHash) for each deleted entity.

        See `_watch_entity_event` for detailed documentation on parameters, return
        value, error handling, and usage examples.

        Note:
            If auto_start=True, you should await the filter's start() method
            to ensure it has started before continuing.
        """
        return await self._watch_entity_event(
            "deleted", callback, from_block=from_block, auto_start=auto_start
        )

    async def cleanup_filters(self) -> None:
        """
        Stop and uninstall all active async event filters.

        This is automatically called when the AsyncArkiv client exits its context,
        but can be called manually if needed.
        """
        if not self._active_filters:
            logger.debug("No active filters to cleanup")
            return

        logger.info(
            f"Cleaning up {len(self._active_filters)} active async event filter(s)..."
        )

        for event_filter in self._active_filters:
            try:
                await event_filter.uninstall()
            except Exception as e:
                logger.warning(f"Error cleaning up async filter: {e}")

        self._active_filters.clear()
        logger.info("All async event filters cleaned up")

    @property
    def active_filters(self) -> list[AsyncEventFilter]:
        """Get a copy of currently active async event filters."""
        return list(self._active_filters)

    async def _watch_entity_event(
        self,
        event_type: EventType,
        callback: (
            AsyncCreateCallback
            | AsyncUpdateCallback
            | AsyncExtendCallback
            | AsyncDeleteCallback
        ),
        *,
        from_block: str | int = "latest",
        auto_start: bool = True,
    ) -> AsyncEventFilter:
        """
        Internal method to watch for entity events (async).

        This method creates an async event filter that monitors for entity events on the
        Arkiv storage contract. The callback is invoked each time the specified event
        occurs, receiving details about the event and the transaction hash.

        Args:
            event_type: Type of event to watch for ("created", "updated", "extended", "deleted")
            callback: Async function to call when an event is detected.
                     Receives (Event, TxHash) as arguments where Event is one of:
                     CreateEvent, UpdateEvent, ExtendEvent, or DeleteEvent depending on event_type.
            from_block: Starting block for the filter. Can be:
                       - "latest": Only watch for new events (default)
                       - Block number (int): Watch from a specific historical block
            auto_start: If True, starts polling immediately (default: True).
                       If False, you must manually await filter.start()

        Returns:
            AsyncEventFilter instance for controlling the watch. Use this to:
            - Stop polling: await filter.stop()
            - Resume polling: await filter.start()
            - Check status: filter.is_running
            - Cleanup: await filter.uninstall()

        Raises:
            ValueError: If callback is not callable
            RuntimeError: If filter creation fails

        Example:
            Basic usage with automatic start:
                >>> async def on_event(event: CreateEvent, tx_hash: TxHash) -> None:
                ...     print(f"Event occurred: {event.entity_key}")
                ...
                >>> filter = await arkiv.arkiv.watch_entity_created(on_event)
                >>> # Filter is now running and will call on_event for each event
                >>> # ... later ...
                >>> await filter.stop()  # Pause watching
                >>> await filter.uninstall()  # Cleanup resources

            Manual start/stop control:
                >>> async def on_event(event: UpdateEvent, tx_hash: TxHash) -> None:
                ...     print(f"Event occurred: {event.entity_key}")
                ...
                >>> filter = await arkiv.arkiv.watch_entity_updated(on_event, auto_start=False)
                >>> # Do some setup work...
                >>> await filter.start()  # Begin watching
                >>> # ... later ...
                >>> await filter.stop()  # Stop watching
                >>> await filter.uninstall()  # Cleanup

            Historical events from specific block:
                >>> filter = await arkiv.arkiv.watch_entity_extended(
                ...     on_event,
                ...     from_block=1000  # Start from block 1000
                ... )

        Note:
            - Only captures the specified event type (not other lifecycle events)
            - With from_block="latest", misses events before filter creation
            - Filter must be uninstalled via await filter.uninstall() to free resources
            - All active filters are automatically cleaned up when AsyncArkiv client
              context exits
            - Callback exceptions are caught and logged but don't stop the filter
            - Requires explicit await of start() when auto_start=True
        """
        event_filter = AsyncEventFilter(
            contract=self.contract,
            event_type=event_type,
            callback=callback,
            from_block=from_block,
        )

        # Start the filter if auto_start is enabled
        if auto_start:
            await event_filter.start()

        # Track the filter for cleanup
        self._active_filters.append(event_filter)

        return event_filter

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
