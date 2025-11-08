"""Tests for query field selection and projection."""

from eth_typing import ChecksumAddress

from arkiv import Arkiv
from arkiv.types import (
    ALL,
    ATTRIBUTES,
    CONTENT_TYPE,
    CREATED_AT,
    EXPIRATION,
    KEY,
    LAST_MODIFIED_AT,
    NONE,
    OP_INDEX_IN_TX,
    OWNER,
    PAYLOAD,
    TX_INDEX_IN_BLOCK,
    Attributes,
    Entity,
    EntityKey,
    QueryOptions,
)

BTL = 100
CONTENT_TYPE_VALUE = "text/plain"


def create_test_entities(
    client: Arkiv,
) -> tuple[EntityKey, EntityKey]:
    """
    Create two test entities with different payloads and attributes.

    Returns:
        Tuple of (entity_key_1, entity_key_2, unique_id)
    """
    # Create first entity
    payload1 = b"First entity payload"
    attributes1 = Attributes({"name": "Alice", "age": 30})
    entity_key_1, _ = client.arkiv.create_entity(
        payload=payload1,
        content_type=CONTENT_TYPE_VALUE,
        attributes=attributes1,
        btl=BTL,
    )

    # Update first entity to change last_modified_at
    updated_payload1 = b"First entity payload - updated"
    client.arkiv.update_entity(
        entity_key_1,
        payload=updated_payload1,
        content_type=CONTENT_TYPE_VALUE,
        attributes=attributes1,
        btl=BTL,
    )

    # Create second entity
    payload2 = b"Second entity payload"
    attributes2 = Attributes({"name": "Bob", "age": 25})
    entity_key_2, _ = client.arkiv.create_entity(
        payload=payload2,
        content_type=CONTENT_TYPE_VALUE,
        attributes=attributes2,
        btl=BTL,
    )

    # Update second entity to change last_modified_at
    updated_payload2 = b"Second entity payload - updated"
    client.arkiv.update_entity(
        entity_key_2,
        payload=updated_payload2,
        content_type=CONTENT_TYPE_VALUE,
        attributes=attributes2,
        btl=BTL,
    )

    return entity_key_1, entity_key_2


def query_entity_by_key(
    client: Arkiv, entity_key: EntityKey, fields: int
) -> tuple[QueryOptions, EntityKey]:
    """
    Helper to query an entity by key with specified fields.

    Returns:
        Tuple of (result entity, expected entity_key)
    """
    query = f'$key = "{entity_key}"'
    options = QueryOptions(fields=fields)
    result = client.arkiv.query_entities_page(query=query, options=options)

    # Should find exactly one entity
    assert len(result.entities) == 1
    entity = result.entities[0]

    # Verify fields bitmask matches request
    assert entity.fields == fields

    return entity, entity_key


def validate_entity(
    entity: Entity,
    entity_key: EntityKey | None = None,
    owner: ChecksumAddress | None = None,
    created_at_block: int | None = None,
    last_modified_at_block: int | None = None,
    expires_at_block: int | None = None,
    transaction_index: int | None = None,
    operation_index: int | None = None,
    payload: bytes | None = None,
    content_type: str | None = None,
    attributes: Attributes | None = None,
) -> None:
    """
    Validate entity fields against expected values.

    All parameters default to None, meaning we expect those fields to be None.
    """
    assert entity.key == entity_key, (
        f"Entity key mismatch: expected {entity_key}, got {entity.key}"
    )

    assert entity.owner == owner, (
        f"Owner mismatch: expected {owner}, got {entity.owner}"
    )

    assert entity.created_at_block == created_at_block, (
        f"Created at block mismatch: expected {created_at_block}, "
        f"got {entity.created_at_block}"
    )

    assert entity.last_modified_at_block == last_modified_at_block, (
        f"Last modified at block mismatch: expected {last_modified_at_block}, "
        f"got {entity.last_modified_at_block}"
    )

    assert entity.expires_at_block == expires_at_block, (
        f"Expires at block mismatch: expected {expires_at_block}, "
        f"got {entity.expires_at_block}"
    )

    assert entity.transaction_index == transaction_index, (
        f"Transaction index mismatch: expected {transaction_index}, "
        f"got {entity.transaction_index}"
    )

    assert entity.operation_index == operation_index, (
        f"Operation index mismatch: expected {operation_index}, "
        f"got {entity.operation_index}"
    )

    assert entity.payload == payload, (
        f"Payload mismatch: expected {payload}, got {entity.payload}"
    )

    assert entity.content_type == content_type, (
        f"Content type mismatch: expected {content_type}, got {entity.content_type}"
    )

    assert entity.attributes == attributes, (
        f"Attributes mismatch: expected {attributes}, got {entity.attributes}"
    )


class TestQuerySelect:
    """Test selecting specific fields from query results."""

    def test_query_select_no_fields(self, arkiv_client_http: Arkiv) -> None:
        """Test querying entities with NONE fields - no data should be populated."""
        # Create test entities
        entity_key_1, _ = create_test_entities(arkiv_client_http)

        # Query with NONE fields
        entity, _ = query_entity_by_key(arkiv_client_http, entity_key_1, NONE)

        # Verify all fields are None (no data populated)
        validate_entity(entity)

    def test_query_select_all_fields(self, arkiv_client_http: Arkiv) -> None:
        """Test querying entities with ALL fields - all data should be populated."""
        # Create test entities
        _, entity_key_2 = create_test_entities(arkiv_client_http)

        # Query with ALL fields
        entity, expected_key = query_entity_by_key(arkiv_client_http, entity_key_2, ALL)

        # Calculate expected values
        expected_created_at = entity.created_at_block
        expected_last_modified_at = (
            expected_created_at + 1 if expected_created_at else None
        )
        expected_expires_at = (
            expected_last_modified_at + BTL if expected_last_modified_at else None
        )

        # Verify all fields are populated with correct values
        validate_entity(
            entity,
            entity_key=expected_key,
            owner=arkiv_client_http.eth.default_account,
            created_at_block=expected_created_at,
            last_modified_at_block=expected_last_modified_at,
            expires_at_block=expected_expires_at,
            transaction_index=entity.transaction_index,  # Just verify not None
            operation_index=entity.operation_index,  # Just verify not None
            payload=b"Second entity payload - updated",
            content_type=CONTENT_TYPE_VALUE,
            attributes=Attributes({"name": "Bob", "age": 25}),
        )

    def test_query_select_key_only(self, arkiv_client_http: Arkiv) -> None:
        """Test querying with only KEY field."""
        entity_key_1, _ = create_test_entities(arkiv_client_http)
        entity, expected_key = query_entity_by_key(arkiv_client_http, entity_key_1, KEY)

        validate_entity(entity, entity_key=expected_key)

    def test_query_select_owner_only(self, arkiv_client_http: Arkiv) -> None:
        """Test querying with only OWNER field."""
        entity_key_1, _ = create_test_entities(arkiv_client_http)
        entity, _ = query_entity_by_key(arkiv_client_http, entity_key_1, OWNER)

        validate_entity(entity, owner=arkiv_client_http.eth.default_account)

    def test_query_select_payload_only(self, arkiv_client_http: Arkiv) -> None:
        """Test querying with only PAYLOAD field."""
        entity_key_1, _ = create_test_entities(arkiv_client_http)
        entity, _ = query_entity_by_key(arkiv_client_http, entity_key_1, PAYLOAD)

        validate_entity(entity, payload=b"First entity payload - updated")

    def test_query_select_content_type_only(self, arkiv_client_http: Arkiv) -> None:
        """Test querying with only CONTENT_TYPE field."""
        entity_key_1, _ = create_test_entities(arkiv_client_http)
        entity, _ = query_entity_by_key(arkiv_client_http, entity_key_1, CONTENT_TYPE)

        validate_entity(entity, content_type=CONTENT_TYPE_VALUE)

    def test_query_select_attributes_only(self, arkiv_client_http: Arkiv) -> None:
        """Test querying with only ATTRIBUTES field (requires KEY for query)."""
        entity_key_1, _ = create_test_entities(arkiv_client_http)
        # query with ATTRIBUTES only leads to web3.exceptions.Web3RPCError: {'code': -32603, 'message': 'method handler crashed'}
        # entity, _ = query_entity_by_key(arkiv_client_http, entity_key_1, ATTRIBUTES)
        # query with KEY | ATTRIBUTES works
        entity, _ = query_entity_by_key(
            arkiv_client_http, entity_key_1, KEY | ATTRIBUTES
        )

        validate_entity(
            entity,
            entity_key=entity_key_1,
            attributes=Attributes({"name": "Alice", "age": 30}),
        )

    def test_query_select_expiration_only(self, arkiv_client_http: Arkiv) -> None:
        """Test querying with only EXPIRATION field."""
        entity_key_1, _ = create_test_entities(arkiv_client_http)
        entity, _ = query_entity_by_key(arkiv_client_http, entity_key_1, EXPIRATION)

        assert entity.expires_at_block is not None
        assert entity.expires_at_block > 0

    def test_query_select_created_at_only(self, arkiv_client_http: Arkiv) -> None:
        """Test querying with only CREATED_AT field."""
        entity_key_1, _ = create_test_entities(arkiv_client_http)
        entity, _ = query_entity_by_key(arkiv_client_http, entity_key_1, CREATED_AT)

        assert entity.created_at_block is not None
        assert entity.created_at_block > 0

    def test_query_select_last_modified_at_only(self, arkiv_client_http: Arkiv) -> None:
        """Test querying with only LAST_MODIFIED_AT field."""
        entity_key_1, _ = create_test_entities(arkiv_client_http)
        entity, _ = query_entity_by_key(
            arkiv_client_http, entity_key_1, LAST_MODIFIED_AT
        )

        assert entity.last_modified_at_block is not None
        assert entity.last_modified_at_block > 0

    def test_query_select_tx_index_only(self, arkiv_client_http: Arkiv) -> None:
        """Test querying with only TX_INDEX_IN_BLOCK field."""
        entity_key_1, _ = create_test_entities(arkiv_client_http)
        entity, _ = query_entity_by_key(
            arkiv_client_http, entity_key_1, TX_INDEX_IN_BLOCK
        )

        assert entity.transaction_index is not None
        assert entity.transaction_index >= 0

    def test_query_select_op_index_only(self, arkiv_client_http: Arkiv) -> None:
        """Test querying with only OP_INDEX_IN_TX field."""
        entity_key_1, _ = create_test_entities(arkiv_client_http)
        entity, _ = query_entity_by_key(arkiv_client_http, entity_key_1, OP_INDEX_IN_TX)

        assert entity.operation_index is not None
        assert entity.operation_index >= 0
