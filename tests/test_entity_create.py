"""Tests for entity creation functionality in ArkivModule."""

import logging

from hexbytes import HexBytes
from web3.types import TxReceipt

from arkiv.client import Arkiv
from arkiv.contract import STORAGE_ADDRESS
from arkiv.types import Annotations, CreateOp, Operations, TxHash
from arkiv.utils import check_entity_key, to_receipt, to_tx_params

logger = logging.getLogger(__name__)

TX_SUCCESS = 1


def check_tx_hash(label: str, tx_hash: TxHash) -> None:
    """Check transaction hash validity."""
    logger.info(f"{label}: Checking transaction hash {tx_hash}")
    assert tx_hash is not None, f"{label}: Transaction hash should not be None"
    assert isinstance(tx_hash, str), (
        f"{label}: Transaction hash should be a string (TxHash)"
    )
    assert len(tx_hash) == 66, (
        f"{label}: Transaction hash should be 66 characters long (0x + 64 hex)"
    )
    assert tx_hash.startswith("0x"), f"{label}: Transaction hash should start with 0x"


class TestEntityCreate:
    """Test cases for create_entity function."""

    def test_create_entity_via_web3(self, arkiv_client_http: Arkiv) -> None:
        """Test create_entity with custom payload checking against Web3 client behavior."""
        payload = b"Hello world!"
        annotations: Annotations = Annotations({"type": "Greeting", "version": 1})
        btl = 60  # 60 blocks to live

        # Get the expected sender address from client's default account
        expected_from_address = arkiv_client_http.eth.default_account

        # Wrap in Operations container
        create_op = CreateOp(payload=payload, annotations=annotations, btl=btl)
        operations = Operations(creates=[create_op])

        # Convert to transaction parameters and send
        tx_params = None  # Use default tx params
        tx_params = to_tx_params(operations, tx_params)
        tx_hash = arkiv_client_http.eth.send_transaction(tx_params)

        logger.info(f"Transaction hash: {tx_hash.to_0x_hex()}")

        # Basic transaction hash validation
        assert tx_hash is not None
        assert isinstance(tx_hash, HexBytes)
        assert len(tx_hash) == 32  # Hash length in bytes

        # Wait for transaction confirmation
        tx_receipt: TxReceipt = arkiv_client_http.eth.wait_for_transaction_receipt(
            tx_hash
        )
        logger.info(f"Transaction confirmed in block {tx_receipt['blockNumber']}")
        logger.info(f"Gas used: {tx_receipt['gasUsed']}")
        logger.info(
            f"Transaction status: {'SUCCESS' if tx_receipt['status'] == TX_SUCCESS else 'FAILED'}"
        )
        receipt = to_receipt(arkiv_client_http.arkiv.contract, tx_hash, tx_receipt)
        assert receipt is not None, "Receipt should not be None"
        logger.info(f"Arkiv receipt: {receipt}")

        # Verify transaction was successful
        assert tx_receipt["status"] == TX_SUCCESS, "Transaction should have succeeded"

        # Verify transaction was included in a block
        assert tx_receipt["blockNumber"] is not None, "Transaction should be in a block"
        assert tx_receipt["blockNumber"] > 0, "Block number should be positive"

        # Verify gas was consumed (entity creation should use gas)
        assert tx_receipt["gasUsed"] > 0, "Transaction should have consumed gas"

        # Verify transaction hash matches
        assert tx_receipt["transactionHash"] == tx_hash, (
            "Receipt hash should match transaction hash"
        )

        # Get the actual transaction details for further validation
        tx_details = arkiv_client_http.eth.get_transaction(tx_hash)
        logger.info(f"Transaction from: {tx_details['from']}")
        logger.info(f"Transaction to: {tx_details['to']}")
        logger.info(f"Transaction value: {tx_details['value']}")

        # Verify transaction sender matches the current signer
        assert tx_details["from"] == expected_from_address, (
            f"Transaction sender should be {expected_from_address}, got {tx_details['from']}"
        )

        # Verify transaction was sent to the correct Arkiv storage contract
        assert tx_details["to"] == STORAGE_ADDRESS, (
            f"Transaction should be sent to Arkiv storage contract {STORAGE_ADDRESS}, got {tx_details['to']}"
        )

        # Verify transaction value is 0 (no ETH should be sent)
        assert tx_details["value"] == 0, "Entity creation should not send ETH"

        # Verify transaction contains data (RLP-encoded operations)
        # Some blockchain implementations may use 'input' instead of 'data'
        tx_data = tx_details.get("data") or tx_details.get("input")
        assert tx_data is not None, "Transaction should contain data or input field"
        assert len(tx_data) > 0, "Transaction data should not be empty"
        assert tx_data != "0x", "Transaction data should contain encoded operations"
        logger.info(f"Transaction data length: {len(tx_data)} bytes")

        logger.info("Entity creation successful")

        # assert that receipt has a creates field
        assert hasattr(receipt, "creates"), "Receipt should have 'creates' field"
        assert len(receipt.creates) > 0, (
            "Receipt should have at least one entry in 'creates'"
        )
        create = receipt.creates[0]
        # check that create has an entity_key attribute
        assert hasattr(create, "entity_key"), (
            "Create receipt should have 'entity_key' attribute"
        )
        entity_key = create.entity_key
        assert entity_key is not None, "Entity key should not be None"
        logger.info(f"Entity key: {entity_key}")

        entity = arkiv_client_http.arkiv.get_entity(entity_key)
        logger.info(f"Entity: {entity}")

        assert entity.entity_key == entity_key, "Entity key should match"
        assert entity.payload == payload, "Entity payload should match"
        assert entity.annotations == annotations, "Entity annotations should match"
        assert entity.owner == expected_from_address, (
            "Entity owner should match transaction sender"
        )
        assert entity.expires_at_block is not None, (
            "Entity should have an expiration block"
        )
        assert entity.expires_at_block > 0, "Entity expiration block should be positive"
        assert entity.expires_at_block > tx_receipt["blockNumber"], (
            "Entity expiration block should be in the future"
        )

    def test_create_entity_simple(self, arkiv_client_http: Arkiv) -> None:
        """Test create_entity."""
        pl: bytes = b"Hello world!"
        ann: Annotations = Annotations({"type": "Greeting", "version": 1})
        btl: int = 60

        entity_key, tx_hash = arkiv_client_http.arkiv.create_entity(
            payload=pl, annotations=ann, btl=btl
        )

        label = "create_entity (a)"
        check_entity_key(entity_key, label)
        check_tx_hash(label, tx_hash)

        entity = arkiv_client_http.arkiv.get_entity(entity_key)
        logger.info(f"{label}: Retrieved entity: {entity}")

        assert entity.entity_key == entity_key, f"{label}: Entity key should match"
        assert entity.payload == pl, f"{label}: Entity payload should match"
        assert entity.annotations == ann, f"{label}: Entity annotations should match"
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

    def test_create_entities_bulk(self, arkiv_client_http: Arkiv) -> None:
        """Test create_entities for bulk entity creation."""
        # Create multiple CreateOp objects
        create_ops = [
            CreateOp(
                payload=b"Entity 1",
                annotations=Annotations({"type": "bulk", "index": 1}),
                btl=100,
            ),
            CreateOp(
                payload=b"Entity 2",
                annotations=Annotations({"type": "bulk", "index": 2}),
                btl=100,
            ),
            CreateOp(
                payload=b"Entity 3",
                annotations=Annotations({"type": "bulk", "index": 3}),
                btl=100,
            ),
        ]

        # Call create_entities
        entity_keys, tx_hash = arkiv_client_http.arkiv.create_entities(create_ops)

        label = "create_entities"
        logger.info(f"{label}: Entity keys: {entity_keys}, tx_hash: {tx_hash}")

        # Verify transaction hash
        assert tx_hash is not None, f"{label}: Transaction hash should not be None"
        check_tx_hash(label, tx_hash)

        # Verify all entities were created
        assert len(entity_keys) == 3, f"{label}: Should have 3 created entities"

        # Verify each entity can be retrieved and has correct data
        for i, entity_key in enumerate(entity_keys):
            check_entity_key(entity_key, f"{label} entity {i + 1}")

            entity = arkiv_client_http.arkiv.get_entity(entity_key)
            logger.info(f"{label}: Retrieved entity {i + 1}: {entity}")

            expected_payload = f"Entity {i + 1}".encode()
            expected_annotations = Annotations({"type": "bulk", "index": i + 1})

            assert entity.payload == expected_payload, (
                f"{label}: Entity {i + 1} payload should match"
            )
            assert entity.annotations == expected_annotations, (
                f"{label}: Entity {i + 1} annotations should match"
            )
            assert entity.owner == arkiv_client_http.eth.default_account, (
                f"{label}: Entity {i + 1} owner should match transaction sender"
            )

        logger.info(f"{label}: Bulk entity creation successful")

    def test_create_entities_empty_list_raises(self, arkiv_client_http: Arkiv) -> None:
        """Test that create_entities raises ValueError for empty list."""
        import pytest

        with pytest.raises(
            ValueError, match="create_ops must contain at least one CreateOp"
        ):
            arkiv_client_http.arkiv.create_entities([])
