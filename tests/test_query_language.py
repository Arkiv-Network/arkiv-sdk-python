"""Tests for Arkiv query language syntax and operators."""

import logging
import uuid

from arkiv import Arkiv
from arkiv.types import ATTRIBUTES, KEY, CreateOp, Operations, QueryOptions

from .utils import to_create

OPTIONS = QueryOptions(fields=KEY | ATTRIBUTES, max_results_per_page=20)

logger = logging.getLogger(__name__)


def add_to_c(c: list[CreateOp], a):
    c.append(to_create(attributes=a))


def create_test_entities(client: Arkiv) -> tuple[str, list[str]]:
    """
    Create a batch of test entities with sequential numeric attributes.
    """
    batch = str(uuid.uuid4())

    # Build list of CreateOp operations
    c: list[CreateOp] = []
    add_to_c(c, {"batch": batch, "id": 1, "type": "A", "size": "xs", "idx": 1})
    add_to_c(c, {"batch": batch, "id": 2, "type": "A", "size": "s", "idx": 2})
    add_to_c(c, {"batch": batch, "id": 3, "type": "A", "size": "m", "idx": 3})
    add_to_c(c, {"batch": batch, "id": 4, "type": "A", "size": "l", "idx": 4})

    add_to_c(c, {"batch": batch, "id": 5, "type": "B", "size": "xs", "idx": 1})
    add_to_c(c, {"batch": batch, "id": 6, "type": "B", "size": "s", "idx": 2})
    add_to_c(c, {"batch": batch, "id": 7, "type": "B", "size": "m", "idx": 3})
    add_to_c(c, {"batch": batch, "id": 8, "type": "B", "size": "l", "idx": 4})

    add_to_c(c, {"batch": batch, "id": 9, "type": "C", "size": "xs", "idx": 1})
    add_to_c(c, {"batch": batch, "id": 10, "type": "C", "size": "s", "idx": 2})
    add_to_c(c, {"batch": batch, "id": 11, "type": "C", "size": "m", "idx": 3})
    add_to_c(c, {"batch": batch, "id": 12, "type": "C", "size": "l", "idx": 4})

    # Execute all creates in a single transaction
    operations = Operations(creates=c)
    receipt = client.arkiv.execute(operations)

    # Extract entity keys from receipt
    entity_keys = [create.key for create in receipt.creates]
    assert len(entity_keys) == 12

    return batch, entity_keys


def execute_query_test(
    client: Arkiv, label: str, query: str, expected_ids: list[int]
) -> None:
    """Execute a query and check result against expected ids."""

    # Create test entities
    batch, _ = create_test_entities(client)

    # Fetch all elements of batch
    query_base = f'batch = "{batch}"'
    if query == "":
        query_final = query_base
    else:
        query_final = f"{query_base} AND {query}"

    entities = list(client.arkiv.query_entities(query=query_final, options=OPTIONS))

    result_ids = [entity.attributes["id"] for entity in entities]
    assert set(result_ids) == set(expected_ids), (
        f"{label} failed. Expected: {expected_ids}, got: {result_ids}"
    )


class TestQueryLanguage:
    """Test query language syntax, operators, and expressions."""

    def test_query_language_full_batch(self, arkiv_client_http: Arkiv) -> None:
        """Test basic iteration over multiple pages of entities."""
        execute_query_test(arkiv_client_http, "Full Batch", "", list(range(1, 13)))

    # === AND Tests ===#
    def test_query_language_and_filter_type_a(self, arkiv_client_http: Arkiv) -> None:
        """Test query filtering for only type 'A' entities."""
        execute_query_test(
            arkiv_client_http, "Filter Type A", 'type = "A"', [1, 2, 3, 4]
        )

    def test_query_language_and_filter_idx_1(self, arkiv_client_http: Arkiv) -> None:
        """Test query filtering for only idx 1 entities."""
        execute_query_test(arkiv_client_http, "Filter Idx 1", "idx = 1", [1, 5, 9])

    def test_query_language_and_filter_type_b_idx_2(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test query filtering for type 'B' AND idx 2."""
        execute_query_test(
            arkiv_client_http, "Filter Type B & Idx 2", 'type = "B" AND idx = 2', [6]
        )

    # === OR Tests ===#
    def test_query_language_or_type_a_or_b(self, arkiv_client_http: Arkiv) -> None:
        """Test OR condition: type 'A' OR type 'B'."""
        execute_query_test(
            arkiv_client_http,
            "OR Type A or B",
            '(type = "A" OR type = "B")',
            [1, 2, 3, 4, 5, 6, 7, 8],
        )

    def test_query_language_or_idx_1_or_4(self, arkiv_client_http: Arkiv) -> None:
        """Test OR condition: idx 1 OR idx 4."""
        execute_query_test(
            arkiv_client_http,
            "OR Idx 1 or 4",
            "(idx = 1 OR idx = 4)",
            [1, 4, 5, 8, 9, 12],
        )

    def test_query_language_or_size_xs_or_l(self, arkiv_client_http: Arkiv) -> None:
        """Test OR condition: size 'xs' OR size 'l'."""
        execute_query_test(
            arkiv_client_http,
            "OR Size xs or l",
            '(size = "xs" OR size = "l")',
            [1, 4, 5, 8, 9, 12],
        )

    def test_query_language_or_two_conditions(self, arkiv_client_http: Arkiv) -> None:
        """Test multiple OR conditions: (type A OR type B) AND (idx 1 OR idx 2)."""
        execute_query_test(
            arkiv_client_http,
            "Two OR Conditions",
            '(type = "A" OR type = "B") AND (idx = 1 OR idx = 2)',
            [1, 2, 5, 6],
        )

    # === NOT Tests ===#
    def test_query_language_not_type_a_1(self, arkiv_client_http: Arkiv) -> None:
        """Test NOT condition: exclude type 'A' entities."""
        execute_query_test(
            arkiv_client_http,
            "NOT Type A (1)",
            'type != "A"',
            [5, 6, 7, 8, 9, 10, 11, 12],
        )

    def test_query_language_not_type_a_2(self, arkiv_client_http: Arkiv) -> None:
        """Test NOT condition: exclude type 'A' entities."""
        execute_query_test(
            arkiv_client_http,
            "NOT Type A (2)",
            'NOT (type = "A")',
            [5, 6, 7, 8, 9, 10, 11, 12],
        )

    def test_query_language_not_idx_1(self, arkiv_client_http: Arkiv) -> None:
        """Test NOT condition: exclude idx 1 entities."""
        execute_query_test(
            arkiv_client_http,
            "NOT Idx 1",
            "idx != 1",
            [2, 3, 4, 6, 7, 8, 10, 11, 12],
        )

    def test_query_language_not_with_and(self, arkiv_client_http: Arkiv) -> None:
        """Test NOT with AND: type 'A' but NOT idx 2."""
        execute_query_test(
            arkiv_client_http,
            "NOT with AND",
            'type = "A" AND idx != 2',
            [1, 3, 4],
        )

    def test_query_language_not_with_or(self, arkiv_client_http: Arkiv) -> None:
        """Test NOT with OR: exclude type 'A' OR type 'C'."""
        execute_query_test(
            arkiv_client_http,
            "NOT with OR",
            '(type != "A" AND type != "C")',
            [5, 6, 7, 8],
        )

    def test_query_language_not_multiple_conditions(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test multiple NOT conditions: exclude idx 1 AND exclude idx 4."""
        execute_query_test(
            arkiv_client_http,
            "Multiple NOT Conditions",
            "idx != 1 AND idx != 4",
            [2, 3, 6, 7, 10, 11],
        )

    # === Comparison Operators Tests ===#
    def test_query_language_greater_than(self, arkiv_client_http: Arkiv) -> None:
        """Test > operator: idx > 2."""
        execute_query_test(
            arkiv_client_http,
            "Greater Than idx > 2",
            "idx > 2",
            [3, 4, 7, 8, 11, 12],
        )

    def test_query_language_greater_than_or_equal(
        self, arkiv_client_http: Arkiv
    ) -> None:
        """Test >= operator: idx >= 3."""
        execute_query_test(
            arkiv_client_http,
            "Greater Than or Equal idx >= 3",
            "idx >= 3",
            [3, 4, 7, 8, 11, 12],
        )

    def test_query_language_less_than(self, arkiv_client_http: Arkiv) -> None:
        """Test < operator: idx < 3."""
        execute_query_test(
            arkiv_client_http,
            "Less Than idx < 3",
            "idx < 3",
            [1, 2, 5, 6, 9, 10],
        )

    def test_query_language_less_than_or_equal(self, arkiv_client_http: Arkiv) -> None:
        """Test <= operator: idx <= 2."""
        execute_query_test(
            arkiv_client_http,
            "Less Than or Equal idx <= 2",
            "idx <= 2",
            [1, 2, 5, 6, 9, 10],
        )

    def test_query_language_comparison_with_and(self, arkiv_client_http: Arkiv) -> None:
        """Test comparison with AND: type = 'A' AND idx > 2."""
        execute_query_test(
            arkiv_client_http,
            "Comparison with AND",
            'type = "A" AND idx > 2',
            [3, 4],
        )

    def test_query_language_comparison_range(self, arkiv_client_http: Arkiv) -> None:
        """Test range with comparison operators: idx >= 2 AND idx <= 3."""
        execute_query_test(
            arkiv_client_http,
            "Comparison Range idx 2-3",
            "idx >= 2 AND idx <= 3",
            [2, 3, 6, 7, 10, 11],
        )

    # === IN Tests ===#
    # @pytest.mark.xfail(reason="IN operator not yet supported by query parser")
    def test_query_language_in_type_list(self, arkiv_client_http: Arkiv) -> None:
        """Test IN condition: type in ('A', 'B')."""
        execute_query_test(
            arkiv_client_http,
            "IN Type A or B",
            'type IN ("A" "B")',
            [1, 2, 3, 4, 5, 6, 7, 8],
        )

    # @pytest.mark.xfail(reason="IN operator not yet supported by query parser")
    def test_query_language_in_idx_list(self, arkiv_client_http: Arkiv) -> None:
        """Test IN condition: idx in (1, 3, 4)."""
        execute_query_test(
            arkiv_client_http,
            "IN Idx 1, 3 or 4",
            "idx IN (1 3 4)",
            [1, 3, 4, 5, 7, 8, 9, 11, 12],
        )
