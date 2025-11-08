"""Base class for Arkiv module with shared functionality and documentation.

This module provides a base class pattern for sharing common methods, utility functions,
and documentation between synchronous (ArkivModule) and asynchronous (AsyncArkivModule)
implementations.

Key Design Decisions:
=====================
1. Public API methods (execute, create_entity, update_entity, etc.) are defined here with
   full docstrings and `raise NotImplementedError()` bodies. This provides a single source
   of truth for documentation while allowing both sync and async implementations to override.

2. Async methods use `# type: ignore[override]` to suppress mypy's return type checking,
   since async functions automatically wrap return types in Coroutine[Any, Any, T].

3. Subclass implementations include `# Docstring inherited from ArkivModuleBase.<method>`
   comments to indicate the documentation source.

4. Shared utility methods (_check_operations, _check_tx_and_get_receipt, etc.) are
   implemented directly in this base class.

This approach:
- Satisfies mypy's type checking (using type: ignore[override] for async)
- Avoids documentation duplication - single source of truth for all docstrings
- Provides clear method signatures for IDE autocomplete and type hints
- Shares utility method implementations between sync/async
- Makes it clear which methods differ between sync/async (async requires type: ignore)
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from eth_typing import ChecksumAddress
from web3.types import TxParams, TxReceipt

from arkiv.types import (
    ALL,
    QUERY_OPTIONS_DEFAULT,
    Attributes,
    Entity,
    EntityKey,
    Operations,
    QueryOptions,
    QueryPage,
    TransactionReceipt,
    TxHash,
)
from arkiv.utils import to_receipt

from .contract import EVENTS_ABI, FUNCTIONS_ABI, STORAGE_ADDRESS

if TYPE_CHECKING:
    pass

TX_SUCCESS = 1

logger = logging.getLogger(__name__)

# Generic type variable for the client (Arkiv or AsyncArkiv)
ClientT = TypeVar("ClientT")


class ArkivModuleBase(Generic[ClientT]):
    """Base class providing shared functionality for Arkiv modules.

    This class contains ONLY methods that are truly identical between sync and async:
    - Initialization (__init__)
    - Public API methods (execute, create_entity, update_entity, etc.)
    - Utility methods (_check_operations, _check_tx_and_get_receipt, etc.)
    """

    BTL_DEFAULT = (
        1000  # Default blocks to live for created entities (~30 mins with 2s blocks)
    )

    def __init__(self, client: ClientT, btl_default: int = BTL_DEFAULT) -> None:
        """Initialize Arkiv module with client reference.

        Args:
            client: Arkiv or AsyncArkiv client instance
            btl_default: Default blocks-to-live for created entities
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

        # Track active event filters for cleanup (type will be EventFilter or AsyncEventFilter)
        self._active_filters: list[Any] = []

    def is_available(self) -> bool:
        """Check if Arkiv functionality is available. Should always be true for Arkiv clients."""
        return True

    def execute(
        self, operations: Operations, tx_params: TxParams | None = None
    ) -> TransactionReceipt:
        """
        Execute operations on the Arkiv storage contract.

        This method processes a batch of entity operations (creates, updates, deletions,
        extensions) in a single blockchain transaction. It handles the transaction
        submission, waits for confirmation, and returns a detailed receipt with all
        emitted events.

        Args:
            operations: Operations to execute. Can contain any combination of:
                       - creates: List of CreateOp objects for new entities
                       - updates: List of UpdateOp objects to modify existing entities
                       - deletes: List of DeleteOp objects to remove entities
                       - extensions: List of ExtendOp objects to extend entity lifetimes
            tx_params: Optional transaction parameters to customize the transaction:
                      - from: Sender address (defaults to client's default account)
                      - gas: Gas limit (auto-estimated if not provided)
                      - gasPrice: Gas price (uses network default if not provided)
                      - nonce: Transaction nonce (auto-managed if not provided)
                      - value: ETH value to send (should be 0 for entity operations)

        Returns:
            TransactionReceipt containing:
            - tx_hash: Hash of the transaction
            - block_number: Block number where transaction was included
            - creates: List of CreateEvent for each created entity
            - updates: List of UpdateEvent for each updated entity
            - deletes: List of DeleteEvent for each deleted entity
            - extensions: List of ExtendEvent for each extended entity

        Raises:
            RuntimeError: If the transaction fails (status != 1)
            ValueError: If operations contain invalid data
            Web3RPCError: If RPC communication fails

        Example:
            Create and update entities in a single transaction:
                >>> operations = Operations(
                ...     creates=[CreateOp(payload=b"data", btl=100)],
                ...     updates=[UpdateOp(entity_key=key, payload=b"new", btl=100)]
                ... )
                >>> receipt = client.arkiv.execute(operations)
                >>> print(f"Created {len(receipt.creates)} entities")
                >>> print(f"Updated {len(receipt.updates)} entities")

        Note:
            - All operations in a batch succeed or fail together (atomic)
            - Transaction hash can be used to track confirmation externally
            - Events are emitted in the same order as operations
            - For async version, use 'await' before calling this method
        """
        raise NotImplementedError("Subclasses must implement execute()")

    def create_entity(
        self,
        payload: bytes | None = None,
        content_type: str | None = None,
        attributes: Attributes | None = None,
        btl: int | None = None,
        tx_params: TxParams | None = None,
    ) -> tuple[EntityKey, TransactionReceipt]:
        """
        Create a new entity on the Arkiv storage contract.

        Args:
            payload: Optional data payload for the entity (default: empty bytes)
            content_type: Optional content type for the payload (default: "application/octet-stream")
            attributes: Optional key-value attributes as metadata
            btl: Blocks to live - entity lifetime in blocks (default: self.btl_default)
            tx_params: Optional transaction parameters (gas, gasPrice, etc.)

        Returns:
            Tuple of (EntityKey, TransactionReceipt):
            - EntityKey: Unique identifier for the created entity
            - TransactionReceipt: Receipt with transaction details and emitted events

        Raises:
            RuntimeError: If the transaction fails or receipt validation fails
            ValueError: If invalid parameters are provided

        Example:
            >>> entity_key, receipt = client.arkiv.create_entity(
            ...     payload=b"Hello, Arkiv!",
            ...     attributes=Attributes({"type": "greeting", "version": 1}),
            ...     btl=1000
            ... )
            >>> print(f"Created entity: {entity_key}")

        Note:
            - When using AsyncArkiv, use 'await' before calling this method
            - Entity will expire after btl blocks from current block
            - All attributes values must be strings or non-negative integers
        """
        raise NotImplementedError("Subclasses must implement create_entity()")

    def update_entity(
        self,
        entity_key: EntityKey,
        payload: bytes | None = None,
        content_type: str | None = None,
        attributes: Attributes | None = None,
        btl: int | None = None,
        tx_params: TxParams | None = None,
    ) -> TransactionReceipt:
        """
        Update an existing entity on the Arkiv storage contract.

        All provided fields will replace the existing values. If a field is not provided,
        default values will be used (empty bytes for payload, empty dict for attributes).

        Args:
            entity_key: The entity key of the entity to update
            payload: Optional new data payload (default: empty bytes)
            content_type: Optional new content type (default: "application/octet-stream")
            attributes: Optional new attributes (default: empty dict)
            btl: New blocks to live from current block (default: self.btl_default)
            tx_params: Optional transaction parameters

        Returns:
            TransactionReceipt with transaction details and update events

        Raises:
            RuntimeError: If the transaction fails or entity doesn't exist
            ValueError: If invalid parameters are provided

        Example:
            >>> receipt = client.arkiv.update_entity(
            ...     entity_key=my_entity_key,
            ...     payload=b"Updated content",
            ...     attributes=Attributes({"status": "updated", "version": 2})
            ... )

        Note:
            - When using AsyncArkiv, use 'await' before calling this method
            - Updates replace all entity data, not merge
            - Owner cannot be changed via update (use transfer_owner for that)
        """
        raise NotImplementedError("Subclasses must implement update_entity()")

    def change_owner(
        self,
        entity_key: EntityKey,
        new_owner: ChecksumAddress,
        tx_params: TxParams | None = None,
    ) -> TransactionReceipt:
        """
        Change the owner of an entity.

        Args:
            entity_key: The entity key whose ownership to transfer
            new_owner: The address of the new owner
            tx_params: Optional transaction parameters

        Returns:
            TransactionReceipt with transaction details and ownership change events

        Raises:
            RuntimeError: If the transaction fails or entity doesn't exist
            ValueError: If entity_key or new_owner is invalid

        Example:
            >>> receipt = client.arkiv.change_owner(
            ...     entity_key=my_entity_key,
            ...     new_owner="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
            ... )

        Note:
            - When using AsyncArkiv, use 'await' before calling this method
            - Only the current owner can transfer ownership
            - New owner must be a valid Ethereum address
        """
        raise NotImplementedError("Subclasses must implement change_owner()")

    def extend_entity(
        self,
        entity_key: EntityKey,
        number_of_blocks: int,
        tx_params: TxParams | None = None,
    ) -> TransactionReceipt:
        """
        Extend the lifetime of an entity by a specified number of blocks.

        Args:
            entity_key: The entity key to extend
            number_of_blocks: Number of blocks to add to current expiration
            tx_params: Optional transaction parameters

        Returns:
            TransactionReceipt with transaction details and extension events

        Raises:
            RuntimeError: If the transaction fails or entity doesn't exist
            ValueError: If number_of_blocks is not positive

        Example:
            >>> receipt = client.arkiv.extend_entity(
            ...     entity_key=my_entity_key,
            ...     number_of_blocks=500  # Extend by ~15 minutes
            ... )

        Note:
            - When using AsyncArkiv, use 'await' before calling this method
            - Extension cost is proportional to number_of_blocks
            - Cannot extend already expired entities
        """
        raise NotImplementedError("Subclasses must implement extend_entity()")

    def delete_entity(
        self,
        entity_key: EntityKey,
        tx_params: TxParams | None = None,
    ) -> TransactionReceipt:
        """
        Delete an entity from the Arkiv storage contract.

        Args:
            entity_key: The entity key to delete
            tx_params: Optional transaction parameters

        Returns:
            TransactionReceipt with transaction details and deletion events

        Raises:
            RuntimeError: If the transaction fails or entity doesn't exist
            ValueError: If entity_key is invalid

        Example:
            >>> receipt = client.arkiv.delete_entity(entity_key=my_entity_key)

        Note:
            - When using AsyncArkiv, use 'await' before calling this method
            - Deleted entities cannot be recovered
            - Only entity owner can delete the entity
        """
        raise NotImplementedError("Subclasses must implement delete_entity()")

    def entity_exists(self, entity_key: EntityKey, at_block: int | None = None) -> bool:
        """
        Check if an entity exists in storage.

        Args:
            entity_key: The entity key to check
            at_block: Optional block number to check at (default: latest)

        Returns:
            True if the entity exists, False otherwise

        Example:
            >>> if client.arkiv.entity_exists(entity_key):
            ...     print("Entity exists!")

        Note:
            - When using AsyncArkiv, use 'await' before calling this method
            - Returns False for expired entities
            - Returns False if any error occurs during query
        """
        raise NotImplementedError("Subclasses must implement entity_exists()")

    def get_entity(
        self, entity_key: EntityKey, fields: int = ALL, at_block: int | None = None
    ) -> Entity:
        """
        Get an entity by its entity key.

        Args:
            entity_key: The entity key to retrieve
            fields: Bitfield indicating which fields to retrieve (default: ALL)
                   Use constants from types: KEY, ATTRIBUTES, PAYLOAD, CONTENT_TYPE,
                   EXPIRATION, OWNER, or combine with | operator
            at_block: Optional block number to query at (default: latest)

        Returns:
            Entity object with the requested fields populated

        Raises:
            ValueError: If entity not found or multiple entities returned

        Example:
            >>> entity = client.arkiv.get_entity(entity_key)
            >>> print(f"Payload: {entity.payload}")
            >>> print(f"Owner: {entity.owner}")

            Get only specific fields:
            >>> from arkiv.types import PAYLOAD, ATTRIBUTES
            >>> entity = client.arkiv.get_entity(
            ...     entity_key,
            ...     fields=PAYLOAD | ATTRIBUTES
            ... )

        Note:
            - When using AsyncArkiv, use 'await' before calling this method
            - Requesting fewer fields can improve performance
            - Use NONE to check existence without fetching data
        """
        raise NotImplementedError("Subclasses must implement get_entity()")

    def query_entities_page(
        self, query: str, options: QueryOptions = QUERY_OPTIONS_DEFAULT
    ) -> QueryPage:
        """
        Execute a query against entity storage.

        Args:
            query: SQL-like WHERE clause to filter entities
                  Examples: "$key = 123", "$attributes.type = 'user'"
            options: QueryOptions for fields, pagination, and block number
                    - fields: Which entity fields to retrieve
                    - at_block: Block number to query at
                    - max_results_per_page: Limit results
                    - cursor: For pagination (from previous QueryResult)

        Returns:
            QueryResult containing:
            - entities: List of matching Entity objects
            - block_number: Block number where query was executed
            - cursor: Optional cursor for next page (not yet implemented)

        Raises:
            ValueError: If both query and cursor provided, or neither provided

        Example:
            Query by attribute:
            >>> result = client.arkiv.query_entities(
            ...     "$attributes.type = 'user'",
            ...     options=QueryOptions(fields=PAYLOAD | ATTRIBUTES)
            ... )
            >>> for entity in result.entities:
            ...     print(entity.payload)

            Query with pagination:
            >>> result = client.arkiv.query_entities(
            ...     "$attributes.status = 'active'",
            ...     options=QueryOptions(max_results_per_page=10)
            ... )

        Note:
            - When using AsyncArkiv, use 'await' before calling this method
            - Query syntax is SQL-like with $ prefix for metadata fields
            - Results are ordered by entity key
            - Cursor-based pagination not yet fully implemented
        """
        raise NotImplementedError("Subclasses must implement query_entities()")

    # NOTE: Other public API methods (iterate_entities, watch_entity_*, etc.) could also
    # be defined here, but they have more significant differences between sync/async
    # (e.g., AsyncIterator vs Iterator, AsyncEventFilter vs EventFilter).

    def _check_operations(
        self, operations: Sequence[Any], operation_name: str, expected_count: int
    ) -> None:
        """Check that the number of operations matches the expected count."""
        if len(operations) != expected_count:
            raise RuntimeError(
                f"Expected {expected_count} '{operation_name}' operations but got {len(operations)}"
            )

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
