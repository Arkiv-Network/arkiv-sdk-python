# Fluent Query API Proposal

## Overview

A type-safe, fluent query builder API inspired by JOOQ that provides an intuitive, SQL-like interface for constructing Arkiv queries. The API follows the builder pattern and allows for method chaining to construct complex queries.

## Design Goals

1. **Simplicity**: WHERE clauses can be plain SQL-like strings OR composable expressions
2. **SQL Familiarity**: Follow SQL query patterns (SELECT, WHERE, ORDER BY, etc.)
3. **Type Safety**: Use typed attribute classes for ORDER BY and optional WHERE expressions
4. **Readability**: Clear, self-documenting code that matches SQL structure
5. **Backward Compatibility**: Coexist with existing string-based query API
6. **Transparency**: Query strings are passed directly to Arkiv node

## Core API Design

Parts and descriptions
- `.select(...)` **(mandatory)** starts the query chain; feeds into "fields" bitmask of QueryOptions. Empty `.select()` means "all fields"
- `.where(...)` feeds into "query" parameter of query_entities (accepts string OR expression)
- `.order_by(...)` (optional) feeds into "order_by" field of QueryOptions of query_entities
- `.limit(n)` (optional) limits total results returned; feeds into "max_results" field of QueryOptions
- `.at_block(...)` (optional) feeds into "at_block" field of QueryOptions of query_entities
- `.fetch()` returns the QueryIterator from query_entities
- `.count()` optimized to retrieve only entity keys, count them, and return an int

**Note**: `.select()` is always required to start a query chain, similar to SQL requiring `SELECT`.

### Field Selection

Arkiv supports selection of entity field groups (not individual user-defined attributes):
- **Metadata fields**: `KEY`, `OWNER`, `CREATED_AT`, `LAST_MODIFIED_AT`, `EXPIRES_AT`, `TX_INDEX_IN_BLOCK`, `OP_INDEX_IN_TX`
- **Content fields**: `PAYLOAD`, `CONTENT_TYPE`
- **Attributes**: `ATTRIBUTES` (all user-defined attributes - cannot select individual ones)

The `.select()` method accepts a list of these field constants:

### Basic Query Structure

```python
from arkiv import Arkiv, IntSort, StrSort
from arkiv.types import KEY, OWNER, ATTRIBUTES, PAYLOAD, CONTENT_TYPE

client = Arkiv()

# Simple query - WHERE clause is a plain SQL-like string
# Select specific field groups (no brackets needed)
results = client.arkiv \
    .select(KEY, ATTRIBUTES) \
    .where('type = "user"') \
    .fetch()

# Select all fields - empty select() means "all fields"
results = client.arkiv \
    .select() \
    .where('type = "user" AND age >= 18') \
    .fetch()

# Select multiple field groups
results = client.arkiv \
    .select(KEY, OWNER, ATTRIBUTES, PAYLOAD, CONTENT_TYPE) \
    .where('status = "active"') \
    .fetch()

# Select single field
results = client.arkiv \
    .select(KEY) \
    .where('type = "user"') \
    .fetch()

# Complex conditions with OR and parentheses
results = client.arkiv \
    .select() \
    .where('(type = "user" OR type = "admin") AND status != "banned"') \
    .fetch()

# Count matching entities (select() required but fields ignored)
count = client.arkiv \
    .select() \
    .where('type = "user"') \
    .count()
```

**Key Points**:
- `.select()` is **mandatory** to start a query chain (like SQL's `SELECT`)
- `.select()` with no arguments means "all fields"
- `.where()` takes a plain string with SQL-like syntax that is passed directly to the Arkiv node
- Arkiv returns all user-defined attributes or none - cannot select specific attributes like `type` or `age`
- Field groups: `KEY`, `OWNER`, `ATTRIBUTES`, `PAYLOAD`, `CONTENT_TYPE`, etc.
- For sorting: use `IntSort` for numeric fields, `StrSort` for string fields

### Sorting

Sorting uses type-specific sort classes (`IntSort` for numeric, `StrSort` for string):

```python
from arkiv import IntSort, StrSort, ASC, DESC

# Single field sorting
results = client.arkiv \
    .select() \
    .where('type = "user"') \
    .order_by(IntSort('age', DESC)) \
    .fetch()

# Multiple field sorting - no brackets needed
results = client.arkiv \
    .select() \
    .where('type = "user"') \
    .order_by(
        StrSort('status'),          # String, ascending (default)
        IntSort('age', DESC)        # Numeric, descending
    ) \
    .fetch()

# Ascending is default, so direction can be omitted
results = client.arkiv \
    .select() \
    .where('status = "active"') \
    .order_by(
        IntSort('priority', DESC),  # Descending - explicit
        StrSort('name')             # Ascending - default
    ) \
    .fetch()

# Alternative: Method chaining for direction
results = client.arkiv \
    .select() \
    .where('type = "user"') \
    .order_by(
        StrSort('status').asc(),
        IntSort('age').desc()
    ) \
    .fetch()
```

**Why type-specific classes are valuable:**
- **Explicit type**: `IntSort` vs `StrSort` - immediately clear from class name
- **Required for sorting**: Arkiv needs to know if attribute is string or numeric
- **IDE support**: Type system knows what's available for each class
- **Prevents errors**: Can't accidentally use wrong type
- **Default direction**: ASC is default, only specify DESC when needed

### Result Limiting

Use `.limit(n)` to restrict the total number of entities returned across all pages. This is useful for:
- Preventing accidentally fetching millions of entities
- "Top N" queries (e.g., "10 most recent users")
- Pagination at the application level

```python
# Get first 10 matching entities
results = client.arkiv \
    .select() \
    .where('type = "user"') \
    .limit(10) \
    .fetch()

# Top 5 users by age
results = client.arkiv \
    .select() \
    .where('type = "user" AND status = "active"') \
    .order_by(IntSort('age', DESC)) \
    .limit(5) \
    .fetch()

# Combine with other options
results = client.arkiv \
    .select(KEY, ATTRIBUTES) \
    .where('status = "active"') \
    .order_by(StrSort('name')) \
    .limit(100) \
    .at_block(12345) \
    .fetch()
```

**Implementation details:**
- `.limit(n)` sets `max_results` in `QueryOptions`
- The iterator stops after yielding `n` entities, even if more pages exist
- Internally optimizes `max_results_per_page` to avoid fetching unnecessary data
- `None` (default) means unlimited - fetch all matching entities
- **Prevents errors**: Can't accidentally use wrong type
- **Default direction**: ASC is default, only specify DESC when needed

## Expression Builder (Type-Safe WHERE Clauses)

While string-based WHERE clauses are simple and familiar, the SDK also provides an **expression builder** for type-safe, composable filter expressions. This is useful when:
- Building queries programmatically from user input
- Wanting compile-time/runtime type checking
- Composing complex conditions from reusable parts

### Expression Classes

Two attribute classes for building WHERE expressions:

```python
from arkiv.query_builder import IntAttr, StrAttr
```

- `IntAttr(name)` - For integer/numeric attributes
- `StrAttr(name)` - For string attributes

### Comparison Operators

Both classes support standard comparison operators that return `Expr` objects:

```python
# Integer comparisons
IntAttr("age") == 18        # age = 18
IntAttr("age") != 18        # age != 18
IntAttr("age") > 18         # age > 18
IntAttr("age") >= 18        # age >= 18
IntAttr("age") < 65         # age < 65
IntAttr("age") <= 65        # age <= 65

# String comparisons
StrAttr("status") == "active"    # status = "active"
StrAttr("status") != "banned"    # status != "banned"
StrAttr("name") > "A"            # name > "A" (lexicographic)
StrAttr("name") >= "A"           # name >= "A"
StrAttr("name") < "Z"            # name < "Z"
StrAttr("name") <= "Z"           # name <= "Z"
```

### Type Safety

The expression builder provides **runtime type checking** to catch errors early:

```python
# ✓ Correct - comparing int attribute to int value
IntAttr("age") >= 18

# ✗ TypeError - comparing int attribute to string value
IntAttr("age") == "18"  # Raises TypeError: IntAttr 'age' requires int, got str

# ✓ Correct - comparing string attribute to string value
StrAttr("status") == "active"

# ✗ TypeError - comparing string attribute to int value
StrAttr("status") == 1  # Raises TypeError: StrAttr 'status' requires str, got int
```

### Combining Expressions with `&`, `|`, and `~`

Expressions can be combined using `&` (AND), `|` (OR), and `~` (NOT) operators:

```python
from arkiv.query_builder import IntAttr, StrAttr

age = IntAttr("age")
status = StrAttr("status")
role = StrAttr("role")

# AND conditions
expr = (age >= 18) & (status == "active")
# Generates: age >= 18 AND status = "active"

# OR conditions
expr = (role == "admin") | (role == "moderator")
# Generates: role = "admin" OR role = "moderator"

# NOT conditions
expr = ~(status == "banned")
# Generates: NOT (status = "banned")

expr = ~(role == "guest")
# Generates: NOT (role = "guest")

# Complex nested conditions
expr = ((role == "admin") | (role == "moderator")) & (status == "active")
# Generates: (role = "admin" OR role = "moderator") AND status = "active"

# NOT with AND/OR
expr = (age >= 18) & ~(status == "banned")
# Generates: age >= 18 AND NOT (status = "banned")

expr = ~((role == "guest") | (status == "inactive"))
# Generates: NOT (role = "guest" OR status = "inactive")

# Mixed with multiple attributes
expr = (age >= 18) & (age < 65) & (status != "banned")
# Generates: age >= 18 AND age < 65 AND status != "banned"
```

### Operator Precedence

The operators follow Python's precedence rules (tightest to loosest):

| Precedence | Operator | Meaning |
|------------|----------|---------|
| 1 (tightest) | `~` | NOT |
| 2 | `&` | AND |
| 3 (loosest) | `|` | OR |

This matches standard logical operator precedence:

```python
# This expression:
~a & b | c

# Is parsed by Python as:
((~a) & b) | c

# Which generates:
(NOT a AND b) OR c
```

**Important**: Comparison operators (`==`, `>=`, etc.) have **lower** precedence than `&`, `|`, `~`. Always use parentheses around comparisons:

```python
# ✗ Wrong - Python parses this incorrectly
age >= 18 & status == "active"  # Parsed as: age >= (18 & status) == "active"

# ✓ Correct - parentheses required
(age >= 18) & (status == "active")
```

### Using Expressions in Queries

Pass expressions directly to `.where()`:

```python
from arkiv import Arkiv, IntSort
from arkiv.query_builder import IntAttr, StrAttr

client = Arkiv()

# Define reusable attribute references
age = IntAttr("age")
status = StrAttr("status")
role = StrAttr("role")

# Simple expression
results = client.arkiv \
    .select() \
    .where(status == "active") \
    .fetch()

# Combined expression
results = client.arkiv \
    .select() \
    .where((age >= 18) & (status == "active")) \
    .order_by(IntSort("age", DESC)) \
    .fetch()

# Complex expression with OR
admin_or_mod = (role == "admin") | (role == "moderator")
active_staff = admin_or_mod & (status == "active")

results = client.arkiv \
    .select() \
    .where(active_staff) \
    .fetch()
```

### Programmatic Query Building

The expression builder shines when building queries dynamically:

```python
from arkiv.query_builder import IntAttr, StrAttr, Expr

def build_user_filter(
    min_age: int | None = None,
    max_age: int | None = None,
    status: str | None = None,
    roles: list[str] | None = None,
) -> Expr | None:
    """Build a filter expression from optional criteria."""
    conditions: list[Expr] = []

    age = IntAttr("age")
    if min_age is not None:
        conditions.append(age >= min_age)
    if max_age is not None:
        conditions.append(age <= max_age)

    if status is not None:
        conditions.append(StrAttr("status") == status)

    if roles:
        role_attr = StrAttr("role")
        role_conditions = [role_attr == r for r in roles]
        # Combine with OR: role = "admin" OR role = "mod" OR ...
        role_expr = role_conditions[0]
        for rc in role_conditions[1:]:
            role_expr = role_expr | rc
        conditions.append(role_expr)

    if not conditions:
        return None

    # Combine all conditions with AND
    result = conditions[0]
    for c in conditions[1:]:
        result = result & c
    return result

# Usage
expr = build_user_filter(min_age=18, status="active", roles=["admin", "mod"])
results = client.arkiv.select().where(expr).fetch()
```

### String vs Expression: When to Use Each

| Use Case | Recommended Approach |
|----------|---------------------|
| Static, simple queries | String: `'type = "user"'` |
| Complex static queries | String: `'(a OR b) AND c'` |
| Dynamic query building | Expression builder |
| User input filtering | Expression builder (type-safe) |
| Reusable query components | Expression builder |
| Quick prototyping | String |

Both approaches can be mixed - use what's clearest for your use case.

## Class Summary

| Class | Purpose | Example |
|-------|---------|---------|
| `IntSort` | ORDER BY for integer attributes | `IntSort("age", DESC)` |
| `StrSort` | ORDER BY for string attributes | `StrSort("name")` |
| `IntAttr` | WHERE expressions for integers | `IntAttr("age") >= 18` |
| `StrAttr` | WHERE expressions for strings | `StrAttr("status") == "active"` |
| `Expr` | Combined expression (returned by operators) | `(a >= 1) & (b == "x")`, `~(a == 1)` |

**Operators on `Expr`**:
- `&` - AND: `(a >= 1) & (b == "x")`
- `|` - OR: `(a == 1) | (a == 2)`
- `~` - NOT: `~(a == 1)`

**Methods on `Expr`**:
- `to_sql()` - Returns the SQL string representation of the expression

```python
expr = (IntAttr("age") >= 18) & (StrAttr("status") == "active")
expr.to_sql()  # Returns: 'age >= 18 AND status = "active"'

expr = ~(StrAttr("role") == "guest")
expr.to_sql()  # Returns: 'NOT (role = "guest")'
```

## Implementation Architecture

### Core Classes


## Migration Strategy

The fluent API coexists with the existing string-based API:

```python
from arkiv import Arkiv, IntSort, StrSort, DESC
from arkiv.query_builder import IntAttr, StrAttr
from arkiv.types import KEY, ATTRIBUTES

client = Arkiv()

# Existing API - still supported
results = list(client.arkiv.query_entities('type = "user" AND age >= 18'))

# New fluent API - select() is mandatory entry point
results = client.arkiv \
    .select() \
    .where('type = "user" AND age >= 18') \
    .fetch()

# With field selection
results = client.arkiv \
    .select(KEY, ATTRIBUTES) \
    .where('type = "user"') \
    .fetch()

# With sorting
results = client.arkiv \
    .select(KEY, ATTRIBUTES) \
    .where('type = "user" AND age >= 18') \
    .order_by(
        StrSort('status'),
        IntSort('age', DESC)
    ) \
    .fetch()

# With expression builder instead of string
age = IntAttr("age")
status = StrAttr("status")

results = client.arkiv \
    .select(KEY, ATTRIBUTES) \
    .where((age >= 18) & (status == "active")) \
    .order_by(IntSort('age', DESC)) \
    .fetch()

# With block pinning
results = client.arkiv \
    .select(KEY, ATTRIBUTES) \
    .where('status = "active"') \
    .at_block(12345) \
    .fetch()

# With result limiting - get top 10
results = client.arkiv \
    .select() \
    .where('type = "user"') \
    .order_by(IntSort('age', DESC)) \
    .limit(10) \
    .fetch()

# Quick count (select() required, but fields ignored)
count = client.arkiv \
    .select() \
    .where('type = "user"') \
    .count()
```

**Key differences**: The fluent API provides a cleaner interface for:
- **Field selection**: `.select(KEY, ATTRIBUTES)` instead of bitmask `KEY | ATTRIBUTES`
- **Sorting**: `.order_by()` with type-specific classes `IntSort`, `StrSort`
- **Type-safe filters**: Expression builder with `IntAttr`, `StrAttr` (optional)
- **Result limiting**: `.limit(n)` to cap total results (safety + "top N" queries)
- **Block pinning**: `.at_block()` for historical queries
- **Counting**: `.count()` convenience method
- **Iteration**: Returns same iterator, but building the query is more readable

**Note**: Both `.select()` and `.order_by()` use Python's `*args` so no brackets needed:
- `.select(KEY, ATTRIBUTES)` not `.select([KEY, ATTRIBUTES])`
- `.order_by(StrSort('name'), IntSort('age', DESC))` not `.order_by([...])`

## Benefits

1. **Simplicity**: WHERE clauses can use familiar SQL syntax OR type-safe expressions
2. **Readability**: Self-documenting code that reads like SQL
3. **Type Safety**: `IntSort`/`StrSort` for ORDER BY, `IntAttr`/`StrAttr` for WHERE
4. **Runtime Checking**: Expression builder catches type mismatches (e.g., `IntAttr("age") == "18"`)
5. **Composability**: Build queries programmatically with method chaining and `&`/`|` operators
6. **Transparency**: Query strings are passed directly to node - what you see is what you get
7. **Flexibility**: Choose string or expression approach based on use case
8. **Safety**: `.limit(n)` prevents accidentally fetching all entities
9. **Testability**: Easy to test query building separately from execution

## Open Questions

1. **Error Messages**: How to provide clear error messages when query construction fails?

2. **Performance**: Overhead of building query objects vs. direct string construction?

## TODO

### Missing Tests

The following fluent API methods need functional tests (beyond method chaining tests):

- **`.at_block(n)`** - Test that queries are actually pinned to a specific block number
- **`.limit(n)`** - Test that iteration stops after `n` entities across pages
- **`.max_page_size(n)`** - Test that page size is correctly applied to RPC calls
