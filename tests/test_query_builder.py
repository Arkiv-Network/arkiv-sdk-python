"""Tests for fluent query builder API."""

import uuid

import pytest

from arkiv import (
    ASC,
    DESC,
    Arkiv,
    AsyncArkiv,
    IntSort,
    StrSort,
)
from arkiv.types import ATTRIBUTES, KEY, Attributes, CreateOp, Operations

EXPIRES_IN = 100
CONTENT_TYPE = "text/plain"


def create_test_entities(client: Arkiv, num_names: int) -> tuple[str, list[str]]:
    """
    Create test entities with name/sequence combinations for query testing.

    Creates num_names x 3 entities. Each name (name_1, name_2, ...) has 3 entities
    with sequence values 1, 2, 3. This structure allows testing multi-field sorting.

    Example with num_names=2:
        - name="name_1", sequence=1
        - name="name_1", sequence=2
        - name="name_1", sequence=3
        - name="name_2", sequence=1
        - name="name_2", sequence=2
        - name="name_2", sequence=3

    All entities are created in a single transaction using client.arkiv.execute().

    Returns:
        Tuple of (batch_id, list of entity keys)
    """
    batch_id = str(uuid.uuid4())

    # Build list of CreateOp operations
    create_ops: list[CreateOp] = []
    entity_num = 0
    for name_idx in range(1, num_names + 1):
        for seq in range(1, 4):  # sequence 1, 2, 3 for each name
            entity_num += 1
            payload = f"Entity {entity_num}".encode()
            attributes = Attributes(
                {"batch_id": batch_id, "sequence": seq, "name": f"name_{name_idx}"}
            )

            create_op = CreateOp(
                payload=payload,
                content_type=CONTENT_TYPE,
                attributes=attributes,
                expires_in=EXPIRES_IN,
            )
            create_ops.append(create_op)

    # Execute all creates in a single transaction
    operations = Operations(creates=create_ops)
    receipt = client.arkiv.execute(operations)

    # Extract entity keys from receipt
    entity_keys = [create.key for create in receipt.creates]

    return batch_id, entity_keys


class TestIntSort:
    """Tests for IntSort dataclass."""

    def test_default_direction_is_asc(self) -> None:
        """Test that default direction is ascending."""
        attr = IntSort("age")
        assert attr.name == "age"
        assert attr.direction == ASC

    def test_explicit_desc_direction(self) -> None:
        """Test explicit descending direction."""
        attr = IntSort("age", DESC)
        assert attr.name == "age"
        assert attr.direction == DESC

    def test_asc_method(self) -> None:
        """Test .asc() method returns new instance with ASC direction."""
        attr = IntSort("age", DESC)
        asc_attr = attr.asc()
        assert asc_attr.direction == ASC
        assert asc_attr.name == "age"
        # Original unchanged
        assert attr.direction == DESC

    def test_desc_method(self) -> None:
        """Test .desc() method returns new instance with DESC direction."""
        attr = IntSort("age")
        desc_attr = attr.desc()
        assert desc_attr.direction == DESC
        assert desc_attr.name == "age"
        # Original unchanged
        assert attr.direction == ASC

    def test_to_order_by_attribute(self) -> None:
        """Test conversion to OrderByAttribute."""
        attr = IntSort("priority", DESC)
        order_by = attr.to_order_by_attribute()
        assert order_by.attribute == "priority"
        assert order_by.type == "int"
        assert order_by.direction == "desc"


class TestStrSort:
    """Tests for StrSort dataclass."""

    def test_default_direction_is_asc(self) -> None:
        """Test that default direction is ascending."""
        attr = StrSort("name")
        assert attr.name == "name"
        assert attr.direction == ASC

    def test_explicit_desc_direction(self) -> None:
        """Test explicit descending direction."""
        attr = StrSort("status", DESC)
        assert attr.name == "status"
        assert attr.direction == DESC

    def test_asc_method(self) -> None:
        """Test .asc() method returns new instance with ASC direction."""
        attr = StrSort("name", DESC)
        asc_attr = attr.asc()
        assert asc_attr.direction == ASC
        assert asc_attr.name == "name"
        # Original unchanged
        assert attr.direction == DESC

    def test_desc_method(self) -> None:
        """Test .desc() method returns new instance with DESC direction."""
        attr = StrSort("name")
        desc_attr = attr.desc()
        assert desc_attr.direction == DESC
        assert desc_attr.name == "name"
        # Original unchanged
        assert attr.direction == ASC

    def test_to_order_by_attribute(self) -> None:
        """Test conversion to OrderByAttribute."""
        attr = StrSort("status", DESC)
        order_by = attr.to_order_by_attribute()
        assert order_by.attribute == "status"
        assert order_by.type == "str"
        assert order_by.direction == "desc"


class TestQueryBuilder:
    """Tests for sync QueryBuilder fluent API."""

    def test_select_all_fields(self, arkiv_client_http: Arkiv) -> None:
        """Test .select() with no args selects all fields."""
        batch_id, _ = create_test_entities(arkiv_client_http, 1)  # 1 name x 3 seq = 3

        results = list(
            arkiv_client_http.arkiv.select().where(f'batch_id = "{batch_id}"').fetch()
        )

        assert len(results) == 3
        # All fields should be populated
        for entity in results:
            assert entity.key is not None
            assert entity.attributes is not None
            assert entity.payload is not None

    def test_select_specific_fields(self, arkiv_client_http: Arkiv) -> None:
        """Test .select() with specific field bitmasks."""
        batch_id, _ = create_test_entities(arkiv_client_http, 1)  # 1 name x 3 seq = 3

        results = list(
            arkiv_client_http.arkiv.select(KEY, ATTRIBUTES)
            .where(f'batch_id = "{batch_id}"')
            .fetch()
        )

        assert len(results) == 3
        for entity in results:
            assert entity.key is not None
            assert entity.attributes is not None
            # PAYLOAD was not selected
            assert entity.payload is None

    def test_where_clause(self, arkiv_client_http: Arkiv) -> None:
        """Test .where() filters results correctly."""
        batch_id, _ = create_test_entities(arkiv_client_http, 2)  # 2 names x 3 seq = 6

        # Query for specific sequence (each name has seq 1,2,3 so seq=3 matches 2)
        results = list(
            arkiv_client_http.arkiv.select(KEY, ATTRIBUTES)
            .where(f'batch_id = "{batch_id}" AND sequence = 3')
            .fetch()
        )

        assert len(results) == 2
        for result in results:
            assert result.attributes is not None
            assert result.attributes["sequence"] == 3

    def test_order_by_int_asc(self, arkiv_client_http: Arkiv) -> None:
        """Test .order_by() with IntSort ascending."""
        batch_id, _ = create_test_entities(
            arkiv_client_http, 2
        )  # 2 names times 3 seq = 6

        results = list(
            arkiv_client_http.arkiv.select(KEY, ATTRIBUTES)
            .where(f'batch_id = "{batch_id}"')
            .order_by(IntSort("sequence"))
            .fetch()
        )

        assert len(results) == 6
        sequences = [e.attributes["sequence"] for e in results if e.attributes]
        # Each sequence value appears twice (once per name)
        assert sequences == [1, 1, 2, 2, 3, 3]

    def test_order_by_int_desc(self, arkiv_client_http: Arkiv) -> None:
        """Test .order_by() with IntSort descending."""
        batch_id, _ = create_test_entities(
            arkiv_client_http, 2
        )  # 2 names times 3 seq = 6

        results = list(
            arkiv_client_http.arkiv.select(KEY, ATTRIBUTES)
            .where(f'batch_id = "{batch_id}"')
            .order_by(IntSort("sequence", DESC))
            .fetch()
        )

        assert len(results) == 6
        sequences = [e.attributes["sequence"] for e in results if e.attributes]
        # Each sequence value appears twice (once per name)
        assert sequences == [3, 3, 2, 2, 1, 1]

    def test_order_by_str_asc(self, arkiv_client_http: Arkiv) -> None:
        """Test .order_by() with StrSort ascending."""
        batch_id, _ = create_test_entities(arkiv_client_http, 3)  # 3 names x 3 seq = 9

        results = list(
            arkiv_client_http.arkiv.select(KEY, ATTRIBUTES)
            .where(f'batch_id = "{batch_id}"')
            .order_by(StrSort("name"))
            .fetch()
        )

        assert len(results) == 9
        names = [e.attributes["name"] for e in results if e.attributes]
        # Each name appears 3 times (once per sequence)
        assert names == ["name_1"] * 3 + ["name_2"] * 3 + ["name_3"] * 3

    def test_order_by_str_desc(self, arkiv_client_http: Arkiv) -> None:
        """Test .order_by() with StrSort descending."""
        batch_id, _ = create_test_entities(arkiv_client_http, 3)  # 3 names x 3 seq = 9

        results = list(
            arkiv_client_http.arkiv.select(KEY, ATTRIBUTES)
            .where(f'batch_id = "{batch_id}"')
            .order_by(StrSort("name", DESC))
            .fetch()
        )

        assert len(results) == 9
        names = [e.attributes["name"] for e in results if e.attributes]
        # Each name appears 3 times (once per sequence), descending order
        assert names == ["name_3"] * 3 + ["name_2"] * 3 + ["name_1"] * 3

    def test_complex_where_with_multiple_order_by(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test complex WHERE with AND/OR and multiple ORDER BY fields."""
        batch_id, _ = create_test_entities(arkiv_client_http, 3)  # 3 names x 3 seq = 9

        # Query: (name_1 OR name_3) AND (sequence = 1 OR sequence = 3)
        # This should match 4 entities:
        #   name_1/seq=1, name_1/seq=3, name_3/seq=1, name_3/seq=3
        # Order by: sequence DESC, name ASC
        # Expected order: (3, name_1), (3, name_3), (1, name_1), (1, name_3)
        results = list(
            arkiv_client_http.arkiv.select(KEY, ATTRIBUTES)
            .where(
                f'batch_id = "{batch_id}" AND '
                f'(name = "name_1" OR name = "name_3") AND '
                f"(sequence = 1 OR sequence = 3)"
            )
            .order_by(IntSort("sequence", DESC), StrSort("name"))
            .fetch()
        )

        assert len(results) == 4
        # Extract (sequence, name) tuples
        result_pairs = [
            (e.attributes["sequence"], e.attributes["name"])
            for e in results
            if e.attributes
        ]
        # Sorted by sequence DESC, then name ASC
        assert result_pairs == [
            (3, "name_1"),
            (3, "name_3"),
            (1, "name_1"),
            (1, "name_3"),
        ]

    def test_count(self, arkiv_client_http: Arkiv) -> None:
        """Test .count() returns correct count."""
        batch_id, _ = create_test_entities(arkiv_client_http, 2)  # 2 names x 3 seq = 6

        count = (
            arkiv_client_http.arkiv.select().where(f'batch_id = "{batch_id}"').count()
        )

        assert count == 6

    def test_count_with_filter(self, arkiv_client_http: Arkiv) -> None:
        """Test .count() with WHERE filter."""
        batch_id, _ = create_test_entities(arkiv_client_http, 3)  # 3 names x 3 seq = 9

        # Filter to sequence <= 2: each name has seq 1,2 matching = 3 names x 2 = 6
        count = (
            arkiv_client_http.arkiv.select()
            .where(f'batch_id = "{batch_id}" AND sequence <= 2')
            .count()
        )

        assert count == 6

    def test_count_empty_result(self, arkiv_client_http: Arkiv) -> None:
        """Test .count() returns 0 for no matches."""
        count = (
            arkiv_client_http.arkiv.select()
            .where('batch_id = "nonexistent-batch-id"')
            .count()
        )

        assert count == 0

    def test_method_chaining(self, arkiv_client_http: Arkiv) -> None:
        """Test that all methods return self for chaining."""
        builder = arkiv_client_http.arkiv.select(KEY, ATTRIBUTES)

        # Each method should return the same builder instance
        builder2 = builder.where('type = "test"')
        assert builder2 is builder

        builder3 = builder.order_by(IntSort("sequence"))
        assert builder3 is builder

        builder4 = builder.at_block(12345)
        assert builder4 is builder


class TestAsyncQueryBuilder:
    """Tests for async AsyncQueryBuilder fluent API."""

    @pytest.mark.asyncio
    async def test_select_all_fields(self, async_arkiv_client_http: AsyncArkiv) -> None:
        """Test async .select() with no args selects all fields."""
        # Create entities using sync client first (from fixture's underlying connection)
        # For async tests, we need to use the async client for everything
        batch_id = str(uuid.uuid4())

        # Create test entities using async client
        create_ops = [
            CreateOp(
                payload=f"Entity {i}".encode(),
                content_type=CONTENT_TYPE,
                attributes=Attributes(
                    {"batch_id": batch_id, "sequence": i, "name": f"entity_{i}"}
                ),
                expires_in=EXPIRES_IN,
            )
            for i in range(1, 4)
        ]
        operations = Operations(creates=create_ops)
        await async_arkiv_client_http.arkiv.execute(operations)

        results = []
        async for entity in (
            async_arkiv_client_http.arkiv.select()
            .where(f'batch_id = "{batch_id}"')
            .fetch()
        ):
            results.append(entity)

        assert len(results) == 3
        for entity in results:
            assert entity.key is not None
            assert entity.attributes is not None
            assert entity.payload is not None

    @pytest.mark.asyncio
    async def test_async_count(self, async_arkiv_client_http: AsyncArkiv) -> None:
        """Test async .count() returns correct count."""
        batch_id = str(uuid.uuid4())

        # Create test entities
        create_ops = [
            CreateOp(
                payload=f"Entity {i}".encode(),
                content_type=CONTENT_TYPE,
                attributes=Attributes({"batch_id": batch_id, "sequence": i}),
                expires_in=EXPIRES_IN,
            )
            for i in range(1, 6)
        ]
        operations = Operations(creates=create_ops)
        await async_arkiv_client_http.arkiv.execute(operations)

        count = await (
            async_arkiv_client_http.arkiv.select()
            .where(f'batch_id = "{batch_id}"')
            .count()
        )

        assert count == 5

    @pytest.mark.asyncio
    async def test_async_order_by(self, async_arkiv_client_http: AsyncArkiv) -> None:
        """Test async .order_by() sorts results correctly."""
        batch_id = str(uuid.uuid4())

        # Create test entities
        create_ops = [
            CreateOp(
                payload=f"Entity {i}".encode(),
                content_type=CONTENT_TYPE,
                attributes=Attributes({"batch_id": batch_id, "sequence": i}),
                expires_in=EXPIRES_IN,
            )
            for i in range(1, 4)
        ]
        operations = Operations(creates=create_ops)
        await async_arkiv_client_http.arkiv.execute(operations)

        results = []
        async for entity in (
            async_arkiv_client_http.arkiv.select(KEY, ATTRIBUTES)
            .where(f'batch_id = "{batch_id}"')
            .order_by(IntSort("sequence", DESC))
            .fetch()
        ):
            results.append(entity)

        assert len(results) == 3
        sequences = [e.attributes["sequence"] for e in results if e.attributes]
        assert sequences == [3, 2, 1]
