"""Tests for entity ownership change functionality in ArkivModule."""

import logging

import pytest
from web3.exceptions import Web3RPCError

from arkiv.account import NamedAccount
from arkiv.client import Arkiv
from arkiv.types import Attributes

from .utils import check_tx_hash

logger = logging.getLogger(__name__)


class TestEntityChangeOwner:
    """Test cases for change_owner function."""

    def test_change_owner_simple(
        self, arkiv_client_http: Arkiv, account_2: NamedAccount
    ) -> None:
        """Test changing ownership of a single entity."""
        # Create an entity
        payload = b"Entity data should remain unchanged"
        attributes: Attributes = Attributes({"data": "important", "version": 1})
        btl = 150

        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=payload, attributes=attributes, btl=btl
        )

        # Get entity before ownership change
        entity_before = arkiv_client_http.arkiv.get_entity(entity_key)

        # Change ownership
        new_owner = account_2.address
        change_receipt = arkiv_client_http.arkiv.change_owner(entity_key, new_owner)
        check_tx_hash("change_owner_verify_data", change_receipt)

        # Get entity after ownership change
        entity_after = arkiv_client_http.arkiv.get_entity(entity_key)

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

        logger.info("Ownership change preserved entity data")

    def test_change_owner_multiple_entities(
        self, arkiv_client_http: Arkiv, account_2: NamedAccount
    ) -> None:
        """Test changing ownership of multiple entities."""
        # Create multiple entities
        entity_keys = []
        for i in range(3):
            payload = f"Entity {i} for ownership transfer".encode()
            attributes: Attributes = Attributes({"index": i, "batch": "ownership"})
            entity_key, _ = arkiv_client_http.arkiv.create_entity(
                payload=payload, attributes=attributes, btl=100
            )
            entity_keys.append(entity_key)

        logger.info(
            f"Created {len(entity_keys)} entities for multiple ownership transfer"
        )

        # Change ownership of all entities to Bob
        new_owner = account_2.address
        for i, entity_key in enumerate(entity_keys):
            receipt = arkiv_client_http.arkiv.change_owner(entity_key, new_owner)
            check_tx_hash(f"change_owner_{i}", receipt)
            logger.info(
                f"Changed owner {i + 1}/{len(entity_keys)}: {entity_key} -> {new_owner}"
            )

        # Verify all entities have new owner
        for entity_key in entity_keys:
            entity = arkiv_client_http.arkiv.get_entity(entity_key)
            assert entity.owner == new_owner, (
                f"Entity {entity_key} should have new owner {new_owner}"
            )

        logger.info("All entities successfully transferred to new owner")

    def test_change_owner_unauthorized(
        self, arkiv_client_http: Arkiv, account_1: NamedAccount, account_2: NamedAccount
    ) -> None:
        """Test that non-owners cannot change entity ownership."""
        # Create an entity as alice (default account)
        payload = b"Test entity for unauthorized transfer"
        attributes: Attributes = Attributes({"type": "test"})
        _entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=payload, attributes=attributes, btl=100
        )

        assert arkiv_client_http.eth.default_account == account_1.address, (
            "Default account should be account 1's address"
        )

        try:
            arkiv_client_http.accounts[account_2.name] = account_2
            arkiv_client_http.switch_to(account_2.name)

            assert arkiv_client_http.eth.default_account == account_2.address, (
                "Current account (after switch_to) should be account 2's address"
            )

            # This should fail as account 2 is not the owner
            # Expected: Web3RPCError or similar exception
            with pytest.raises(Web3RPCError):
                arkiv_client_http.arkiv.change_owner(_entity_key, account_2.address)
        finally:
            # Reset to account_1
            arkiv_client_http.switch_to(account_1.name)

    def test_change_owner_to_same_owner(self, arkiv_client_http: Arkiv) -> None:
        """Test changing ownership to the same owner (should succeed as no-op)."""
        # Create an entity
        payload = b"Test entity for same-owner transfer"
        attributes: Attributes = Attributes({"type": "test"})
        entity_key, _ = arkiv_client_http.arkiv.create_entity(
            payload=payload, attributes=attributes, btl=100
        )

        # Get current owner
        current_owner = arkiv_client_http.eth.default_account

        # Change ownership to same owner
        receipt = arkiv_client_http.arkiv.change_owner(entity_key, current_owner)
        check_tx_hash("change_owner_same", receipt)

        # Verify owner is still the same
        entity = arkiv_client_http.arkiv.get_entity(entity_key)
        assert entity.owner == current_owner, "Owner should remain unchanged"

        logger.info("Same-owner transfer completed successfully")
