"""Tests for entity extension functionality in ArkivModule."""

import logging

import pytest
from eth_typing import HexStr
from web3.exceptions import Web3RPCError

from arkiv.client import Arkiv
from arkiv.types import Attributes, CreateOp, ExtendOp, Operations

from .utils import bulk_create_entities, check_tx_hash

logger = logging.getLogger(__name__)


class TestEntityExtend:
    """Test cases for extend_entity function."""

    def test_extend_entity_simple(self, arkiv_client_http: Arkiv) -> None:
        """Test extending a single entity's lifetime."""
        # Create an entity to extend
        payload = b"Test entity for extension"
        content_type = "text/plain"
        attributes: Attributes = Attributes({"type": "test", "purpose": "extension"})
        btl = 100

        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=payload, content_type=content_type, attributes=attributes, btl=btl
        )

        logger.info(f"Created entity {entity_key} for extension test")

        # Get initial expiration block
        entity_before = arkiv_client_http.arkiv.get_entity(entity_key)
        logger.info(f"Entity before extension: {entity_before}")
        initial_expiration = entity_before.expires_at_block
        assert initial_expiration is not None, "Entity should have expiration block"
        logger.info(f"Initial expiration block: {initial_expiration}")

        # Extend the entity by 50 blocks
        number_of_blocks = 50
        extend_tx_hash = arkiv_client_http.arkiv.extend_entity(
            entity_key, number_of_blocks
        )

        label = "extend_entity"
        check_tx_hash(label, extend_tx_hash)
        logger.info(
            f"{label}: Extended entity {entity_key} by {number_of_blocks} blocks, tx_hash: {extend_tx_hash}"
        )

        # Verify the entity still exists and expiration increased
        entity_after = arkiv_client_http.arkiv.get_entity(entity_key)
        logger.info(f"Entity after extension: {entity_after}")
        assert entity_after.expires_at_block == initial_expiration + number_of_blocks, (
            f"Expiration should increase by {number_of_blocks} blocks"
        )

        logger.info(
            f"{label}: Entity expiration increased from {initial_expiration} to {entity_after.expires_at_block}"
        )

    def test_extend_entity_multiple_times(self, arkiv_client_http: Arkiv) -> None:
        """Test extending the same entity multiple times."""
        # Create an entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"Entity for multiple extensions", btl=100
        )

        # Get initial expiration
        entity = arkiv_client_http.arkiv.get_entity(entity_key)
        initial_expiration = entity.expires_at_block
        assert initial_expiration is not None, "Entity should have expiration block"

        # Extend multiple times
        extensions = [20, 30, 50]
        for i, blocks in enumerate(extensions):
            extend_tx_hash = arkiv_client_http.arkiv.extend_entity(entity_key, blocks)
            check_tx_hash(f"extend_{i}", extend_tx_hash)
            logger.info(f"Extension {i + 1}: extended by {blocks} blocks")

        # Verify final expiration
        entity_final = arkiv_client_http.arkiv.get_entity(entity_key)
        expected_expiration = initial_expiration + sum(extensions)
        assert entity_final.expires_at_block == expected_expiration, (
            f"Expiration should be {expected_expiration}"
        )

        logger.info(
            f"Multiple extensions successful: {initial_expiration} -> {entity_final.expires_at_block}"
        )

    def test_extend_entity_execute_bulk(self, arkiv_client_http: Arkiv) -> None:
        """Test extending multiple entities in a single transaction."""
        # Create entities using bulk transaction
        create_ops = [
            CreateOp(
                payload=f"Bulk entity {i}".encode(),
                content_type="text/plain",
                attributes=Attributes({"batch": "bulk", "index": i}),
                btl=100,
            )
            for i in range(3)
        ]

        # Use helper function for bulk creation
        entity_keys = bulk_create_entities(
            arkiv_client_http, create_ops, "create_bulk_entity"
        )

        # Get initial expirations
        initial_expirations = {}
        for entity_key in entity_keys:
            entity = arkiv_client_http.arkiv.get_entity(entity_key)
            expires_at = entity.expires_at_block
            assert expires_at is not None, "Entity should have expiration block"
            initial_expirations[entity_key] = expires_at

        # Bulk extend
        number_of_blocks = 200
        extend_ops = [
            ExtendOp(key=key, number_of_blocks=number_of_blocks) for key in entity_keys
        ]
        operations = Operations(extensions=extend_ops)
        receipt = arkiv_client_http.arkiv.execute(operations)

        # Check transaction hash of bulk extend
        check_tx_hash("extend_bulk_entity", receipt)

        # Verify all extensions succeeded
        if len(receipt.extensions) != len(extend_ops):
            raise RuntimeError(
                f"Expected {len(extend_ops)} extensions in receipt, got {len(receipt.extensions)}"
            )

        # Verify all expirations increased
        for entity_key in entity_keys:
            entity = arkiv_client_http.arkiv.get_entity(entity_key)
            expected_expiration = initial_expirations[entity_key] + number_of_blocks
            assert entity.expires_at_block == expected_expiration, (
                f"Entity {entity_key} expiration should be {expected_expiration}"
            )

        logger.info("Bulk extension of entities successful")

    def test_extend_nonexistent_entity_behavior(self, arkiv_client_http: Arkiv) -> None:
        """Test that extending a non-existent entity raises an exception."""
        from arkiv.types import EntityKey

        # Create a fake entity key (should not exist)
        fake_entity_key = EntityKey(
            HexStr("0x0000000000000000000000000000000000000000000000000000000000000001")
        )

        # Verify it doesn't exist
        assert not arkiv_client_http.arkiv.entity_exists(fake_entity_key), (
            "Fake entity should not exist"
        )

        # Attempt to extend should raise a Web3RPCError
        with pytest.raises(Web3RPCError) as exc_info:
            arkiv_client_http.arkiv.extend_entity(fake_entity_key, 100)

        # Verify the error message indicates entity not found
        error_message = str(exc_info.value)
        assert "entity" in error_message.lower(), "Error message should mention entity"
        assert "not found" in error_message.lower(), (
            "Error message should indicate entity not found"
        )

        logger.info(
            f"Extend of non-existent entity correctly raised {type(exc_info.value).__name__}"
        )

    def test_extend_deleted_entity_behavior(self, arkiv_client_http: Arkiv) -> None:
        """Test that extending a deleted entity raises an exception."""
        # Create an entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"Entity to delete then extend", btl=100
        )

        # Delete the entity
        delete_tx_hash = arkiv_client_http.arkiv.delete_entity(entity_key)
        check_tx_hash("delete_before_extend", delete_tx_hash)

        # Verify it's deleted
        assert not arkiv_client_http.arkiv.entity_exists(entity_key), (
            "Entity should be deleted"
        )

        # Attempt to extend should raise a Web3RPCError
        with pytest.raises(Web3RPCError) as exc_info:
            arkiv_client_http.arkiv.extend_entity(entity_key, 100)

        # Verify the error message indicates entity not found
        error_message = str(exc_info.value)
        assert "entity" in error_message.lower(), "Error message should mention entity"
        assert "not found" in error_message.lower(), (
            "Error message should indicate entity not found"
        )

        logger.info(
            f"Extend of deleted entity correctly raised {type(exc_info.value).__name__}"
        )

    def test_extend_entity_minimal_blocks(self, arkiv_client_http: Arkiv) -> None:
        """Test extending an entity by a minimal number of blocks."""
        # Create an entity
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=b"Entity for minimal extension", btl=100
        )

        # Get initial expiration
        entity_before = arkiv_client_http.arkiv.get_entity(entity_key)
        initial_expiration = initial_expiration = entity_before.expires_at_block
        assert initial_expiration is not None, (
            f"Entity should have expiration block, actual entity: {entity_before}"
        )

        # Extend by just 1 block
        extend_tx_hash = arkiv_client_http.arkiv.extend_entity(entity_key, 1)
        check_tx_hash("extend_minimal", extend_tx_hash)

        # Verify expiration increased by 1
        entity_after = arkiv_client_http.arkiv.get_entity(entity_key)
        assert entity_after.expires_at_block == initial_expiration + 1, (
            "Expiration should increase by 1 block"
        )

        logger.info(
            f"Minimal extension successful: {initial_expiration} -> {entity_after.expires_at_block}"
        )
