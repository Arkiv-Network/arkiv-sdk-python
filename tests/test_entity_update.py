"""Tests for entity update functionality in ArkivModule."""

import logging
from dataclasses import replace

import pytest
from eth_typing import HexStr
from web3.exceptions import Web3RPCError

from arkiv.client import Arkiv
from arkiv.types import (
    Annotations,
    CreateOp,
    Operations,
    UpdateOp,
)

from .utils import bulk_create_entities, check_entity, check_tx_hash

logger = logging.getLogger(__name__)


class TestEntityUpdate:
    """Test cases for update_entity function."""

    def test_update_entity_payload(self, arkiv_client_http: Arkiv) -> None:
        """Test updating an entity's payload."""
        # Create an entity to update
        original_payload = b"Original payload"
        annotations: Annotations = Annotations({"type": "test", "purpose": "update"})
        btl = 100

        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=original_payload, annotations=annotations, btl=btl
        )

        logger.info(f"Created entity {entity_key} for update test")

        # Verify original payload
        entity_before = arkiv_client_http.arkiv.get_entity(entity_key)
        assert entity_before.payload == original_payload, (
            "Original payload should match"
        )

        # Update the entity with new payload
        new_payload = b"Updated payload"
        update_tx_hash = arkiv_client_http.arkiv.update_entity(
            entity_key, payload=new_payload, annotations=annotations, btl=btl
        )

        label = "update_entity_payload"
        check_tx_hash(label, update_tx_hash)
        logger.info(f"{label}: Updated entity {entity_key}, tx_hash: {update_tx_hash}")

        # Verify the entity has the new payload
        expected = replace(entity_before, payload=new_payload)
        check_entity(label, arkiv_client_http, expected)

        logger.info(f"{label}: Entity payload update successful")

    def test_update_entity_annotations(self, arkiv_client_http: Arkiv) -> None:
        """Test updating an entity's annotations."""
        # Create an entity
        payload = b"Test payload"
        original_annotations = Annotations({"status": "draft", "version": 1})
        btl = 100

        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=payload, annotations=original_annotations, btl=btl
        )

        logger.info(f"Created entity {entity_key} with original annotations")

        # Verify original annotations
        entity_before = arkiv_client_http.arkiv.get_entity(entity_key)
        assert entity_before.annotations == original_annotations, (
            "Original annotations should match"
        )

        # Update with new annotations
        new_annotations = Annotations({"status": "published", "version": 2})
        update_tx_hash = arkiv_client_http.arkiv.update_entity(
            entity_key, payload=payload, annotations=new_annotations, btl=btl
        )

        label = "update_annotations"
        check_tx_hash(label, update_tx_hash)

        # Verify annotations were updated
        expected = replace(entity_before, annotations=new_annotations)
        check_entity(label, arkiv_client_http, expected)

        logger.info("Entity annotations update successful")

    def test_update_entity_multiple_times(self, arkiv_client_http: Arkiv) -> None:
        """Test updating the same entity multiple times."""
        # Create an entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"Version 0", btl=100
        )

        # Verify original entity
        entity_before = arkiv_client_http.arkiv.get_entity(entity_key)
        assert entity_before.payload == b"Version 0", "Original payload should match"
        assert entity_before.annotations == {}, "Original annotations should be {}"

        # Update multiple times
        versions = [b"Version 1", b"Version 2", b"Version 3"]
        for i, version_payload in enumerate(versions):
            update_tx_hash = arkiv_client_http.arkiv.update_entity(
                entity_key, payload=version_payload, btl=100
            )
            label = f"update_{i}"
            check_tx_hash(label, update_tx_hash)
            logger.info(f"Update {i + 1}: set payload to {version_payload!r}")

            # Verify the update
            expected = replace(entity_before, payload=version_payload)
            check_entity(label, arkiv_client_http, expected)

        logger.info("Multiple updates successful")

    def test_update_entity_execute_bulk(self, arkiv_client_http: Arkiv) -> None:
        """Test updating multiple entities in a single transaction."""
        # Create entities using bulk transaction
        create_ops = [
            CreateOp(
                payload=f"Original entity {i}".encode(),
                content_type="text/plain",
                annotations=Annotations({"batch": "bulk", "index": i}),
                btl=100,
            )
            for i in range(3)
        ]

        for i in range(3):
            logger.info(f"crt op[{i}]: {create_ops[i]}")

        # Use helper function for bulk creation
        entity_keys = bulk_create_entities(
            arkiv_client_http, create_ops, "create_bulk_for_update"
        )

        logger.info(f"Created {len(entity_keys)} entities for bulk update")

        # Verify original payloads
        entities_before = []
        for i, entity_key in enumerate(entity_keys):
            entities_before.append(arkiv_client_http.arkiv.get_entity(entity_key))
            assert entities_before[-1].payload == f"Original entity {i}".encode(), (
                "Original payload should match"
            )

        # Bulk update
        update_ops = [
            UpdateOp(
                entity_key=key,
                payload=f"Updated entity {i}".encode(),
                content_type="text/plain",
                annotations=Annotations({"batch": "bulk", "index": i, "updated": True}),
                btl=150,
            )
            for i, key in enumerate(entity_keys)
        ]

        for i in range(len(update_ops)):
            logger.info(f"upd op[{i}]: {update_ops[i]}")

        receipt = arkiv_client_http.arkiv.execute(Operations(updates=update_ops))

        # Check transaction hash of bulk update
        check_tx_hash("update_bulk_entity", receipt.tx_hash)

        # Verify all updates succeeded
        if len(receipt.updates) != len(update_ops):
            raise RuntimeError(
                f"Expected {len(update_ops)} updates in receipt, got {len(receipt.updates)}"
            )

        # Verify all payloads and annotations were updated
        for i in range(len(entity_keys)):
            expected = replace(
                entities_before[i],
                payload=f"Updated entity {i}".encode(),
                annotations=Annotations({"batch": "bulk", "index": i, "updated": True}),
            )
            check_entity(f"bulk_update_{i}", arkiv_client_http, expected)

        logger.info("Bulk update of entities successful")

    def test_update_entity_to_empty_payload(self, arkiv_client_http: Arkiv) -> None:
        """Test updating an entity with an empty payload."""
        # Create an entity with some payload
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"Non-empty payload", content_type="text/plain", btl=100
        )
        entity_before = arkiv_client_http.arkiv.get_entity(entity_key)

        # Update with empty payload
        update_tx_hash = arkiv_client_http.arkiv.update_entity(
            entity_key, payload=b"", btl=100
        )
        label = "update_to_empty_payload"
        check_tx_hash(label, update_tx_hash)

        # Verify the entity now has empty payload
        expected = replace(entity_before, payload=b"")
        check_entity(label, arkiv_client_http, expected)

    def test_update_entity_from_empty_payload(self, arkiv_client_http: Arkiv) -> None:
        """Test updating an entity with an empty payload."""
        # Create an entity with some payload
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"", content_type="text/plain", btl=100
        )
        entity_before = arkiv_client_http.arkiv.get_entity(entity_key)

        # Update with empty payload
        non_empty_payload = b"Non-empty payload"
        update_tx_hash = arkiv_client_http.arkiv.update_entity(
            entity_key, payload=non_empty_payload, btl=100
        )
        label = "update_empty_payload"
        check_tx_hash(label, update_tx_hash)

        # Verify the entity now has new payload
        expected = replace(entity_before, payload=non_empty_payload)
        check_entity(label, arkiv_client_http, expected)

        logger.info("Update from empty payload successful")

    def test_update_nonexistent_entity_behavior(self, arkiv_client_http: Arkiv) -> None:
        """Test that updating a non-existent entity raises an exception."""
        from arkiv.types import EntityKey

        # Create a fake entity key (should not exist)
        fake_entity_key = EntityKey(
            HexStr("0x0000000000000000000000000000000000000000000000000000000000000001")
        )

        # Verify it doesn't exist
        assert not arkiv_client_http.arkiv.entity_exists(fake_entity_key), (
            "Fake entity should not exist"
        )

        # Attempt to update should raise a Web3RPCError
        with pytest.raises(Web3RPCError) as exc_info:
            arkiv_client_http.arkiv.update_entity(
                fake_entity_key, payload=b"New payload", btl=100
            )

        # Verify the error message indicates entity not found
        error_message = str(exc_info.value)
        assert (
            "entity" in error_message.lower() or "not found" in error_message.lower()
        ), "Error message should mention entity or not found"

        logger.info(
            f"Update of non-existent entity correctly raised {type(exc_info.value).__name__}"
        )

    def test_update_deleted_entity_behavior(self, arkiv_client_http: Arkiv) -> None:
        """Test that updating a deleted entity raises an exception."""
        # Create an entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"Entity to delete then update", btl=100
        )

        # Delete the entity
        delete_tx_hash = arkiv_client_http.arkiv.delete_entity(entity_key)
        check_tx_hash("delete_before_update", delete_tx_hash)

        # Verify it's deleted
        assert not arkiv_client_http.arkiv.entity_exists(entity_key), (
            "Entity should be deleted"
        )

        # Attempt to update should raise a Web3RPCError
        with pytest.raises(Web3RPCError) as exc_info:
            arkiv_client_http.arkiv.update_entity(
                entity_key, payload=b"Updated payload", btl=100
            )

        # Verify the error message indicates entity not found
        error_message = str(exc_info.value)
        assert (
            "entity" in error_message.lower() or "not found" in error_message.lower()
        ), "Error message should mention entity or not found"

        logger.info(
            f"Update of deleted entity correctly raised {type(exc_info.value).__name__}"
        )

    # TODO figure out what the idea behind btl extension was
    def test_update_entity_btl_extension(self, arkiv_client_http: Arkiv) -> None:
        """Test that updating an entity with a higher btl extends its lifetime."""
        # Create an entity with initial btl
        payload = b"Test payload"
        content_type = "text/plain"
        initial_btl = 100
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=payload, content_type=content_type, btl=initial_btl
        )

        # Get initial expiration
        entity_before = arkiv_client_http.arkiv.get_entity(entity_key)
        initial_expiration = entity_before.expires_at_block
        assert initial_expiration is not None, "Entity should have expiration block"
        logger.info(f"Initial expiration block: {initial_expiration}")

        # Update with higher btl
        new_btl = 200
        update_tx_hash = arkiv_client_http.arkiv.update_entity(
            entity_key, payload=payload, content_type=content_type, btl=new_btl
        )
        check_tx_hash("update_btl", update_tx_hash)

        # Verify new expiration (btl extension calculation)
        assert entity_before.expires_at_block is not None
        expected = replace(
            entity_before,
            expires_at_block=entity_before.expires_at_block - initial_btl + new_btl,
        )
        check_entity("update_btl", arkiv_client_http, expected)

        # Verify expiration was extended (should be roughly initial + new_btl)
        # Note: exact value depends on block advancement during the update
        assert expected.expires_at_block is not None
        assert expected.expires_at_block > initial_expiration, (
            "Expiration should increase with higher btl"
        )

        logger.info(
            f"BTL extension successful: {initial_expiration} -> {expected.expires_at_block}"
        )

    def test_update_entity_both_payload_and_annotations(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test updating both payload and annotations simultaneously."""
        # Create an entity
        original_payload = b"Original data"
        original_annotations = Annotations({"version": 1, "status": "initial"})
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=original_payload, annotations=original_annotations, btl=100
        )

        # Get original entity
        entity_before = arkiv_client_http.arkiv.get_entity(entity_key)

        # Update both payload and annotations
        new_payload = b"New data"
        new_annotations = Annotations({"version": 2, "status": "updated"})
        update_tx_hash = arkiv_client_http.arkiv.update_entity(
            entity_key, payload=new_payload, annotations=new_annotations, btl=100
        )
        label = "update_both"
        check_tx_hash(label, update_tx_hash)

        # Verify both were updated
        expected = replace(
            entity_before, payload=new_payload, annotations=new_annotations
        )
        check_entity(label, arkiv_client_http, expected)

        logger.info("Simultaneous payload and annotations update successful")
