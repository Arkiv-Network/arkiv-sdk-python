"""Tests for batch operations."""

import pytest

from arkiv.batch import AsyncBatchBuilder, BatchBuilder
from arkiv.types import EntityKey


class TestBatchBuilderBase:
    """Tests for BatchBuilderBase shared functionality."""

    def test_batch_initial_state_is_empty(self, arkiv_client_http):
        """Test that a new batch builder has no operations."""
        # We need to test via BatchBuilder since Base is generic
        batch = BatchBuilder(arkiv_client_http.arkiv)

        assert batch.is_empty
        assert batch.operation_count == 0
        assert batch.receipt is None

    def test_batch_create_entity_adds_operation(self, arkiv_client_http):
        """Test that create_entity adds a create operation."""
        batch = BatchBuilder(arkiv_client_http.arkiv)

        result = batch.create_entity(
            payload=b"test data",
            content_type="text/plain",
            attributes={"type": "test"},
            expires_in=3600,
        )

        assert result is batch  # Returns self for chaining
        assert not batch.is_empty
        assert batch.operation_count == 1
        assert len(batch.operations.creates) == 1

    def test_batch_update_entity_adds_operation(self, arkiv_client_http):
        """Test that update_entity adds an update operation."""
        batch = BatchBuilder(arkiv_client_http.arkiv)
        entity_key = EntityKey("0x" + "ab" * 32)

        result = batch.update_entity(
            entity_key=entity_key,
            payload=b"updated data",
            expires_in=3600,
        )

        assert result is batch
        assert batch.operation_count == 1
        assert len(batch.operations.updates) == 1

    def test_batch_extend_entity_adds_operation(self, arkiv_client_http):
        """Test that extend_entity adds an extend operation."""
        batch = BatchBuilder(arkiv_client_http.arkiv)
        entity_key = EntityKey("0x" + "ab" * 32)

        result = batch.extend_entity(entity_key=entity_key, extend_by=7200)

        assert result is batch
        assert batch.operation_count == 1
        assert len(batch.operations.extensions) == 1
        assert batch.operations.extensions[0].extend_by == 7200

    def test_batch_change_owner_adds_operation(self, arkiv_client_http):
        """Test that change_owner adds a change owner operation."""
        batch = BatchBuilder(arkiv_client_http.arkiv)
        entity_key = EntityKey("0x" + "ab" * 32)
        new_owner = "0x" + "cd" * 20

        result = batch.change_owner(entity_key=entity_key, new_owner=new_owner)

        assert result is batch
        assert batch.operation_count == 1
        assert len(batch.operations.change_owners) == 1

    def test_batch_delete_entity_adds_operation(self, arkiv_client_http):
        """Test that delete_entity adds a delete operation."""
        batch = BatchBuilder(arkiv_client_http.arkiv)
        entity_key = EntityKey("0x" + "ab" * 32)

        result = batch.delete_entity(entity_key=entity_key)

        assert result is batch
        assert batch.operation_count == 1
        assert len(batch.operations.deletes) == 1

    def test_batch_multiple_operations_accumulate(self, arkiv_client_http):
        """Test that multiple operations accumulate correctly."""
        batch = BatchBuilder(arkiv_client_http.arkiv)
        entity_key = EntityKey("0x" + "ab" * 32)

        batch.create_entity(payload=b"data1", expires_in=3600)
        batch.create_entity(payload=b"data2", expires_in=3600)
        batch.create_entity(payload=b"data3", expires_in=3600)
        batch.update_entity(entity_key, payload=b"updated", expires_in=3600)
        batch.delete_entity(entity_key)

        assert batch.operation_count == 5
        assert len(batch.operations.creates) == 3
        assert len(batch.operations.updates) == 1
        assert len(batch.operations.deletes) == 1

    def test_batch_method_chaining(self, arkiv_client_http):
        """Test that methods can be chained."""
        batch = BatchBuilder(arkiv_client_http.arkiv)
        entity_key = EntityKey("0x" + "ab" * 32)

        batch.create_entity(payload=b"data1", expires_in=3600).create_entity(
            payload=b"data2", expires_in=3600
        ).update_entity(entity_key, payload=b"updated", expires_in=3600).delete_entity(
            entity_key
        )

        assert batch.operation_count == 4

    def test_batch_clear_removes_all_operations(self, arkiv_client_http):
        """Test that clear removes all accumulated operations."""
        batch = BatchBuilder(arkiv_client_http.arkiv)

        batch.create_entity(payload=b"data1", expires_in=3600)
        batch.create_entity(payload=b"data2", expires_in=3600)
        assert batch.operation_count == 2

        result = batch.clear()

        assert result is batch
        assert batch.is_empty
        assert batch.operation_count == 0
        assert batch.receipt is None


class TestBatchBuilder:
    """Tests for synchronous BatchBuilder execution."""

    def test_batch_execute_empty_batch_raises_error(self, arkiv_client_http):
        """Test that executing an empty batch raises RuntimeError."""
        batch = BatchBuilder(arkiv_client_http.arkiv)

        with pytest.raises(RuntimeError, match="Cannot execute empty batch"):
            batch.execute()

    def test_batch_execute_single_create(self, arkiv_client_http):
        """Test executing a batch with a single create operation."""
        batch = BatchBuilder(arkiv_client_http.arkiv)
        batch.create_entity(
            payload=b"batch test",
            attributes={"type": "batch_test"},
            expires_in=3600,
        )

        receipt = batch.execute()

        assert receipt is not None
        assert len(receipt.creates) == 1
        assert batch.receipt is receipt

        # Verify entity was created
        entity = arkiv_client_http.arkiv.get_entity(receipt.creates[0].key)
        assert entity.payload == b"batch test"

    def test_batch_execute_multiple_creates(self, arkiv_client_http):
        """Test executing a batch with multiple create operations."""
        batch = BatchBuilder(arkiv_client_http.arkiv)

        for i in range(5):
            batch.create_entity(
                payload=f"item {i}".encode(),
                attributes={"type": "batch_test", "index": i},
                expires_in=3600,
            )

        receipt = batch.execute()

        assert len(receipt.creates) == 5

        # Verify all entities were created
        for i, create_event in enumerate(receipt.creates):
            entity = arkiv_client_http.arkiv.get_entity(create_event.key)
            assert entity.payload == f"item {i}".encode()

    def test_batch_execute_mixed_operations(self, arkiv_client_http):
        """Test executing a batch with mixed operation types."""
        # First create an entity to update/delete
        key1, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"original",
            attributes={"type": "batch_test"},
            expires_in=3600,
        )

        batch = BatchBuilder(arkiv_client_http.arkiv)
        batch.create_entity(payload=b"new entity", expires_in=3600)
        batch.update_entity(key1, payload=b"updated via batch", expires_in=3600)

        receipt = batch.execute()

        assert len(receipt.creates) == 1
        assert len(receipt.updates) == 1

        # Verify update
        entity = arkiv_client_http.arkiv.get_entity(key1)
        assert entity.payload == b"updated via batch"

    def test_batch_context_manager_executes_on_exit(self, arkiv_client_http):
        """Test that context manager executes batch on normal exit."""
        with BatchBuilder(arkiv_client_http.arkiv) as batch:
            batch.create_entity(payload=b"context manager test", expires_in=3600)

        assert batch.receipt is not None
        assert len(batch.receipt.creates) == 1

    def test_batch_context_manager_does_not_execute_on_exception(
        self, arkiv_client_http
    ):
        """Test that context manager doesn't execute on exception."""
        batch = None
        try:
            with BatchBuilder(arkiv_client_http.arkiv) as batch:
                batch.create_entity(payload=b"should not be created", expires_in=3600)
                raise ValueError("Test exception")
        except ValueError:
            pass

        assert batch is not None
        assert batch.receipt is None

    def test_batch_context_manager_does_not_execute_empty_batch(
        self, arkiv_client_http
    ):
        """Test that context manager doesn't execute if batch is empty."""
        with BatchBuilder(arkiv_client_http.arkiv) as batch:
            pass  # No operations added

        assert batch.receipt is None

    def test_batch_loop_creates_in_batch(self, arkiv_client_http):
        """Test creating entities in a loop within batch context."""
        items = [{"name": f"item_{i}", "value": i * 10} for i in range(10)]

        with BatchBuilder(arkiv_client_http.arkiv) as batch:
            for item in items:
                batch.create_entity(
                    payload=item["name"].encode(),
                    attributes={"type": "loop_test", "value": item["value"]},
                    expires_in=3600,
                )

        assert batch.receipt is not None
        assert len(batch.receipt.creates) == 10

        # Verify entities
        for i, create_event in enumerate(batch.receipt.creates):
            entity = arkiv_client_http.arkiv.get_entity(create_event.key)
            assert entity.payload == f"item_{i}".encode()


class TestAsyncBatchBuilder:
    """Tests for asynchronous AsyncBatchBuilder execution."""

    @pytest.mark.asyncio
    async def test_async_batch_execute_empty_batch_raises_error(
        self, async_arkiv_client_http
    ):
        """Test that executing an empty async batch raises RuntimeError."""
        async with async_arkiv_client_http as client:
            batch = AsyncBatchBuilder(client.arkiv)

            with pytest.raises(RuntimeError, match="Cannot execute empty batch"):
                await batch.execute()

    @pytest.mark.asyncio
    async def test_async_batch_execute_single_create(self, async_arkiv_client_http):
        """Test executing an async batch with a single create operation."""
        async with async_arkiv_client_http as client:
            batch = AsyncBatchBuilder(client.arkiv)
            batch.create_entity(
                payload=b"async batch test",
                attributes={"type": "async_batch_test"},
                expires_in=3600,
            )

            receipt = await batch.execute()

            assert receipt is not None
            assert len(receipt.creates) == 1
            assert batch.receipt is receipt

            # Verify entity was created
            entity = await client.arkiv.get_entity(receipt.creates[0].key)
            assert entity.payload == b"async batch test"

    @pytest.mark.asyncio
    async def test_async_batch_execute_multiple_creates(self, async_arkiv_client_http):
        """Test executing an async batch with multiple creates."""
        async with async_arkiv_client_http as client:
            batch = AsyncBatchBuilder(client.arkiv)

            for i in range(5):
                batch.create_entity(
                    payload=f"async item {i}".encode(),
                    attributes={"type": "async_batch_test", "index": i},
                    expires_in=3600,
                )

            receipt = await batch.execute()

            assert len(receipt.creates) == 5

    @pytest.mark.asyncio
    async def test_async_batch_context_manager_executes_on_exit(
        self, async_arkiv_client_http
    ):
        """Test that async context manager executes batch on normal exit."""
        async with async_arkiv_client_http as client:
            async with AsyncBatchBuilder(client.arkiv) as batch:
                batch.create_entity(
                    payload=b"async context manager test", expires_in=3600
                )

            assert batch.receipt is not None
            assert len(batch.receipt.creates) == 1

    @pytest.mark.asyncio
    async def test_async_context_manager_does_not_execute_on_exception(
        self, async_arkiv_client_http
    ):
        """Test that async context manager doesn't execute on exception."""
        async with async_arkiv_client_http as client:
            batch = None
            try:
                async with AsyncBatchBuilder(client.arkiv) as batch:
                    batch.create_entity(
                        payload=b"should not be created", expires_in=3600
                    )
                    raise ValueError("Test exception")
            except ValueError:
                pass

            assert batch is not None
            assert batch.receipt is None

    @pytest.mark.asyncio
    async def test_async_loop_creates_in_async_batch(self, async_arkiv_client_http):
        """Test creating entities in a loop within async batch context."""
        async with async_arkiv_client_http as client:
            items = [{"name": f"async_item_{i}", "value": i * 10} for i in range(10)]

            async with AsyncBatchBuilder(client.arkiv) as batch:
                for item in items:
                    batch.create_entity(
                        payload=item["name"].encode(),
                        attributes={"type": "async_loop_test", "value": item["value"]},
                        expires_in=3600,
                    )

            assert batch.receipt is not None
            assert len(batch.receipt.creates) == 10


class TestModuleIntegration:
    """Tests for batch() method integration on ArkivModule."""

    def test_batch_method_returns_batch_builder(self, arkiv_client_http):
        """Test that arkiv.batch() returns a BatchBuilder."""
        batch = arkiv_client_http.arkiv.batch()

        assert isinstance(batch, BatchBuilder)
        assert batch.is_empty

    def test_batch_method_context_manager(self, arkiv_client_http):
        """Test using arkiv.batch() as context manager."""
        with arkiv_client_http.arkiv.batch() as batch:
            batch.create_entity(payload=b"module batch test", expires_in=3600)

        assert batch.receipt is not None
        assert len(batch.receipt.creates) == 1

    @pytest.mark.asyncio
    async def test_async_batch_method_returns_async_batch_builder(
        self, async_arkiv_client_http
    ):
        """Test that async arkiv.batch() returns an AsyncBatchBuilder."""
        async with async_arkiv_client_http as client:
            batch = client.arkiv.batch()

            assert isinstance(batch, AsyncBatchBuilder)
            assert batch.is_empty

    @pytest.mark.asyncio
    async def test_async_batch_method_context_manager(self, async_arkiv_client_http):
        """Test using async arkiv.batch() as async context manager."""
        async with async_arkiv_client_http as client:
            async with client.arkiv.batch() as batch:
                batch.create_entity(payload=b"async module batch test", expires_in=3600)

            assert batch.receipt is not None
            assert len(batch.receipt.creates) == 1


class TestBatchMultiStepWorkflow:
    """Integration tests for multi-batch workflows with all operation types."""

    def test_batch_five_workflow(self, arkiv_client_http, account_1, account_2):
        """Test a complex workflow spanning 5 batches with all operation types.

        This test exercises:
        - Creating entities across multiple batches
        - Updating entities created in previous batches
        - Extending entity lifetimes
        - Changing entity ownership
        - Deleting entities
        """
        # Track entities created in each batch
        batch1_keys = []
        batch2_keys = []
        batch3_keys = []
        batch4_keys = []
        batch5_keys = []

        # ===== Batch #1: Create 2 simple entities =====
        with arkiv_client_http.arkiv.batch() as batch:
            batch.create_entity(payload=b"batch1 entity1", expires_in=3600)
            batch.create_entity(payload=b"batch1 entity2", expires_in=3600)

        assert len(batch.receipt.creates) == 2
        batch1_keys = [c.key for c in batch.receipt.creates]

        # Verify batch #1 entities
        for i, key in enumerate(batch1_keys):
            entity = arkiv_client_http.arkiv.get_entity(key)
            assert entity.payload == f"batch1 entity{i + 1}".encode()
            assert entity.attributes.get("name") is None  # No attributes yet

        # ===== Batch #2: Create 2 more + update batch #1 entities =====
        with arkiv_client_http.arkiv.batch() as batch:
            # Create new entities
            batch.create_entity(payload=b"batch2 entity1", expires_in=3600)
            batch.create_entity(payload=b"batch2 entity2", expires_in=3600)
            # Update batch #1 entities with attributes
            for i, key in enumerate(batch1_keys):
                batch.update_entity(
                    key,
                    payload=f"batch1 entity{i + 1} updated".encode(),
                    attributes={"name": f"entity1_{i}", "version": 1},
                    expires_in=3600,
                )

        assert len(batch.receipt.creates) == 2
        assert len(batch.receipt.updates) == 2
        batch2_keys = [c.key for c in batch.receipt.creates]

        # Verify batch #1 entities were updated
        for i, key in enumerate(batch1_keys):
            entity = arkiv_client_http.arkiv.get_entity(key)
            assert entity.payload == f"batch1 entity{i + 1} updated".encode()
            assert entity.attributes["name"] == f"entity1_{i}"
            assert entity.attributes["version"] == 1

        # ===== Batch #3: Create 2 + update batch #2 + extend batch #1 =====
        batch1_expires_before = [
            arkiv_client_http.arkiv.get_entity(k).expires_at_block for k in batch1_keys
        ]

        with arkiv_client_http.arkiv.batch() as batch:
            # Create new entities
            batch.create_entity(payload=b"batch3 entity1", expires_in=3600)
            batch.create_entity(payload=b"batch3 entity2", expires_in=3600)
            # Update batch #2 entities
            for i, key in enumerate(batch2_keys):
                batch.update_entity(
                    key,
                    payload=f"batch2 entity{i + 1} updated".encode(),
                    attributes={"name": f"entity2_{i}", "version": 1},
                    expires_in=3600,
                )
            # Extend batch #1 entities
            for key in batch1_keys:
                batch.extend_entity(key, extend_by=1000)

        assert len(batch.receipt.creates) == 2
        assert len(batch.receipt.updates) == 2
        assert len(batch.receipt.extensions) == 2
        batch3_keys = [c.key for c in batch.receipt.creates]

        # Verify batch #1 entities were extended
        for i, key in enumerate(batch1_keys):
            entity = arkiv_client_http.arkiv.get_entity(key)
            assert entity.expires_at_block > batch1_expires_before[i]
            # TODO logging output of expires_at_block_before and after for debugging

        # Verify batch #2 entities were updated
        for i, key in enumerate(batch2_keys):
            entity = arkiv_client_http.arkiv.get_entity(key)
            assert entity.attributes["name"] == f"entity2_{i}"

        # ===== Batch #4: Create 2 + update batch #3 + extend batch #2 + change owner batch #1 =====
        batch2_expires_before = [
            arkiv_client_http.arkiv.get_entity(k).expires_at_block for k in batch2_keys
        ]

        # Verify batch #1 entities have expected old owner
        for key in batch1_keys:
            entity = arkiv_client_http.arkiv.get_entity(key)
            assert entity.owner == account_1.address

        with arkiv_client_http.arkiv.batch() as batch:
            # Create new entities
            batch.create_entity(payload=b"batch4 entity1", expires_in=3600)
            batch.create_entity(payload=b"batch4 entity2", expires_in=3600)
            # Update batch #3 entities
            for i, key in enumerate(batch3_keys):
                batch.update_entity(
                    key,
                    payload=f"batch3 entity{i + 1} updated".encode(),
                    attributes={"name": f"entity3_{i}", "version": 1},
                    expires_in=3600,
                )
            # Extend batch #2 entities
            for key in batch2_keys:
                batch.extend_entity(key, extend_by=2000)
            # Change owner of batch #1 entities
            for key in batch1_keys:
                batch.change_owner(key, account_2.address)

        assert len(batch.receipt.creates) == 2
        assert len(batch.receipt.updates) == 2
        assert len(batch.receipt.extensions) == 2
        assert len(batch.receipt.change_owners) == 2
        batch4_keys = [c.key for c in batch.receipt.creates]

        # Verify batch #1 entities have new owner
        for key in batch1_keys:
            entity = arkiv_client_http.arkiv.get_entity(key)
            assert entity.owner == account_2.address

        # Verify batch #2,3,4 entities still have original owner
        for key in batch2_keys + batch3_keys + batch4_keys:
            entity = arkiv_client_http.arkiv.get_entity(key)
            assert entity.owner == account_1.address

        # Verify batch #2 have been extended
        for i, key in enumerate(batch2_keys):
            entity = arkiv_client_http.arkiv.get_entity(key)
            assert entity.expires_at_block > batch2_expires_before[i]

        # ===== Batch #5: Create 2 + update batch #4 + extend batch #3 + delete batch #2 =====
        # We delete batch #2 entities which are still owned by account_1
        batch3_expires_before = [
            arkiv_client_http.arkiv.get_entity(k).expires_at_block for k in batch3_keys
        ]

        with arkiv_client_http.arkiv.batch() as batch:
            # Create new entities
            batch.create_entity(payload=b"batch5 entity1", expires_in=3600)
            batch.create_entity(payload=b"batch5 entity2", expires_in=3600)
            # Update batch #4 entities
            for i, key in enumerate(batch4_keys):
                batch.update_entity(
                    key,
                    payload=f"batch4 entity{i + 1} updated".encode(),
                    attributes={"name": f"entity4_{i}", "version": 1},
                    expires_in=3600,
                )
            # Extend batch #3 entities
            for key in batch3_keys:
                batch.extend_entity(key, extend_by=2000)
            # Delete batch #2 entities (still owned by account_1)
            for key in batch2_keys:
                batch.delete_entity(key)

        assert len(batch.receipt.creates) == 2
        assert len(batch.receipt.updates) == 2
        assert len(batch.receipt.extensions) == 2
        assert len(batch.receipt.deletes) == 2
        batch5_keys = [c.key for c in batch.receipt.creates]

        # Verify batch #5 entities were created
        for i, key in enumerate(batch5_keys):
            entity = arkiv_client_http.arkiv.get_entity(key)
            assert entity.payload == f"batch5 entity{i + 1}".encode()
            assert entity.owner == account_1.address

        # Verify batch #4 entities were updated
        for i, key in enumerate(batch4_keys):
            entity = arkiv_client_http.arkiv.get_entity(key)
            assert entity.attributes["name"] == f"entity4_{i}"
            assert entity.owner == account_1.address

        # Verify batch #3 entities were extended
        for i, key in enumerate(batch3_keys):
            entity = arkiv_client_http.arkiv.get_entity(key)
            assert entity.expires_at_block > batch3_expires_before[i]

        # Verify batch #2 entities were deleted (should not exist)
        for key in batch2_keys:
            assert not arkiv_client_http.arkiv.entity_exists(key)

        # Verify batch #1 entities still owned by account_2 (changed in batch #4)
        for key in batch1_keys:
            entity = arkiv_client_http.arkiv.get_entity(key)
            assert entity.owner == account_2.address

        # Final summary: we should have 8 entities remaining
        # batch1: 2 (owned by account_2, changed in batch #4)
        # batch2: 0 (deleted in batch #5)
        # batch3: 2 (owned by account_1)
        # batch4: 2 (owned by account_1)
        # batch5: 2 (owned by account_1)
        remaining_keys = batch1_keys + batch3_keys + batch4_keys + batch5_keys
        for key in remaining_keys:
            assert arkiv_client_http.arkiv.entity_exists(key)
