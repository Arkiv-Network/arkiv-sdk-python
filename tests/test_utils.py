"""Tests for utility functions in arkiv.utils module."""

import pytest
from eth_typing import HexStr
from web3 import Web3
from web3.types import Nonce, TxParams, Wei

from arkiv.contract import STORAGE_ADDRESS
from arkiv.exceptions import EntityKeyException
from arkiv.types import (
    Annotation,
    CreateOp,
    DeleteOp,
    EntityKey,
    ExtendOp,
    Operations,
    UpdateOp,
)
from arkiv.utils import (
    check_entity_key,
    entity_key_to_bytes,
    rlp_encode_transaction,
    split_annotations,
    to_create_operation,
    to_entity_key,
    to_tx_params,
)


class TestSplitAnnotations:
    """Test cases for split_annotations function."""

    def test_split_annotations_empty(self) -> None:
        """Test split_annotations with None input."""
        string_annotations, numeric_annotations = split_annotations(None)

        assert string_annotations == []
        assert numeric_annotations == []

    def test_split_annotations_empty_dict(self) -> None:
        """Test split_annotations with empty dict."""
        string_annotations, numeric_annotations = split_annotations({})

        assert string_annotations == []
        assert numeric_annotations == []

    def test_split_annotations_only_strings(self) -> None:
        """Test split_annotations with only string values."""
        annotations: dict[str, str | int] = {
            "name": "test",
            "description": "hello world",
        }
        string_annotations, numeric_annotations = split_annotations(annotations)

        assert len(string_annotations) == 2
        assert len(numeric_annotations) == 0

        # Check string annotations
        assert string_annotations[0].key == "name"
        assert string_annotations[0].value == "test"
        assert string_annotations[1].key == "description"
        assert string_annotations[1].value == "hello world"

    def test_split_annotations_only_integers(self) -> None:
        """Test split_annotations with only integer values."""
        annotations: dict[str, str | int] = {"priority": 1, "version": 42}
        string_annotations, numeric_annotations = split_annotations(annotations)

        assert len(string_annotations) == 0
        assert len(numeric_annotations) == 2

        # Check numeric annotations
        assert numeric_annotations[0].key == "priority"
        assert numeric_annotations[0].value == 1
        assert numeric_annotations[1].key == "version"
        assert numeric_annotations[1].value == 42

    def test_split_annotations_mixed(self) -> None:
        """Test split_annotations with mixed string and integer values."""
        annotations: dict[str, str | int] = {
            "name": "test entity",
            "priority": 5,
            "category": "experimental",
            "count": 100,
        }
        string_annotations, numeric_annotations = split_annotations(annotations)

        assert len(string_annotations) == 2
        assert len(numeric_annotations) == 2

        # Check all annotations are present (order may vary due to dict)
        string_keys = {a.key for a in string_annotations}
        numeric_keys = {a.key for a in numeric_annotations}

        assert string_keys == {"name", "category"}
        assert numeric_keys == {"priority", "count"}

    def test_split_annotations_validates_zero(self) -> None:
        """Test that split_annotations validates zero integers."""
        annotations: dict[str, str | int] = {"zeroIsValid": 0}

        string_annotations, numeric_annotations = split_annotations(annotations)
        assert string_annotations == []
        assert len(numeric_annotations) == 1
        assert numeric_annotations[0].key == "zeroIsValid"
        assert numeric_annotations[0].value == 0

    def test_split_annotations_validates_non_negative_integers(self) -> None:
        """Test that split_annotations validates non-negative integers."""
        annotations: dict[str, str | int] = {"invalid": -1}

        with pytest.raises(
            ValueError, match="Integer annotation values must be non-negative"
        ):
            split_annotations(annotations)


class TestToCreateOperation:
    """Test cases for to_create_operation function."""

    def test_to_create_operation_minimal(self) -> None:
        """Test to_create_operation with minimal parameters."""
        create_op = to_create_operation()

        assert create_op.data == b""
        assert create_op.btl == 0
        assert create_op.string_annotations == []
        assert create_op.numeric_annotations == []

    def test_to_create_operation_with_payload(self) -> None:
        """Test to_create_operation with payload."""
        payload = b"Hello, Arkiv!"
        create_op = to_create_operation(payload=payload)

        assert create_op.data == payload
        assert create_op.btl == 0
        assert create_op.string_annotations == []
        assert create_op.numeric_annotations == []

    def test_to_create_operation_with_btl(self) -> None:
        """Test to_create_operation with custom BTL."""
        btl = 1000
        create_op = to_create_operation(btl=btl)

        assert create_op.data == b""
        assert create_op.btl == btl
        assert create_op.string_annotations == []
        assert create_op.numeric_annotations == []

    def test_to_create_operation_with_annotations(self) -> None:
        """Test to_create_operation with annotations."""
        annotations: dict[str, str | int] = {"name": "test", "priority": 5}
        create_op = to_create_operation(annotations=annotations)

        assert create_op.data == b""
        assert create_op.btl == 0
        assert len(create_op.string_annotations) == 1
        assert len(create_op.numeric_annotations) == 1

        assert create_op.string_annotations[0].key == "name"
        assert create_op.string_annotations[0].value == "test"
        assert create_op.numeric_annotations[0].key == "priority"
        assert create_op.numeric_annotations[0].value == 5

    def test_to_create_operation_complete(self) -> None:
        """Test to_create_operation with all parameters."""
        payload = b"Complete test data"
        annotations: dict[str, str | int] = {
            "name": "complete test",
            "priority": 10,
            "category": "testing",
            "version": 2,
        }
        btl = 5000

        create_op = to_create_operation(
            payload=payload, annotations=annotations, btl=btl
        )

        assert create_op.data == payload
        assert create_op.btl == btl
        assert len(create_op.string_annotations) == 2
        assert len(create_op.numeric_annotations) == 2

    def test_to_create_operation_none_payload_becomes_empty(self) -> None:
        """Test that None payload becomes empty bytes."""
        create_op = to_create_operation(payload=None)

        assert create_op.data == b""

    def test_to_create_operation_empty_payload_stays_empty(self) -> None:
        """Test that empty payload stays empty."""
        create_op = to_create_operation(payload=b"")

        assert create_op.data == b""


class TestToTxParams:
    """Test cases for to_tx_params function."""

    def test_to_tx_params_minimal(self) -> None:
        """Test to_tx_params with minimal operations."""
        create_op = CreateOp(
            data=b"minimal", btl=0, string_annotations=[], numeric_annotations=[]
        )
        operations = Operations(creates=[create_op])

        tx_params = to_tx_params(operations)

        assert tx_params["to"] == STORAGE_ADDRESS
        assert tx_params["value"] == 0
        assert "data" in tx_params
        assert isinstance(tx_params["data"], bytes)

    def test_to_tx_params_with_create_operation(self) -> None:
        """Test to_tx_params with create operation."""
        create_op = CreateOp(
            data=b"test data",
            btl=100,
            string_annotations=[Annotation("name", "test")],
            numeric_annotations=[Annotation("priority", 1)],
        )
        operations = Operations(creates=[create_op])

        tx_params = to_tx_params(operations)

        assert tx_params["to"] == STORAGE_ADDRESS
        assert tx_params["value"] == 0
        assert "data" in tx_params
        assert len(tx_params["data"]) > 0

    def test_to_tx_params_with_additional_params(self) -> None:
        """Test to_tx_params with additional transaction parameters."""
        create_op = CreateOp(
            data=b"test", btl=0, string_annotations=[], numeric_annotations=[]
        )
        operations = Operations(creates=[create_op])
        additional_params: TxParams = {
            "gas": 100000,
            "maxFeePerGas": Web3.to_wei(20, "gwei"),
            "nonce": Nonce(42),
        }

        tx_params = to_tx_params(operations, additional_params)

        # Arkiv-specific fields should be present
        assert tx_params["to"] == STORAGE_ADDRESS
        assert tx_params["value"] == 0
        assert "data" in tx_params

        # Additional params should be preserved
        assert tx_params["gas"] == 100000
        assert tx_params["maxFeePerGas"] == Web3.to_wei(20, "gwei")
        assert tx_params["nonce"] == Nonce(42)

    def test_to_tx_params_overrides_arkiv_fields(self) -> None:
        """Test that to_tx_params overrides 'to', 'value', and 'data' fields."""
        create_op = CreateOp(
            data=b"test", btl=0, string_annotations=[], numeric_annotations=[]
        )
        operations = Operations(creates=[create_op])
        conflicting_params: TxParams = {
            "to": "0x999999999999999999999999999999999999999",
            "value": Wei(1000000),
            "data": b"should be overridden",
            "gas": 50000,
        }

        tx_params = to_tx_params(operations, conflicting_params)

        # Arkiv fields should override user input
        assert tx_params["to"] == STORAGE_ADDRESS
        assert tx_params["value"] == 0
        assert tx_params["data"] != b"should be overridden"

        # Non-conflicting params should be preserved
        assert tx_params["gas"] == 50000

    def test_to_tx_params_none_tx_params(self) -> None:
        """Test to_tx_params with None tx_params."""
        create_op = CreateOp(
            data=b"test", btl=0, string_annotations=[], numeric_annotations=[]
        )
        operations = Operations(creates=[create_op])

        tx_params = to_tx_params(operations, None)

        assert tx_params["to"] == STORAGE_ADDRESS
        assert tx_params["value"] == 0
        assert "data" in tx_params


class TestRlpEncodeTransaction:
    """Test cases for rlp_encode_transaction function."""

    def test_rlp_encode_minimal_operations(self) -> None:
        """Test RLP encoding with minimal operations."""
        create_op = CreateOp(
            data=b"", btl=0, string_annotations=[], numeric_annotations=[]
        )
        operations = Operations(creates=[create_op])

        encoded = rlp_encode_transaction(operations)

        assert isinstance(encoded, bytes)
        assert len(encoded) > 0

    def test_rlp_encode_create_operation(self) -> None:
        """Test RLP encoding with create operation."""
        create_op = CreateOp(
            data=b"test data",
            btl=1000,
            string_annotations=[Annotation("name", "test")],
            numeric_annotations=[Annotation("priority", 5)],
        )
        operations = Operations(creates=[create_op])

        encoded = rlp_encode_transaction(operations)

        assert isinstance(encoded, bytes)
        assert len(encoded) > 0

    def test_rlp_encode_update_operation(self) -> None:
        """Test RLP encoding with update operation."""
        entity_key = EntityKey(
            HexStr("0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
        )
        update_op = UpdateOp(
            entity_key=entity_key,
            data=b"updated data",
            btl=2000,
            string_annotations=[Annotation("status", "updated")],
            numeric_annotations=[Annotation("version", 2)],
        )
        operations = Operations(updates=[update_op])

        encoded = rlp_encode_transaction(operations)

        assert isinstance(encoded, bytes)
        assert len(encoded) > 0

    def test_rlp_encode_delete_operation(self) -> None:
        """Test RLP encoding with delete operation."""
        entity_key = EntityKey(
            HexStr("0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890")
        )
        delete_op = DeleteOp(entity_key=entity_key)
        operations = Operations(deletes=[delete_op])

        encoded = rlp_encode_transaction(operations)

        assert isinstance(encoded, bytes)
        assert len(encoded) > 0

    def test_rlp_encode_extend_operation(self) -> None:
        """Test RLP encoding with extend operation."""
        entity_key = EntityKey(
            HexStr("0xfedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321")
        )
        extend_op = ExtendOp(entity_key=entity_key, number_of_blocks=500)
        operations = Operations(extensions=[extend_op])

        encoded = rlp_encode_transaction(operations)

        assert isinstance(encoded, bytes)
        assert len(encoded) > 0

    def test_rlp_encode_mixed_operations(self) -> None:
        """Test RLP encoding with mixed operations."""
        create_op = CreateOp(
            data=b"create data",
            btl=1000,
            string_annotations=[Annotation("type", "mixed_test")],
            numeric_annotations=[Annotation("batch", 1)],
        )

        entity_key_obj = EntityKey(
            HexStr("0x1111111111111111111111111111111111111111111111111111111111111111")
        )
        update_op = UpdateOp(
            entity_key=entity_key_obj,
            data=b"update data",
            btl=1500,
            string_annotations=[Annotation("status", "modified")],
            numeric_annotations=[Annotation("revision", 3)],
        )

        delete_op = DeleteOp(entity_key=entity_key_obj)
        extend_op = ExtendOp(entity_key=entity_key_obj, number_of_blocks=1000)

        operations = Operations(
            creates=[create_op],
            updates=[update_op],
            deletes=[delete_op],
            extensions=[extend_op],
        )

        encoded = rlp_encode_transaction(operations)

        assert isinstance(encoded, bytes)
        assert len(encoded) > 0

    def test_rlp_encode_multiple_creates(self) -> None:
        """Test RLP encoding with multiple create operations."""
        create_op1 = CreateOp(
            data=b"first entity",
            btl=1000,
            string_annotations=[Annotation("name", "first")],
            numeric_annotations=[Annotation("id", 1)],
        )

        create_op2 = CreateOp(
            data=b"second entity",
            btl=2000,
            string_annotations=[Annotation("name", "second")],
            numeric_annotations=[Annotation("id", 2)],
        )

        operations = Operations(creates=[create_op1, create_op2])

        encoded = rlp_encode_transaction(operations)

        assert isinstance(encoded, bytes)
        assert len(encoded) > 0

    def test_rlp_encode_no_annotations(self) -> None:
        """Test RLP encoding with operations that have no annotations."""
        create_op = CreateOp(
            data=b"no annotations",
            btl=500,
            string_annotations=[],
            numeric_annotations=[],
        )
        operations = Operations(creates=[create_op])

        encoded = rlp_encode_transaction(operations)

        assert isinstance(encoded, bytes)
        assert len(encoded) > 0


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
