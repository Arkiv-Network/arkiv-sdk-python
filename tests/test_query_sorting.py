"""Tests for query result sorting and ordering."""

from arkiv import Arkiv
from arkiv.types import ASC, DESC, INT, STR, OrderByAttribute, QueryOptions

from .utils import create_test_entities


class TestQuerySorting:
    """Test sorting and ordering of query results."""

    def test_sort_type_ascending_default(self, arkiv_client_http: Arkiv) -> None:
        """Test sorting by type field in ascending order."""
        batch, _ = create_test_entities(arkiv_client_http)

        # Query all entities in batch, sorted by type ascending
        order_by = [OrderByAttribute(attribute="type", type=STR)]
        options = QueryOptions(order_by=order_by)
        results = list(
            arkiv_client_http.arkiv.query_entities(
                f'batch = "{batch}"', options=options
            )
        )

        # Should get: 4 type A, then 4 type B, then 4 type C
        assert len(results) == 12
        types = [r.attributes["type"] for r in results]
        assert types == ["A"] * 4 + ["B"] * 4 + ["C"] * 4

    def test_sort_type_ascending_explicit(self, arkiv_client_http: Arkiv) -> None:
        """Test sorting by type field in ascending order."""
        batch, _ = create_test_entities(arkiv_client_http)

        # Query all entities in batch, sorted by type ascending
        order_by = [OrderByAttribute(attribute="type", type=STR, direction=ASC)]
        options = QueryOptions(order_by=order_by)
        results = list(
            arkiv_client_http.arkiv.query_entities(
                f'batch = "{batch}"', options=options
            )
        )

        # Should get: 4 type A, then 4 type B, then 4 type C
        assert len(results) == 12
        types = [r.attributes["type"] for r in results]
        assert types == ["A"] * 4 + ["B"] * 4 + ["C"] * 4

    def test_sort_type_descending(self, arkiv_client_http: Arkiv) -> None:
        """Test sorting by type field in descending order."""
        batch, _ = create_test_entities(arkiv_client_http)

        # Query all entities in batch, sorted by type descending
        order_by = [OrderByAttribute(attribute="type", type=STR, direction=DESC)]
        options = QueryOptions(order_by=order_by)
        results = list(
            arkiv_client_http.arkiv.query_entities(
                f'batch = "{batch}"', options=options
            )
        )

        # Should get: 4 type C, then 4 type B, then 4 type A
        assert len(results) == 12
        types = [r.attributes["type"] for r in results]
        assert types == ["C"] * 4 + ["B"] * 4 + ["A"] * 4

    def test_sort_idx_ascending(self, arkiv_client_http: Arkiv) -> None:
        """Test sorting by idx field in ascending order."""
        batch, _ = create_test_entities(arkiv_client_http)

        # Query all entities in batch, sorted by idx ascending
        order_by = [OrderByAttribute(attribute="idx", type=INT)]
        options = QueryOptions(order_by=order_by)
        results = list(
            arkiv_client_http.arkiv.query_entities(
                f'batch = "{batch}"', options=options
            )
        )

        # Should get: 3 idx=1, then 3 idx=2, then 3 idx=3, then 3 idx=4
        assert len(results) == 12
        idxs = [int(r.attributes["idx"]) for r in results]
        assert idxs == [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4]

    def test_sort_idx_descending(self, arkiv_client_http: Arkiv) -> None:
        """Test sorting by idx field in descending order."""
        batch, _ = create_test_entities(arkiv_client_http)

        # Query all entities in batch, sorted by idx descending
        order_by = [OrderByAttribute(attribute="idx", type=INT, direction=DESC)]
        options = QueryOptions(order_by=order_by)
        results = list(
            arkiv_client_http.arkiv.query_entities(
                f'batch = "{batch}"', options=options
            )
        )

        # Should get: 3 idx=4, then 3 idx=3, then 3 idx=2, then 3 idx=1
        assert len(results) == 12
        idxs = [int(r.attributes["idx"]) for r in results]
        assert idxs == [4, 4, 4, 3, 3, 3, 2, 2, 2, 1, 1, 1]

    def test_sort_multi_field(self, arkiv_client_http: Arkiv) -> None:
        """Test multi-field sorting: idx ascending, then type descending."""
        batch, _ = create_test_entities(arkiv_client_http)

        # Query all entities in batch, sorted by idx ascending, then type descending
        order_by = [
            OrderByAttribute(attribute="idx", type=INT),
            OrderByAttribute(attribute="type", type=STR, direction=DESC),
        ]
        options = QueryOptions(order_by=order_by)
        results = list(
            arkiv_client_http.arkiv.query_entities(
                f'batch = "{batch}"', options=options
            )
        )

        # Should get: idx=1 (C, B, A), idx=2 (C, B, A), idx=3 (C, B, A), idx=4 (C, B, A)
        assert len(results) == 12
        ids = [int(r.attributes["id"]) for r in results]
        assert ids == [9, 5, 1, 10, 6, 2, 11, 7, 3, 12, 8, 4]

    def test_sort_three_fields(self, arkiv_client_http: Arkiv) -> None:
        """Test three-field sorting: type asc, size asc, idx desc."""
        batch, _ = create_test_entities(arkiv_client_http)

        # Query all entities in batch with three-level sort
        order_by = [
            OrderByAttribute(attribute="type", type=STR),
            OrderByAttribute(attribute="size", type=STR),
            OrderByAttribute(attribute="idx", type=INT, direction=DESC),
        ]
        options = QueryOptions(order_by=order_by)
        results = list(
            arkiv_client_http.arkiv.query_entities(
                f'batch = "{batch}"', options=options
            )
        )

        # Expected: Type A (l, m, s, xs), Type B (l, m, s, xs), Type C (l, m, s, xs)
        # But for same type+size, idx descending
        # Type A: size=l(idx=4,id=4), size=m(idx=3,id=3), size=s(idx=2,id=2), size=xs(idx=1,id=1)
        # Type B: size=l(idx=4,id=8), size=m(idx=3,id=7), size=s(idx=2,id=6), size=xs(idx=1,id=5)
        # Type C: size=l(idx=4,id=12), size=m(idx=3,id=11), size=s(idx=2,id=10), size=xs(idx=1,id=9)
        assert len(results) == 12
        ids = [int(r.attributes["id"]) for r in results]
        assert ids == [4, 3, 2, 1, 8, 7, 6, 5, 12, 11, 10, 9]

    def test_sort_with_filter(self, arkiv_client_http: Arkiv) -> None:
        """Test sorting combined with query filter."""
        batch, _ = create_test_entities(arkiv_client_http)

        # Query for type A or B only, sorted by idx descending, then type ascending
        order_by = [
            OrderByAttribute(attribute="idx", type=INT, direction=DESC),
            OrderByAttribute(attribute="type", type=STR),
        ]
        options = QueryOptions(order_by=order_by)
        results = list(
            arkiv_client_http.arkiv.query_entities(
                f'batch = "{batch}" AND (type = "A" OR type = "B")', options=options
            )
        )

        # Should get 8 results: idx=4 (A,B), idx=3 (A,B), idx=2 (A,B), idx=1 (A,B)
        # IDs: 4, 8, 3, 7, 2, 6, 1, 5
        assert len(results) == 8
        ids = [int(r.attributes["id"]) for r in results]
        assert ids == [4, 8, 3, 7, 2, 6, 1, 5]

    def test_sort_with_pagination(self, arkiv_client_http: Arkiv) -> None:
        """Test sorting consistency across multiple pages."""
        batch, _ = create_test_entities(arkiv_client_http)

        # Sort by type desc, size asc, idx asc with small page size to force pagination
        order_by = [
            OrderByAttribute(attribute="type", type=STR),
            OrderByAttribute(attribute="size", type=STR),
            OrderByAttribute(attribute="idx", type=INT, direction=DESC),
        ]
        options = QueryOptions(order_by=order_by, max_results_per_page=3)

        # Collect all results across pages using the iterator
        results = list(
            arkiv_client_http.arkiv.query_entities(
                f'batch = "{batch}"', options=options
            )
        )

        # Expected: Type A (l, m, s, xs), Type B (l, m, s, xs), Type C (l, m, s, xs)
        # But for same type+size, idx descending
        # The iterator should have fetched 4 pages (3+3+3+3)
        assert len(results) == 12
        ids = [int(r.attributes["id"]) for r in results]
        assert ids == [4, 3, 2, 1, 8, 7, 6, 5, 12, 11, 10, 9]
