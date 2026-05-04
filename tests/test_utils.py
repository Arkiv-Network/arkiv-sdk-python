"""Tests for utility functions in arkiv.utils module."""

import logging

import pytest
from eth_typing import HexStr
from web3 import Web3

from arkiv.exceptions import AttributeException, EntityKeyException
from arkiv.types import (
    ALL,
    MAX_RESULTS_PER_PAGE_DEFAULT,
    Attributes,
    CreateOp,
    EntityKey,
    Operations,
    QueryOptions,
)
from arkiv.utils import (
    check_entity_key,
    entity_key_to_bytes,
    to_entity_key,
    to_rpc_query_options,
)

logger = logging.getLogger(__name__)


class TestToCreateOperation:
    """Test cases for CreateOp constructor."""

    def test_create_op_minimal(self) -> None:
        """Test CreateOp with minimal valid input."""
        op = CreateOp(
            payload=b"",
            content_type="",
            expires_in=0,
            attributes=Attributes({}),
        )
        assert op.payload == b""
        assert op.expires_in == 0
        assert op.attributes == Attributes({})

    def test_create_op_with_attributes(self) -> None:
        """Test CreateOp with attributes."""
        payload = b"sample data"
        expires_in = 100
        attributes: Attributes = Attributes(
            {
                "name": "example",
                "version": 2,
            }
        )

        op = CreateOp(
            payload=payload,
            content_type="",
            expires_in=expires_in,
            attributes=attributes,
        )

        assert op.payload == payload
        assert op.expires_in == expires_in
        assert op.attributes == attributes


class TestEntityKeyUtils:
    """Test cases for entity key utility functions."""

    def test_to_entity_key_from_int(self) -> None:
        """Test to_entity_key with integer value."""
        int_val = 123456789
        key = to_entity_key(int_val)

        assert isinstance(key, str)
        assert key.startswith("0x")
        assert len(key) == 66
        # verify that key converted to int matches original
        int_val_from_key = int(key, 16)
        assert int_val_from_key == int_val

    def test_entity_key_to_bytes(self) -> None:
        """Test entity_key_to_bytes with EntityKey."""
        int_val = 123456789
        key = to_entity_key(int_val)
        b = entity_key_to_bytes(key)

        assert isinstance(b, bytes)
        assert len(b) == 32
        # Should match int to bytes conversion
        assert b == int_val.to_bytes(32, byteorder="big")

    def test_check_entity_key_valid(self) -> None:
        """Test check_entity_key with valid EntityKey."""
        key = to_entity_key(1)
        # Should not raise
        check_entity_key(key)

    def test_check_entity_key_invalid_length(self) -> None:
        """Test check_entity_key with invalid length."""
        with pytest.raises(EntityKeyException):
            check_entity_key(EntityKey(HexStr("0x1234")))

    def test_check_entity_key_invalid_hex(self) -> None:
        """Test check_entity_key with invalid hex characters."""
        # 64 chars but not valid hex
        bad_key = EntityKey(HexStr("0x" + "g" * 64))
        with pytest.raises(EntityKeyException):
            check_entity_key(bad_key)

    def test_check_entity_key_none(self) -> None:
        """Test check_entity_key with None value."""
        with pytest.raises(EntityKeyException):
            check_entity_key(None)

    def test_check_entity_key_not_str(self) -> None:
        """Test check_entity_key with non-string value."""
        with pytest.raises(EntityKeyException):
            check_entity_key(123)


class TestToRpcQueryOptions:
    """Test cases for to_rpc_query_options function."""

    def test_default_options(self) -> None:
        """Test with default QueryOptions."""

        options = QueryOptions()
        rpc_options = to_rpc_query_options(options)

        # Check structure
        assert "includeData" in rpc_options
        assert "resultsPerPage" in rpc_options
        assert rpc_options["atBlock"] is None

        # Check defaults: attributes=ALL means all includeData flags are True
        assert options.attributes == ALL
        include_data = rpc_options["includeData"]
        assert include_data["key"] is True
        assert include_data["attributes"] is True
        assert include_data["payload"] is True
        assert include_data["contentType"] is True
        assert include_data["expiration"] is True
        assert include_data["owner"] is True

        # Check default page size
        assert int(rpc_options["resultsPerPage"], 16) == MAX_RESULTS_PER_PAGE_DEFAULT

        # Check max_results is None (not passed to RPC, handled by iterator)
        assert options.max_results is None

    def test_page_size_explicit(self) -> None:
        """Test explicit max_results_per_page is used."""
        options = QueryOptions(max_results_per_page=50)
        rpc_options = to_rpc_query_options(options)

        max_results_per_page_custom = 50
        assert max_results_per_page_custom != MAX_RESULTS_PER_PAGE_DEFAULT
        assert int(rpc_options["resultsPerPage"], 16) == max_results_per_page_custom

    def test_page_size_capped_by_max_results(self) -> None:
        """Test that page size is capped by max_results when smaller."""
        # max_results < max_results_per_page: should use max_results
        max_results_capped = 5
        max_results_per_page = 100
        assert max_results_capped < max_results_per_page

        options = QueryOptions(
            max_results=max_results_capped, max_results_per_page=max_results_per_page
        )
        rpc_options = to_rpc_query_options(options)

        assert int(rpc_options["resultsPerPage"], 16) == max_results_capped

    def test_page_size_not_affected_when_max_results_larger(self) -> None:
        """Test that page size unchanged when max_results > max_results_per_page."""
        # max_results > max_results_per_page: should use max_results_per_page
        max_results_capped = 200
        max_results_per_page = 100
        assert max_results_capped > max_results_per_page

        options = QueryOptions(
            max_results=max_results_capped, max_results_per_page=max_results_per_page
        )
        rpc_options = to_rpc_query_options(options)

        assert int(rpc_options["resultsPerPage"], 16) == max_results_per_page

    def test_page_size_equal_to_max_results(self) -> None:
        """Test when max_results equals max_results_per_page."""
        max_results_capped = 35
        max_results_per_page = 35
        assert max_results_capped == max_results_per_page

        options = QueryOptions(
            max_results=max_results_capped, max_results_per_page=max_results_per_page
        )
        rpc_options = to_rpc_query_options(options)

        assert int(rpc_options["resultsPerPage"], 16) == max_results_capped

    def test_page_size_with_max_results_none(self) -> None:
        """Test that page size is unchanged when max_results is None."""
        max_results_capped = None
        max_results_per_page = 35

        options = QueryOptions(
            max_results=max_results_capped, max_results_per_page=max_results_per_page
        )
        rpc_options = to_rpc_query_options(options)

        assert int(rpc_options["resultsPerPage"], 16) == max_results_per_page
