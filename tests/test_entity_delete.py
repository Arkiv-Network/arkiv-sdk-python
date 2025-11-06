"""Tests for entity deletion functionality in ArkivModule."""

import logging

import pytest

from arkiv.client import Arkiv
from arkiv.types import Attributes, CreateOp, DeleteOp, Operations

from .utils import bulk_create_entities, check_tx_hash

logger = logging.getLogger(__name__)


class TestEntityDelete:
    """Test cases for delete_entity function."""

    def test_delete_entity_simple(self, arkiv_client_http: Arkiv) -> None:
        """Test deleting a single entity."""
        # First, create an entity to delete
        payload = b"Test entity for deletion"
        attributes: Attributes = Attributes({"type": "test", "purpose": "deletion"})
        btl = 100

        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=payload, attributes=attributes, btl=btl
        )

        logger.info(f"Created entity {entity_key} for deletion test")

        # Verify the entity exists
        assert arkiv_client_http.arkiv.entity_exists(entity_key), (
            "Entity should exist after creation"
        )

        # Delete the entity
        delete_tx_hash = arkiv_client_http.arkiv.delete_entity(entity_key)

        label = "delete_entity"
        check_tx_hash(label, delete_tx_hash)
        logger.info(f"{label}: Deleted entity {entity_key}, tx_hash: {delete_tx_hash}")

        # Verify the entity no longer exists
        assert not arkiv_client_http.arkiv.entity_exists(entity_key), (
            "Entity should not exist after deletion"
        )

        logger.info(f"{label}: Entity deletion successful")

    def test_delete_multiple_entities_sequentially(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test deleting multiple entities one by one."""
        # Create multiple entities
        entity_keys = []
        for i in range(3):
            payload = f"Entity {i} for sequential deletion".encode()
            attributes: Attributes = Attributes({"index": i, "batch": "sequential"})
            entity_key, _ = arkiv_client_http.arkiv.create_entity(
                payload=payload, attributes=attributes, btl=150
            )
            entity_keys.append(entity_key)

        logger.info(f"Created {len(entity_keys)} entities for sequential deletion")

        # Verify all entities exist
        for entity_key in entity_keys:
            assert arkiv_client_http.arkiv.entity_exists(entity_key), (
                f"Entity {entity_key} should exist before deletion"
            )

        # Delete entities one by one
        for i, entity_key in enumerate(entity_keys):
            receipt = arkiv_client_http.arkiv.delete_entity(entity_key)
            check_tx_hash(f"delete_entity_{i}", receipt)
            logger.info(f"Deleted entity {i + 1}/{len(entity_keys)}: {entity_key}")

            # Verify this entity is deleted
            assert not arkiv_client_http.arkiv.entity_exists(
                entity_key, at_block=receipt.block_number
            ), f"Entity {entity_key} should not exist after deletion"

        # Verify all entities are gone
        for entity_key in entity_keys:
            assert not arkiv_client_http.arkiv.entity_exists(entity_key), (
                f"Entity {entity_key} should still be deleted"
            )

        logger.info("Sequential deletion of multiple entities successful")

    def test_delete_entity_execute_bulk(self, arkiv_client_http: Arkiv) -> None:
        """Test deleting entities that were created in bulk."""
        # Create entities in bulk
        create_ops = [
            CreateOp(
                payload=f"Bulk entity {i}".encode(),
                content_type="text/plain",
                attributes=Attributes({"batch": "bulk", "index": i}),
                btl=100,
            )
            for i in range(3)
        ]

        entity_keys = bulk_create_entities(
            arkiv_client_http, create_ops, label="bulk_delete_test"
        )

        logger.info(f"Created {len(entity_keys)} entities in bulk")

        # Verify all exist
        for entity_key in entity_keys:
            assert arkiv_client_http.arkiv.entity_exists(entity_key), (
                "Bulk-created entity should exist"
            )

        # Bulk delete
        # Wrap in Operations container and execute
        delete_ops = [DeleteOp(key=key) for key in entity_keys]
        operations = Operations(deletes=delete_ops)
        receipt = arkiv_client_http.arkiv.execute(operations)

        # Check transaction hash of bulk delete
        check_tx_hash("delete_bulk_entity", receipt)

        # Verify all deletes succeeded
        if len(receipt.deletes) != len(delete_ops):
            raise RuntimeError(
                f"Expected {len(delete_ops)} deletes in receipt, got {len(receipt.deletes)}"
            )

        # Verify all are deleted
        for entity_key in entity_keys:
            assert not arkiv_client_http.arkiv.entity_exists(entity_key), (
                "Bulk-created entity should be deleted"
            )

        logger.info("Deletion of bulk-created entities successful")

    def test_delete_nonexistent_entity_behavior(self, arkiv_client_http: Arkiv) -> None:
        """Test that deleting a non-existent entity raises an exception."""
        from eth_typing import HexStr
        from web3.exceptions import Web3RPCError

        from arkiv.types import EntityKey

        # Create a fake entity key (should not exist)
        fake_entity_key = EntityKey(
            HexStr("0x0000000000000000000000000000000000000000000000000000000000000001")
        )

        # Verify it doesn't exist
        assert not arkiv_client_http.arkiv.entity_exists(fake_entity_key), (
            "Fake entity should not exist"
        )

        # Attempt to delete should raise a Web3RPCError
        with pytest.raises(Web3RPCError) as exc_info:
            logger.info(
                f"Attempting to delete non-existent entity {fake_entity_key} -> {exc_info}"
            )
            arkiv_client_http.arkiv.delete_entity(fake_entity_key)

        # Verify the error message indicates entity not found
        error_message = str(exc_info.value)
        assert "entity" in error_message.lower(), "Error message should mention entity"
        assert "not found" in error_message.lower(), (
            "Error message should indicate entity not found"
        )

        logger.info(
            f"Delete of non-existent entity correctly raised {type(exc_info.value).__name__}"
        )

    def test_delete_entity_twice(self, arkiv_client_http: Arkiv) -> None:
        """Test that deleting the same entity twice raises an exception."""
        from web3.exceptions import Web3RPCError

        # Create an entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"Entity to delete twice", btl=100
        )

        # First deletion
        delete_tx_hash_1 = arkiv_client_http.arkiv.delete_entity(entity_key)
        check_tx_hash("first_delete", delete_tx_hash_1)

        # Verify it's deleted
        assert not arkiv_client_http.arkiv.entity_exists(entity_key), (
            "Entity should be deleted after first deletion"
        )

        # Second deletion attempt should raise a Web3RPCError
        with pytest.raises(Web3RPCError) as exc_info:
            arkiv_client_http.arkiv.delete_entity(entity_key)

        # Verify the error message indicates entity not found
        error_message = str(exc_info.value)
        assert "entity" in error_message.lower(), "Error message should mention entity"
        assert "not found" in error_message.lower(), (
            "Error message should indicate entity not found"
        )

        logger.info(
            f"Second delete of same entity correctly raised {type(exc_info.value).__name__}"
        )
