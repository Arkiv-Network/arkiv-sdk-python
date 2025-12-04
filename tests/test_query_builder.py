"""Tests for fluent query builder API."""

import uuid

import pytest

from arkiv import (
    ASC,
    DESC,
    Arkiv,
    AsyncArkiv,
    Expr,
    IntAttr,
    IntSort,
    StrAttr,
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


# =============================================================================
# Expression Builder Tests
# =============================================================================


class TestExpr:
    """Tests for Expr class."""

    def test_to_sql(self) -> None:
        """Test to_sql() returns the SQL string."""
        expr = Expr("age >= 18")
        assert expr.to_sql() == "age >= 18"

    def test_and_operator(self) -> None:
        """Test & operator combines expressions with AND."""
        expr1 = Expr("age >= 18")
        expr2 = Expr('status = "active"')
        result = expr1 & expr2
        assert result.to_sql() == 'age >= 18 AND status = "active"'

    def test_or_operator(self) -> None:
        """Test | operator combines expressions with OR (wrapped in parens)."""
        expr1 = Expr('role = "admin"')
        expr2 = Expr('role = "moderator"')
        result = expr1 | expr2
        assert result.to_sql() == '(role = "admin" OR role = "moderator")'

    def test_not_operator(self) -> None:
        """Test ~ operator negates expression with NOT."""
        expr = Expr('status = "banned"')
        result = ~expr
        assert result.to_sql() == 'NOT (status = "banned")'

    def test_complex_combination(self) -> None:
        """Test combining multiple operators."""
        a = Expr("age >= 18")
        b = Expr('status = "active"')
        c = Expr('role = "guest"')

        # (a AND b) OR c
        result = (a & b) | c
        assert result.to_sql() == '(age >= 18 AND status = "active" OR role = "guest")'

        # a AND (b OR c)
        result = a & (b | c)
        assert result.to_sql() == 'age >= 18 AND (status = "active" OR role = "guest")'

        # NOT (a AND b)
        result = ~(a & b)
        assert result.to_sql() == 'NOT (age >= 18 AND status = "active")'

    def test_repr(self) -> None:
        """Test __repr__ for debugging."""
        expr = Expr("age >= 18")
        assert repr(expr) == "Expr('age >= 18')"


class TestIntAttr:
    """Tests for IntAttr expression builder."""

    def test_eq(self) -> None:
        """Test == operator."""
        expr = IntAttr("age") == 18
        assert expr.to_sql() == "age = 18"

    def test_ne(self) -> None:
        """Test != operator."""
        expr = IntAttr("age") != 18
        assert expr.to_sql() == "age != 18"

    def test_gt(self) -> None:
        """Test > operator."""
        expr = IntAttr("age") > 18
        assert expr.to_sql() == "age > 18"

    def test_ge(self) -> None:
        """Test >= operator."""
        expr = IntAttr("age") >= 18
        assert expr.to_sql() == "age >= 18"

    def test_lt(self) -> None:
        """Test < operator."""
        expr = IntAttr("age") < 65
        assert expr.to_sql() == "age < 65"

    def test_le(self) -> None:
        """Test <= operator."""
        expr = IntAttr("age") <= 65
        assert expr.to_sql() == "age <= 65"

    def test_type_error_on_string(self) -> None:
        """Test TypeError raised when comparing to string."""
        with pytest.raises(TypeError, match="IntAttr 'age' requires int, got str"):
            _ = IntAttr("age") == "18"

    def test_type_error_on_float(self) -> None:
        """Test TypeError raised when comparing to float."""
        with pytest.raises(TypeError, match="IntAttr 'age' requires int, got float"):
            _ = IntAttr("age") >= 18.5

    def test_type_error_on_bool(self) -> None:
        """Test TypeError raised when comparing to bool (bool is subclass of int)."""
        with pytest.raises(TypeError, match="IntAttr 'active' requires int, got bool"):
            _ = IntAttr("active") == True  # noqa: E712

    def test_repr(self) -> None:
        """Test __repr__ for debugging."""
        attr = IntAttr("age")
        assert repr(attr) == "IntAttr('age')"

    def test_combining_with_and(self) -> None:
        """Test combining IntAttr expressions with &."""
        age = IntAttr("age")
        expr = (age >= 18) & (age < 65)
        assert expr.to_sql() == "age >= 18 AND age < 65"


class TestStrAttr:
    """Tests for StrAttr expression builder."""

    def test_eq(self) -> None:
        """Test == operator."""
        expr = StrAttr("status") == "active"
        assert expr.to_sql() == 'status = "active"'

    def test_ne(self) -> None:
        """Test != operator."""
        expr = StrAttr("status") != "banned"
        assert expr.to_sql() == 'status != "banned"'

    def test_gt(self) -> None:
        """Test > operator."""
        expr = StrAttr("name") > "A"
        assert expr.to_sql() == 'name > "A"'

    def test_ge(self) -> None:
        """Test >= operator."""
        expr = StrAttr("name") >= "A"
        assert expr.to_sql() == 'name >= "A"'

    def test_lt(self) -> None:
        """Test < operator."""
        expr = StrAttr("name") < "Z"
        assert expr.to_sql() == 'name < "Z"'

    def test_le(self) -> None:
        """Test <= operator."""
        expr = StrAttr("name") <= "Z"
        assert expr.to_sql() == 'name <= "Z"'

    def test_type_error_on_int(self) -> None:
        """Test TypeError raised when comparing to int."""
        with pytest.raises(TypeError, match="StrAttr 'status' requires str, got int"):
            _ = StrAttr("status") == 1

    def test_type_error_on_none(self) -> None:
        """Test TypeError raised when comparing to None."""
        with pytest.raises(
            TypeError, match="StrAttr 'status' requires str, got NoneType"
        ):
            _ = StrAttr("status") == None  # noqa: E711

    def test_repr(self) -> None:
        """Test __repr__ for debugging."""
        attr = StrAttr("status")
        assert repr(attr) == "StrAttr('status')"

    def test_combining_with_or(self) -> None:
        """Test combining StrAttr expressions with |."""
        role = StrAttr("role")
        expr = (role == "admin") | (role == "moderator")
        assert expr.to_sql() == '(role = "admin" OR role = "moderator")'


class TestExpressionBuilderIntegration:
    """Tests for expression builder combined usage."""

    def test_mixed_int_and_str_attrs(self) -> None:
        """Test combining IntAttr and StrAttr expressions."""
        age = IntAttr("age")
        status = StrAttr("status")

        expr = (age >= 18) & (status == "active")
        assert expr.to_sql() == 'age >= 18 AND status = "active"'

    def test_complex_expression(self) -> None:
        """Test complex expression with multiple operators."""
        age = IntAttr("age")
        status = StrAttr("status")
        role = StrAttr("role")

        # (admin OR moderator) AND active AND age >= 18
        expr = (
            ((role == "admin") | (role == "moderator"))
            & (status == "active")
            & (age >= 18)
        )
        assert (
            expr.to_sql()
            == '(role = "admin" OR role = "moderator") AND status = "active" AND age >= 18'
        )

    def test_not_with_combined_expression(self) -> None:
        """Test NOT with a combined expression."""
        role = StrAttr("role")
        status = StrAttr("status")

        expr = ~((role == "guest") | (status == "inactive"))
        assert expr.to_sql() == 'NOT ((role = "guest" OR status = "inactive"))'


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

    def test_where_with_expr(self, arkiv_client_http: Arkiv) -> None:
        """Test .where() with Expr expression builder."""
        batch_id, _ = create_test_entities(arkiv_client_http, 2)  # 2 names x 3 seq = 6

        # Build expression using IntAttr/StrAttr
        batch_attr = StrAttr("batch_id")
        seq_attr = IntAttr("sequence")
        expr = (batch_attr == batch_id) & (seq_attr == 3)

        results = list(
            arkiv_client_http.arkiv.select(KEY, ATTRIBUTES).where(expr).fetch()
        )

        assert len(results) == 2
        for result in results:
            assert result.attributes is not None
            assert result.attributes["sequence"] == 3

    def test_where_with_complex_expr(self, arkiv_client_http: Arkiv) -> None:
        """Test .where() with complex Expr using OR and NOT."""
        batch_id, _ = create_test_entities(arkiv_client_http, 3)  # 3 names x 3 seq = 9

        # Query: batch_id AND (sequence = 1 OR sequence = 3)
        batch_attr = StrAttr("batch_id")
        seq_attr = IntAttr("sequence")
        expr = (batch_attr == batch_id) & ((seq_attr == 1) | (seq_attr == 3))

        results = list(
            arkiv_client_http.arkiv.select(KEY, ATTRIBUTES).where(expr).fetch()
        )

        # Each name has seq 1 and 3 = 2 per name x 3 names = 6
        assert len(results) == 6
        for result in results:
            assert result.attributes is not None
            assert result.attributes["sequence"] in [1, 3]

    def test_where_with_mixed_or_and_expr(self, arkiv_client_http: Arkiv) -> None:
        """Test .where() with mixed OR and AND expression pattern from README.

        Tests the pattern: (role == "admin") | (role == "moderator") & (status == "active")
        This verifies the expression builder works with real queries against actual data.
        """
        batch_id = str(uuid.uuid4())

        # Create entities with role and status attributes
        create_ops = [
            # admin + active
            CreateOp(
                payload=b"admin active",
                content_type=CONTENT_TYPE,
                attributes=Attributes(
                    {"batch_id": batch_id, "role": "admin", "status": "active"}
                ),
                expires_in=EXPIRES_IN,
            ),
            # admin + inactive
            CreateOp(
                payload=b"admin inactive",
                content_type=CONTENT_TYPE,
                attributes=Attributes(
                    {"batch_id": batch_id, "role": "admin", "status": "inactive"}
                ),
                expires_in=EXPIRES_IN,
            ),
            # moderator + active
            CreateOp(
                payload=b"moderator active",
                content_type=CONTENT_TYPE,
                attributes=Attributes(
                    {"batch_id": batch_id, "role": "moderator", "status": "active"}
                ),
                expires_in=EXPIRES_IN,
            ),
            # moderator + inactive
            CreateOp(
                payload=b"moderator inactive",
                content_type=CONTENT_TYPE,
                attributes=Attributes(
                    {"batch_id": batch_id, "role": "moderator", "status": "inactive"}
                ),
                expires_in=EXPIRES_IN,
            ),
            # user + active (should not match)
            CreateOp(
                payload=b"user active",
                content_type=CONTENT_TYPE,
                attributes=Attributes(
                    {"batch_id": batch_id, "role": "user", "status": "active"}
                ),
                expires_in=EXPIRES_IN,
            ),
        ]
        operations = Operations(creates=create_ops)
        arkiv_client_http.arkiv.execute(operations)

        # Build expression: (admin OR moderator) AND active
        batch_attr = StrAttr("batch_id")
        role = StrAttr("role")
        status = StrAttr("status")

        # Pattern from README: (role == "admin") | (role == "moderator") & (status == "active")
        # With proper parentheses for intended meaning: ((admin OR mod) AND active)
        expr = (
            (batch_attr == batch_id)
            & ((role == "admin") | (role == "moderator"))
            & (status == "active")
        )

        results = list(
            arkiv_client_http.arkiv.select(KEY, ATTRIBUTES).where(expr).fetch()
        )

        # Should match: admin+active, moderator+active (2 entities)
        assert len(results) == 2
        roles = {r.attributes["role"] for r in results if r.attributes}
        assert roles == {"admin", "moderator"}
        for result in results:
            assert result.attributes is not None
            assert result.attributes["status"] == "active"

    def test_where_with_not_expr(self, arkiv_client_http: Arkiv) -> None:
        """Test .where() with NOT expression pattern from README.

        Tests the pattern: (age >= 18) & ~(status == "banned")
        """
        batch_id = str(uuid.uuid4())

        # Create entities with age and status attributes
        create_ops = [
            # age 20, active (should match)
            CreateOp(
                payload=b"adult active",
                content_type=CONTENT_TYPE,
                attributes=Attributes(
                    {"batch_id": batch_id, "age": 20, "status": "active"}
                ),
                expires_in=EXPIRES_IN,
            ),
            # age 25, banned (should NOT match - banned)
            CreateOp(
                payload=b"adult banned",
                content_type=CONTENT_TYPE,
                attributes=Attributes(
                    {"batch_id": batch_id, "age": 25, "status": "banned"}
                ),
                expires_in=EXPIRES_IN,
            ),
            # age 15, active (should NOT match - under 18)
            CreateOp(
                payload=b"minor active",
                content_type=CONTENT_TYPE,
                attributes=Attributes(
                    {"batch_id": batch_id, "age": 15, "status": "active"}
                ),
                expires_in=EXPIRES_IN,
            ),
            # age 30, pending (should match)
            CreateOp(
                payload=b"adult pending",
                content_type=CONTENT_TYPE,
                attributes=Attributes(
                    {"batch_id": batch_id, "age": 30, "status": "pending"}
                ),
                expires_in=EXPIRES_IN,
            ),
        ]
        operations = Operations(creates=create_ops)
        arkiv_client_http.arkiv.execute(operations)

        # Build expression from README: (age >= 18) & ~(status == "banned")
        batch_attr = StrAttr("batch_id")
        age = IntAttr("age")
        status = StrAttr("status")

        expr = (batch_attr == batch_id) & (age >= 18) & ~(status == "banned")

        results = list(
            arkiv_client_http.arkiv.select(KEY, ATTRIBUTES).where(expr).fetch()
        )

        # Should match: age 20 active, age 30 pending (2 entities)
        assert len(results) == 2
        for result in results:
            assert result.attributes is not None
            assert result.attributes["age"] >= 18
            assert result.attributes["status"] != "banned"

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
