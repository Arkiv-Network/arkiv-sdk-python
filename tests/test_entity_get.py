"""Tests for entity retrieval functionality in ArkivModule."""

import logging

from arkiv.client import Arkiv
from arkiv.types import ALL, KEY, NONE, Attributes, EntityKey
from arkiv.utils import check_entity_key

from .utils import get_custom_attributes

logger = logging.getLogger(__name__)


class TestEntityExists:
    """Test suite for entity existence."""

    def test_entity_exists_happy_case(self, arkiv_client_http: Arkiv) -> None:
        """Test retrieving only the key field of a newly created entity."""

        entity_key, _, _, _ = create_entity(arkiv_client_http)
        exists = arkiv_client_http.arkiv.entity_exists(entity_key)
        assert exists, "Entity should exist"

    def test_entity_exists_non_existent(self, arkiv_client_http: Arkiv) -> None:
        """Test entity_exists with non-existent entity key."""

        entity_key = "non_existent_entity_key"
        exists = arkiv_client_http.arkiv.entity_exists(entity_key)
        assert not exists, "Entity should not exist"


class TestEntityGetDefault:
    """Test suite for entity retrieval default."""

    def test_get_entity_all_fields(self, arkiv_client_http: Arkiv) -> None:
        """Test retrieving all fields of a newly created entity."""
        entity_key, payload, content_type, attributes = create_entity(arkiv_client_http)

        # Verify entity was created
        check_entity_key(entity_key, "test_get_entity_all_fields")

        # Retrieve entity with all fields (default behavior)
        entity = arkiv_client_http.arkiv.get_entity(entity_key)

        # Verify all fields are populated
        assert entity.key == entity_key, "Entity key should match"
        assert entity.fields == ALL, "All fields should be populated"
        assert entity.owner is not None, "Owner should be populated"
        assert entity.owner == arkiv_client_http.eth.default_account, (
            "Owner should match creator"
        )
        assert entity.payload == payload, "Payload should match"
        assert entity.content_type == content_type, "Content type should match"
        assert entity.expires_at_block is not None, "Expiration should be populated"
        assert entity.expires_at_block > 0, "Expiration should be positive"
        assert entity.attributes is not None, "Attributes should be populated"

        # Verify custom attributes (excluding system fields like $key, $owner, etc)
        custom_attributes = get_custom_attributes(entity)
        assert custom_attributes == attributes, "Custom attributes should match"

        logger.info("test_get_entity_all_fields: Successfully retrieved all fields")


class TestEntityGetProjections:
    """Test suite for entity retrieval projections."""

    def test_get_entity_key_only(self, arkiv_client_http: Arkiv) -> None:
        """Test retrieving only the key field of a newly created entity."""
        entity_key, _, _, _ = create_entity(arkiv_client_http)

        # Verify entity was created
        check_entity_key(entity_key, "test_get_entity_all_fields")

        # Retrieve entity with only KEY field
        entity = arkiv_client_http.arkiv.get_entity(entity_key, fields=KEY)

        # Verify only key is populated
        assert entity.key == entity_key, "Entity key should match"
        assert entity.fields == KEY, "Only KEY field should be set in bitmask"

        # All other fields should be None
        assert entity.owner is None, "Owner should not be populated"
        assert entity.payload is None, "Payload should not be populated"
        assert entity.content_type is None, "Content type should not be populated"
        assert entity.expires_at_block is None, "Expiration should not be populated"
        assert entity.attributes is None, "Attributes should not be populated"

        logger.info("test_get_entity_key_only: Successfully retrieved key only")

    def test_get_entity_no_fields(self, arkiv_client_http: Arkiv) -> None:
        """Test retrieving entity with no fields (NONE bitmask)."""
        entity_key, _, _, _ = create_entity(arkiv_client_http)

        # Verify entity was created
        check_entity_key(entity_key, "test_get_entity_no_fields")

        # Retrieve entity with NONE fields
        entity = arkiv_client_http.arkiv.get_entity(entity_key, fields=NONE)

        # Verify entity exists but has no fields populated
        assert entity.key is None, "Entity key should not be populated"
        assert entity.fields == NONE, "No fields should be set in bitmask"

        # All optional fields should be None
        assert entity.owner is None, "Owner should not be populated"
        assert entity.payload is None, "Payload should not be populated"
        assert entity.content_type is None, "Content type should not be populated"
        assert entity.expires_at_block is None, "Expiration should not be populated"
        assert entity.attributes is None, "Attributes should not be populated"

        logger.info(
            "test_get_entity_no_fields: Successfully retrieved entity with no fields"
        )


def create_entity(
    arkiv_client_http: Arkiv,
) -> tuple[EntityKey, bytes, str, Attributes]:
    # Create an entity with all data
    payload = b"Test entity data"
    content_type = "text/plain"
    attributes = Attributes({"type": "test", "version": 1})
    btl = 100

    entity_key, _ = arkiv_client_http.arkiv.create_entity(
        payload=payload,
        content_type=content_type,
        attributes=attributes,
        btl=btl,
    )

    return entity_key, payload, content_type, attributes
