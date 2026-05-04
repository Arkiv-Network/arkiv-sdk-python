"""Tests for entity creation functionality in ArkivModule."""

import logging

import pytest
from web3.exceptions import Web3RPCError

from arkiv.client import Arkiv
from arkiv.types import (
    Attributes,
    QueryOptions,
)
from arkiv.utils import (
    check_entity_key,
)

from .utils import check_tx_hash, get_custom_attributes

logger = logging.getLogger(__name__)

TX_SUCCESS = 1


class TestEntityCreate:
    """Test cases for create_entity function."""

    def test_create_entity_simple(self, arkiv_client_http: Arkiv) -> None:
        """Test create_entity."""
        pl: bytes = b"Hello world!"
        content_type = "text/plain"
        ann: Attributes = Attributes({"type": "Greeting", "version": 1})
        expires_in: int = 60

        entity_key, tx_receipt = arkiv_client_http.arkiv.create_entity(
            payload=pl, content_type=content_type, attributes=ann, expires_in=expires_in
        )

        label = "create_entity (a)"
        check_entity_key(entity_key, label)
        check_tx_hash(label, tx_receipt)
        assert tx_receipt.block_number > 0, f"{label}: Block number should be positive"

        query_result = arkiv_client_http.arkiv.query_entities_page(
            f"$key = {entity_key}",
            QueryOptions(at_block=tx_receipt.block_number),
        )
        assert len(query_result.entities) == 1, (
            f"{label}: Should return exactly one entity"
        )
        entity = query_result.entities[0]
        # logger.info(f"{label}: Retrieved entity:\n{entity}")

        assert entity.key == entity_key, f"{label}: Entity key should match"
        assert entity.payload == pl, f"{label}: Entity payload should match"
        assert get_custom_attributes(entity) == ann, (
            f"{label}: Entity attributes should match"
        )
        assert entity.owner == arkiv_client_http.eth.default_account, (
            f"{label}: Entity owner should match transaction sender"
        )
        assert entity.expires_at_block is not None, (
            f"{label}: Entity should have an expiration block"
        )
        assert entity.expires_at_block > 0, (
            f"{label}: Entity expiration block should be in the future"
        )
        logger.info(f"{label}: Entity creation and retrieval successful")

    def test_create_entity_payload_only(self, arkiv_client_http: Arkiv) -> None:
        """Test create_entity with only payload, no attributes."""
        pl: bytes = b"Hello world without attributes!"
        content_type = "text/plain"
        expires_in: int = 60

        entity_key, tx_receipt = arkiv_client_http.arkiv.create_entity(
            payload=pl,
            content_type=content_type,
            attributes=None,
            expires_in=expires_in,
        )

        label = "test_create_entity_payload_only"
        check_entity_key(entity_key, label)
        check_tx_hash(label, tx_receipt)
        assert tx_receipt.block_number > 0, f"{label}: Block number should be positive"

        query_result = arkiv_client_http.arkiv.query_entities_page(
            f"$key = {entity_key}", QueryOptions(at_block=tx_receipt.block_number)
        )
        assert len(query_result.entities) == 1, (
            f"{label}: Should return exactly one entity"
        )
        entity = query_result.entities[0]

        assert entity.key == entity_key, f"{label}: Entity key should match"
        assert entity.payload == pl, f"{label}: Entity payload should match"
        assert entity.attributes == {}, f"{label}: Entity attributes should be empty"
        assert entity.owner == arkiv_client_http.eth.default_account, (
            f"{label}: Entity owner should match transaction sender"
        )
        assert entity.expires_at_block is not None, (
            f"{label}: Entity should have an expiration block"
        )
        assert entity.expires_at_block > 0, (
            f"{label}: Entity expiration block should be in the future"
        )
        logger.info(f"{label}: Entity creation and retrieval successful")

    def test_create_entity_attributes_only(self, arkiv_client_http: Arkiv) -> None:
        """Test create_entity."""
        pl: bytes | None = b""
        content_type = "text/plain"
        ann: Attributes = Attributes({"type": "Greeting", "version": 1})
        expires_in: int = 60

        entity_key, tx_receipt = arkiv_client_http.arkiv.create_entity(
            payload=pl, content_type=content_type, attributes=ann, expires_in=expires_in
        )

        label = "test_create_entity_attributes_only"
        check_entity_key(entity_key, label)
        check_tx_hash(label, tx_receipt)
        assert tx_receipt.block_number > 0, f"{label}: Block number should be positive"

        query_result = arkiv_client_http.arkiv.query_entities_page(
            f"$key = {entity_key}", QueryOptions(at_block=tx_receipt.block_number)
        )
        assert len(query_result.entities) == 1, (
            f"{label}: Should return exactly one entity"
        )
        entity = query_result.entities[0]
        # logger.info(f"{label}: Retrieved entity:\n{entity}")

        assert entity.key == entity_key, f"{label}: Entity key should match"
        assert entity.payload == pl, f"{label}: Entity payload should match"
        assert get_custom_attributes(entity) == ann, (
            f"{label}: Entity attributes should match"
        )
        assert entity.owner == arkiv_client_http.eth.default_account, (
            f"{label}: Entity owner should match transaction sender"
        )
        assert entity.expires_at_block is not None, (
            f"{label}: Entity should have an expiration block"
        )
        assert entity.expires_at_block > 0, (
            f"{label}: Entity expiration block should be in the future"
        )
        logger.info(f"{label}: Entity creation and retrieval successful")


class TestEntityCreateValidation:
    """Test cases for entity creation validation and error handling."""

    def test_create_entity_without_account(self, provider) -> None:
        """Test that create_entity raises error when no account is configured."""
        # Create client without an account
        client = Arkiv(provider)

        with pytest.raises(ValueError, match="No account configured"):
            client.arkiv.create_entity(payload=b"test", expires_in=1000)

    def test_create_entity_with_zero_balance_account(
        self, provider, unfunded_account
    ) -> None:
        """Test that create_entity raises error when account has zero balance."""
        # Create client with unfunded account (zero balance)
        client = Arkiv(provider, account=unfunded_account)

        with pytest.raises(Web3RPCError, match="insufficient funds"):
            client.arkiv.create_entity(payload=b"test", expires_in=1000)
