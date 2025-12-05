"""Batch operations for efficient multi-entity transactions.

This module provides batch builders that accumulate multiple entity operations
and execute them in a single transaction, significantly improving performance
and reducing costs compared to individual transactions.

Example:
    >>> with client.arkiv.batch() as batch:
    ...     for i in range(100):
    ...         batch.create_entity(payload=f"item {i}".encode())
    ...     batch.delete_entity(old_key)
    >>> # Single transaction with 101 operations
    >>> keys = [c.key for c in batch.receipt.creates]
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Literal, TypeVar

from eth_typing import ChecksumAddress

from .types import (
    Attributes,
    ChangeOwnerOp,
    CreateOp,
    DeleteOp,
    EntityKey,
    ExtendOp,
    Operations,
    TransactionReceipt,
    UpdateOp,
)
from .utils import to_create_op, to_update_op

if TYPE_CHECKING:
    from .module import ArkivModule
    from .module_async import AsyncArkivModule

# Generic type for the module (sync or async)
ModuleT = TypeVar("ModuleT", bound="ArkivModule | AsyncArkivModule")


class BatchBuilderBase(Generic[ModuleT]):
    """Base class for batch operation builders.

    Accumulates entity operations (create, update, extend, delete, change_owner)
    and provides methods with identical signatures to ArkivModule's single-entity
    methods. Operations are collected but not executed until execute() is called.

    This base class contains all shared logic. Subclasses (BatchBuilder and
    AsyncBatchBuilder) implement the execute() method appropriately.
    """

    def __init__(self, module: ModuleT) -> None:
        """Initialize batch builder with module reference.

        Args:
            module: ArkivModule or AsyncArkivModule instance for execution.
        """
        self._module = module
        self._creates: list[CreateOp] = []
        self._updates: list[UpdateOp] = []
        self._extensions: list[ExtendOp] = []
        self._change_owners: list[ChangeOwnerOp] = []
        self._deletes: list[DeleteOp] = []
        self._receipt: TransactionReceipt | None = None

    def _build_operations(self) -> Operations:
        """Build Operations from accumulated lists."""
        return Operations(
            creates=self._creates,
            updates=self._updates,
            extensions=self._extensions,
            deletes=self._deletes,
            change_owners=self._change_owners,
        )

    @property
    def operations(self) -> Operations:
        """Get the accumulated operations."""
        return self._build_operations()

    @property
    def receipt(self) -> TransactionReceipt | None:
        """Get the transaction receipt after execution."""
        return self._receipt

    @property
    def is_empty(self) -> bool:
        """Check if no operations have been added."""
        return (
            len(self._creates) == 0
            and len(self._updates) == 0
            and len(self._extensions) == 0
            and len(self._change_owners) == 0
            and len(self._deletes) == 0
        )

    @property
    def operation_count(self) -> int:
        """Get total number of accumulated operations."""
        return (
            len(self._creates)
            + len(self._updates)
            + len(self._extensions)
            + len(self._change_owners)
            + len(self._deletes)
        )

    def create_entity(
        self,
        payload: bytes | None = None,
        content_type: str | None = None,
        attributes: Attributes | None = None,
        expires_in: int | None = None,
    ) -> BatchBuilderBase[ModuleT]:
        """Add a create entity operation to the batch.

        Args:
            payload: Binary data for the entity.
            content_type: MIME type of the payload.
            attributes: Key-value attributes for the entity.
            expires_in: Lifetime in seconds.

        Returns:
            Self for method chaining.
        """
        create_op = to_create_op(
            payload=payload,
            content_type=content_type,
            attributes=attributes,
            expires_in=expires_in,
        )
        self._creates.append(create_op)
        return self

    def update_entity(
        self,
        entity_key: EntityKey,
        payload: bytes | None = None,
        content_type: str | None = None,
        attributes: Attributes | None = None,
        expires_in: int | None = None,
    ) -> BatchBuilderBase[ModuleT]:
        """Add an update entity operation to the batch.

        Args:
            entity_key: Key of the entity to update.
            payload: New binary data for the entity.
            content_type: New MIME type of the payload.
            attributes: New key-value attributes.
            expires_in: New lifetime in seconds.

        Returns:
            Self for method chaining.
        """
        update_op = to_update_op(
            entity_key=entity_key,
            payload=payload,
            content_type=content_type,
            attributes=attributes,
            expires_in=expires_in,
        )
        self._updates.append(update_op)
        return self

    def extend_entity(
        self,
        entity_key: EntityKey,
        extend_by: int,
    ) -> BatchBuilderBase[ModuleT]:
        """Add an extend entity operation to the batch.

        Args:
            entity_key: Key of the entity to extend.
            extend_by: Number of seconds to extend the entity's lifetime.

        Returns:
            Self for method chaining.
        """
        extend_op = ExtendOp(key=entity_key, extend_by=extend_by)
        self._extensions.append(extend_op)
        return self

    def change_owner(
        self,
        entity_key: EntityKey,
        new_owner: ChecksumAddress,
    ) -> BatchBuilderBase[ModuleT]:
        """Add a change owner operation to the batch.

        Args:
            entity_key: Key of the entity to transfer.
            new_owner: Address of the new owner.

        Returns:
            Self for method chaining.
        """
        change_owner_op = ChangeOwnerOp(key=entity_key, new_owner=new_owner)
        self._change_owners.append(change_owner_op)
        return self

    def delete_entity(
        self,
        entity_key: EntityKey,
    ) -> BatchBuilderBase[ModuleT]:
        """Add a delete entity operation to the batch.

        Args:
            entity_key: Key of the entity to delete.

        Returns:
            Self for method chaining.
        """
        delete_op = DeleteOp(key=entity_key)
        self._deletes.append(delete_op)
        return self

    def clear(self) -> BatchBuilderBase[ModuleT]:
        """Clear all accumulated operations.

        Returns:
            Self for method chaining.
        """
        self._creates = []
        self._updates = []
        self._extensions = []
        self._deletes = []
        self._change_owners = []
        self._receipt = None
        return self


class BatchBuilder(BatchBuilderBase["ArkivModule"]):
    """Synchronous batch builder for accumulating and executing entity operations.

    Usage:
        >>> with client.arkiv.batch() as batch:
        ...     batch.create_entity(payload=b"data1")
        ...     batch.create_entity(payload=b"data2")
        >>> # Access results
        >>> keys = [c.key for c in batch.receipt.creates]

        >>> # Or without context manager
        >>> batch = client.arkiv.batch()
        >>> batch.create_entity(payload=b"data")
        >>> receipt = batch.execute()
    """

    def execute(self) -> TransactionReceipt:
        """Execute all accumulated operations in a single transaction.

        Returns:
            TransactionReceipt with results of all operations.

        Raises:
            RuntimeError: If no operations have been added.
        """
        if self.is_empty:
            raise RuntimeError("Cannot execute empty batch - no operations added")

        operations = self._build_operations()
        self._receipt = self._module.execute(operations)
        return self._receipt

    def __enter__(self) -> BatchBuilder:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> Literal[False]:
        """Exit context manager, executing batch if no exception occurred."""
        if exc_type is None and not self.is_empty:
            self.execute()
        return False


class AsyncBatchBuilder(BatchBuilderBase["AsyncArkivModule"]):
    """Asynchronous batch builder for accumulating and executing entity operations.

    Usage:
        >>> async with client.arkiv.batch() as batch:
        ...     batch.create_entity(payload=b"data1")
        ...     batch.create_entity(payload=b"data2")
        >>> # Access results
        >>> keys = [c.key for c in batch.receipt.creates]

        >>> # Or without context manager
        >>> batch = client.arkiv.batch()
        >>> batch.create_entity(payload=b"data")
        >>> receipt = await batch.execute()
    """

    async def execute(self) -> TransactionReceipt:
        """Execute all accumulated operations in a single transaction.

        Returns:
            TransactionReceipt with results of all operations.

        Raises:
            RuntimeError: If no operations have been added.
        """
        if self.is_empty:
            raise RuntimeError("Cannot execute empty batch - no operations added")

        operations = self._build_operations()
        self._receipt = await self._module.execute(operations)
        return self._receipt

    async def __aenter__(self) -> AsyncBatchBuilder:
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> Literal[False]:
        """Exit async context manager, executing batch if no exception occurred."""
        if exc_type is None and not self.is_empty:
            await self.execute()
        return False
