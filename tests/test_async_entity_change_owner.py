"""Tests for async entity ownership change functionality in AsyncArkivModule."""

import logging

import pytest

from arkiv.account import NamedAccount
from arkiv.client import AsyncArkiv
from arkiv.types import Attributes

from .utils import check_tx_hash

logger = logging.getLogger(__name__)


class TestAsyncEntityChangeOwner:
    """Test cases for async change_owner function."""

    @pytest.mark.asyncio
    async def test_async_change_owner_simple(
        self, async_arkiv_client_http: AsyncArkiv, account_2: NamedAccount
    ) -> None:
        """Test changing ownership of a single entity asynchronously."""
        # Create an entity as the default account (alice)
        payload = b"Test entity for async ownership transfer"
        attributes: Attributes = Attributes(
            {"type": "test", "purpose": "async_ownership"}
        )
        btl = 100

        entity_key, _ = await async_arkiv_client_http.arkiv.create_entity(
            payload=payload, attributes=attributes, btl=btl
        )

        logger.info(f"Created entity {entity_key} for async ownership test")

        # Verify initial owner
        entity = await async_arkiv_client_http.arkiv.get_entity(entity_key)
        initial_owner = entity.owner
        assert initial_owner == async_arkiv_client_http.eth.default_account, (
            "Initial owner should be the creator"
        )

        # Change ownership to Bob
        new_owner = account_2.address
        change_receipt = await async_arkiv_client_http.arkiv.change_owner(
            entity_key, new_owner
        )

        label = "async_change_owner"
        check_tx_hash(label, change_receipt)
        logger.info(
            f"{label}: Changed owner of entity {entity_key} to {new_owner}, "
            f"tx_hash: {change_receipt.tx_hash}"
        )

        # Verify the new owner
        entity_after = await async_arkiv_client_http.arkiv.get_entity(entity_key)
        assert entity_after.owner == new_owner, (
            f"Owner should be {new_owner} after transfer"
        )
        assert entity_after.owner != initial_owner, (
            "Owner should have changed from initial owner"
        )

        logger.info(f"{label}: Async ownership change successful")

    @pytest.mark.asyncio
    async def test_async_change_owner_and_verify_entity_unchanged(
        self, async_arkiv_client_http: AsyncArkiv, account_2: NamedAccount
    ) -> None:
        """Test that changing ownership doesn't modify entity data asynchronously."""
        # Create an entity
        payload = b"Entity data should remain unchanged in async"
        attributes: Attributes = Attributes({"data": "important", "version": 1})
        btl = 150

        entity_key, _ = await async_arkiv_client_http.arkiv.create_entity(
            payload=payload, attributes=attributes, btl=btl
        )

        # Get entity before ownership change
        entity_before = await async_arkiv_client_http.arkiv.get_entity(entity_key)

        # Change ownership
        new_owner = account_2.address
        change_receipt = await async_arkiv_client_http.arkiv.change_owner(
            entity_key, new_owner
        )
        check_tx_hash("async_change_owner_verify_data", change_receipt)

        # Get entity after ownership change
        entity_after = await async_arkiv_client_http.arkiv.get_entity(entity_key)

        # Verify only owner changed
        assert entity_after.owner == new_owner, "Owner should be updated"
        assert entity_after.payload == entity_before.payload, (
            "Payload should remain unchanged"
        )
        assert entity_after.attributes == entity_before.attributes, (
            "Attributes should remain unchanged"
        )
        assert entity_after.expires_at_block == entity_before.expires_at_block, (
            "Expiration should remain unchanged"
        )
        assert entity_after.key == entity_before.key, (
            "Entity key should remain unchanged"
        )

        logger.info("Async ownership change preserved entity data")

    @pytest.mark.asyncio
    async def test_async_change_owner_multiple_entities(
        self, async_arkiv_client_http: AsyncArkiv, account_2: NamedAccount
    ) -> None:
        """Test changing ownership of multiple entities asynchronously."""
        # Create multiple entities
        entity_keys = []
        for i in range(3):
            payload = f"Entity {i} for async ownership transfer".encode()
            attributes: Attributes = Attributes(
                {"index": i, "batch": "async_ownership"}
            )
            entity_key, _ = await async_arkiv_client_http.arkiv.create_entity(
                payload=payload, attributes=attributes, btl=100
            )
            entity_keys.append(entity_key)

        logger.info(
            f"Created {len(entity_keys)} entities for async multiple ownership transfer"
        )

        # Change ownership of all entities to Bob
        new_owner = account_2.address
        for i, entity_key in enumerate(entity_keys):
            receipt = await async_arkiv_client_http.arkiv.change_owner(
                entity_key, new_owner
            )
            check_tx_hash(f"async_change_owner_{i}", receipt)
            logger.info(
                f"Changed owner {i + 1}/{len(entity_keys)}: {entity_key} -> {new_owner}"
            )

        # Verify all entities have new owner
        for entity_key in entity_keys:
            entity = await async_arkiv_client_http.arkiv.get_entity(entity_key)
            assert entity.owner == new_owner, (
                f"Entity {entity_key} should have new owner {new_owner}"
            )

        logger.info("All entities successfully transferred to new owner asynchronously")

    @pytest.mark.asyncio
    async def test_async_change_owner_to_same_owner(
        self,
        async_arkiv_client_http: AsyncArkiv,
    ) -> None:
        """Test changing ownership to the same owner asynchronously (should succeed as no-op)."""
        # Create an entity
        payload = b"Test entity for async same-owner transfer"
        attributes: Attributes = Attributes({"type": "test"})
        entity_key, _ = await async_arkiv_client_http.arkiv.create_entity(
            payload=payload, attributes=attributes, btl=100
        )

        # Get current owner
        current_owner = async_arkiv_client_http.eth.default_account

        # Change ownership to same owner
        receipt = await async_arkiv_client_http.arkiv.change_owner(
            entity_key, current_owner
        )
        check_tx_hash("async_change_owner_same", receipt)

        # Verify owner is still the same
        entity = await async_arkiv_client_http.arkiv.get_entity(entity_key)
        assert entity.owner == current_owner, "Owner should remain unchanged"

        logger.info("Async same-owner transfer completed successfully")
