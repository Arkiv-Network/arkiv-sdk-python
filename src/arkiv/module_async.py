"""Async entity management module for Arkiv client."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any

from eth_typing import HexStr
from web3.types import TxParams, TxReceipt

from .events_async import AsyncEventFilter
from .module_base import ArkivModuleBase
from .types import (
    ALL,
    NONE,
    QUERY_OPTIONS_DEFAULT,
    Annotations,
    AsyncCreateCallback,
    AsyncDeleteCallback,
    AsyncExtendCallback,
    AsyncUpdateCallback,
    DeleteOp,
    Entity,
    EntityKey,
    EventType,
    ExtendOp,
    Operations,
    QueryOptions,
    QueryResult,
    TransactionReceipt,
    TxHash,
)
from .utils import (
    to_create_op,
    to_query_result,
    to_rpc_query_options,
    to_tx_params,
    to_update_op,
)

# Deal with potential circular imports between client.py and module_async.py
if TYPE_CHECKING:
    from .client import AsyncArkiv  # noqa: F401 - used in Generic type parameter

logger = logging.getLogger(__name__)


class AsyncArkivModule(ArkivModuleBase["AsyncArkiv"]):
    """Async Arkiv module for entity management operations."""

    async def execute(  # type: ignore[override]
        self, operations: Operations, tx_params: TxParams | None = None
    ) -> TransactionReceipt:
        # Docstring inherited from ArkivModuleBase.execute
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

    async def create_entity(  # type: ignore[override]
        self,
        payload: bytes | None = None,
        content_type: str | None = None,
        annotations: Annotations | None = None,
        btl: int | None = None,
        tx_params: TxParams | None = None,
    ) -> tuple[EntityKey, TransactionReceipt]:
        # Docstring inherited from ArkivModuleBase.create_entity
        # Create the operation and execute TX
        create_op = to_create_op(
            payload=payload, content_type=content_type, annotations=annotations, btl=btl
        )
        operations = Operations(creates=[create_op])
        receipt = await self.execute(operations, tx_params)

        # Verify we got at least one create
        creates = receipt.creates
        self._check_operations(receipt.creates, "create", 1)

        # Return entity key and receipt
        entity_key = creates[0].entity_key
        return entity_key, receipt

    async def update_entity(  # type: ignore[override]
        self,
        entity_key: EntityKey,
        payload: bytes | None = None,
        content_type: str | None = None,
        annotations: Annotations | None = None,
        btl: int | None = None,
        tx_params: TxParams | None = None,
    ) -> TransactionReceipt:
        # Docstring inherited from ArkivModuleBase.update_entity
        # Create the update operation and execute TX
        update_op = to_update_op(
            entity_key=entity_key,
            payload=payload,
            content_type=content_type,
            annotations=annotations,
            btl=btl,
        )
        operations = Operations(updates=[update_op])
        receipt = await self.execute(operations, tx_params)

        # Verify receipt and return receipt
        self._check_operations(receipt.updates, "update", 1)
        return receipt

    async def extend_entity(  # type: ignore[override]
        self,
        entity_key: EntityKey,
        number_of_blocks: int,
        tx_params: TxParams | None = None,
    ) -> TransactionReceipt:
        # Docstring inherited from ArkivModuleBase.extend_entity
        # Create the extend operation and execute TX
        extend_op = ExtendOp(entity_key=entity_key, number_of_blocks=number_of_blocks)
        operations = Operations(extensions=[extend_op])
        receipt = await self.execute(operations, tx_params)

        # Verify and return receipt
        self._check_operations(receipt.extensions, "extend", 1)
        return receipt

    async def delete_entity(  # type: ignore[override]
        self,
        entity_key: EntityKey,
        tx_params: TxParams | None = None,
    ) -> TransactionReceipt:
        # Docstring inherited from ArkivModuleBase.delete_entity
        # Create the delete operation and execute TX
        delete_op = DeleteOp(entity_key=entity_key)
        operations = Operations(deletes=[delete_op])
        receipt = await self.execute(operations, tx_params)

        # Verify and return receipt
        self._check_operations(receipt.deletes, "delete", 1)
        return receipt

    async def entity_exists(  # type: ignore[override]
        self, entity_key: EntityKey, at_block: int | None = None
    ) -> bool:
        # Docstring inherited from ArkivModuleBase.entity_exists
        try:
            options = QueryOptions(fields=NONE, at_block=at_block)
            query_result: QueryResult = await self.query_entities(
                f"$key = {entity_key}", options=options
            )
            return len(query_result.entities) > 0
        except Exception:
            return False

    async def get_entity(  # type: ignore[override]
        self, entity_key: EntityKey, fields: int = ALL, at_block: int | None = None
    ) -> Entity:
        # Docstring inherited from ArkivModuleBase.get_entity
        options = QueryOptions(fields=fields, at_block=at_block)
        query_result: QueryResult = await self.query_entities(
            f"$key = {entity_key}", options=options
        )

        if not query_result:
            raise ValueError(f"Entity not found: {entity_key}")

        if len(query_result.entities) != 1:
            raise ValueError(f"Expected 1 entity, got {len(query_result.entities)}")

        result_entity = query_result.entities[0]
        return result_entity

    async def query_entities(  # type: ignore[override]
        self,
        query: str | None = None,
        options: QueryOptions = QUERY_OPTIONS_DEFAULT,
    ) -> QueryResult:
        # Docstring inherited from ArkivModuleBase.query_entities
        options.validate(query)
        rpc_options = to_rpc_query_options(options)
        raw_results = await self.client.eth.query(query, rpc_options)

        return to_query_result(options.fields, raw_results)

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
