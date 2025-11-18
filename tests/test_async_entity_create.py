"""Tests for async entity creation functionality in AsyncArkivModule."""

import logging

import pytest
from web3.exceptions import Web3RPCError

from arkiv import AsyncArkiv
from arkiv.types import Attributes

from .utils import check_entity_key, check_tx_hash

logger = logging.getLogger(__name__)


class TestAsyncEntityCreate:
    """Test cases for async create_entity function."""

    @pytest.mark.asyncio
    async def test_async_create_entity_simple(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test creating a simple entity with async client."""
        # Create entity with simple payload
        payload = b"Test async entity"
        entity_key, receipt = await async_arkiv_client_http.arkiv.create_entity(
            payload=payload,
            expires_in=1000,
        )

        # Verify entity_key and tx_hash formats
        check_entity_key("test_async_create_entity_simple", entity_key)
        check_tx_hash("test_async_create_entity_simple", receipt)

        logger.info(f"Created async entity: {entity_key} (tx: {receipt.tx_hash})")

    @pytest.mark.asyncio
    async def test_async_create_entities_multiple(
        self, async_arkiv_client_http: AsyncArkiv
    ) -> None:
        """Test creating multiple entities sequentially with async/await."""
        # Create multiple entities using async/await
        entity_keys = []
        for i in range(3):
            entity_key, receipt = await async_arkiv_client_http.arkiv.create_entity(
                payload=f"Async entity {i}".encode(),
                attributes=Attributes({"index": i}),
                expires_in=1000,
            )

            # Verify individual entity_key and tx_hash formats
            check_entity_key(f"test_async_create_entities_multiple_{i}", entity_key)
            check_tx_hash(f"test_async_create_entities_multiple_{i}", receipt)

            entity_keys.append(entity_key)
            logger.info(f"Created async entity {i + 1}/3: {entity_key}")

        # Verify all succeeded and are unique
        assert len(entity_keys) == 3
        assert len(set(entity_keys)) == 3, "All entity keys should be unique"


class TestAsyncEntityCreateValidation:
    """Test cases for async entity creation validation and error handling."""

    @pytest.mark.asyncio
    async def test_async_create_entity_without_account(self, async_provider) -> None:
        """Test that async create_entity raises error when no account is configured."""
        # Create async client without an account
        async with AsyncArkiv(async_provider) as client:
            with pytest.raises(ValueError, match="No account configured"):
                await client.arkiv.create_entity(payload=b"test", expires_in=1000)

    @pytest.mark.asyncio
    async def test_async_create_entity_with_zero_balance_account(
        self, async_provider, unfunded_account
    ) -> None:
        """Test that async create_entity raises error when account has zero balance."""
        # Create async client with unfunded account (zero balance)
        async with AsyncArkiv(async_provider, account=unfunded_account) as client:
            with pytest.raises(Web3RPCError, match="insufficient funds"):
                await client.arkiv.create_entity(payload=b"test", expires_in=1000)
