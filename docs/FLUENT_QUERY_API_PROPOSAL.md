# Fluent Query API Proposal

## Overview

A type-safe, fluent query builder API inspired by JOOQ that provides an intuitive, SQL-like interface for constructing Arkiv queries. The API follows the builder pattern and allows for method chaining to construct complex queries.

## Design Goals

1. **Simplicity**: WHERE clauses are plain SQL-like strings - no magic, no operator overloading
2. **SQL Familiarity**: Follow SQL query patterns (SELECT, WHERE, ORDER BY, etc.)
3. **Type Safety**: Use `Attribute()` objects for ORDER BY to specify type and direction
4. **Readability**: Clear, self-documenting code that matches SQL structure
5. **Backward Compatibility**: Coexist with existing string-based query API
6. **Transparency**: Query strings are passed directly to Arkiv node

## Core API Design

Parts and descriptions
- `.select(...)` feeds into "fields" bitmask of QueryOptions of query_entities
- `.where(...)` feeds into "query" parameter of query_entities
- `.order_by(...)` (optional) feeds into "order_by" field of QueryOptions of query_entities
- `.at_block(...)` (optional) feeds into "at_block" field of QueryOptions of query_entities
- `.fetch()` returns the QueryIterator from query_entities
- `.count()` optimized to retrieve only entity keys, count them, and return an int

### Field Selection

Arkiv supports selection of entity field groups (not individual user-defined attributes):
- **Metadata fields**: `KEY`, `OWNER`, `CREATED_AT`, `LAST_MODIFIED_AT`, `EXPIRES_AT`, `TX_INDEX_IN_BLOCK`, `OP_INDEX_IN_TX`
- **Content fields**: `PAYLOAD`, `CONTENT_TYPE`
- **Attributes**: `ATTRIBUTES` (all user-defined attributes - cannot select individual ones)

The `.select()` method accepts a list of these field constants:

### Basic Query Structure

```python
from arkiv import Arkiv
from arkiv.query import IntAttribute, StrAttribute
from arkiv.types import KEY, OWNER, ATTRIBUTES, PAYLOAD, CONTENT_TYPE

client = Arkiv()

# Simple query - WHERE clause is a plain SQL-like string
# Select specific field groups (no brackets needed)
results = client.arkiv \
    .select(KEY, ATTRIBUTES) \
    .where('type = "user"') \
    .fetch()

# Select all fields ( .select() defaults to all fields)
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
    .where('(type = "user" OR type = "admin") AND status != "banned"') \
    .fetch()

# Count matching entities (ignores .select())
count = client.arkiv \
    .where('type = "user"') \
    .count()
```

**Key Points**:
- `.where()` takes a plain string with SQL-like syntax that is passed directly to the Arkiv node
- `.select()` accepts field group constants as arguments (not individual attribute names)
- Arkiv returns all user-defined attributes or none - cannot select specific attributes like `type` or `age`
- Field groups: `KEY`, `OWNER`, `ATTRIBUTES`, `PAYLOAD`, `CONTENT_TYPE`, etc.
- For sorting: use `IntAttribute` for numeric fields, `StrAttribute` for string fields

### Sorting

Sorting uses type-specific attribute classes (`IntAttribute` for numeric, `StrAttribute` for string):

```python
from arkiv.query import IntAttribute, StrAttribute
from arkiv import ASC, DESC

# Single field sorting
results = client.arkiv \
    .select() \
    .where('type = "user"') \
    .order_by(IntAttribute('age', DESC)) \
    .fetch()

# Multiple field sorting - no brackets needed
results = client.arkiv \
    .select() \
    .where('type = "user"') \
    .order_by(
        StrAttribute('status'),          # String, ascending (default)
        IntAttribute('age', DESC)        # Numeric, descending
    ) \
    .fetch()

# Ascending is default, so direction can be omitted
results = client.arkiv \
    .select() \
    .where('status = "active"') \
    .order_by(
        IntAttribute('priority', DESC),  # Descending - explicit
        StrAttribute('name')             # Ascending - default
    ) \
    .fetch()

# Alternative: Method chaining for direction
results = client.arkiv \
    .select() \
    .where('type = "user"') \
    .order_by(
        StrAttribute('status').asc(),
        IntAttribute('age').desc()
    ) \
    .fetch()
```

**Why type-specific classes are valuable:**
- **Explicit type**: `IntAttribute` vs `StrAttribute` - immediately clear from class name
- **Required for sorting**: Arkiv needs to know if attribute is string or numeric
- **IDE support**: Type system knows what's available for each class
- **Prevents errors**: Can't accidentally use wrong type
- **Default direction**: ASC is default, only specify DESC when needed

## Implementation Architecture

### Core Classes


## Migration Strategy

The fluent API would coexist with the existing string-based API:

```python
from arkiv.types import KEY, ATTRIBUTES

# Existing API - still supported
results = list(client.arkiv.query_entities('type = "user" AND age >= 18'))

# New fluent API - same query string, cleaner interface
results = client.arkiv \
    .where('type = "user" AND age >= 18') \
    .fetch()

# With field selection
results = client.arkiv \
    .select(KEY, ATTRIBUTES) \
    .where('type = "user"') \
    .fetch()

# With sorting (new capability made easy)
from arkiv.query import IntAttribute, StrAttribute

results = client.arkiv \
    .select(KEY, ATTRIBUTES) \
    .where('type = "user" AND age >= 18') \
    .order_by(
        StrAttribute('status'),
        IntAttribute('age', DESC)
    ) \
    .fetch()

# With block pinning
results = client.arkiv \
    .select(KEY, ATTRIBUTES) \
    .where('status = "active"') \
    .at_block(12345) \
    .fetch()

# Quick count
count = client.arkiv \
    .where('type = "user"') \
    .count()
```

**Key differences**: The fluent API provides a cleaner interface for:
- **Field selection**: `.select(KEY, ATTRIBUTES)` instead of bitmask `KEY | ATTRIBUTES`
- **Sorting**: `.order_by()` with type-specific classes `IntAttribute`, `StrAttribute`
- **Block pinning**: `.at_block()` for historical queries
- **Counting**: `.count()` convenience method
- **Iteration**: Returns same iterator, but building the query is more readable

While keeping the WHERE clause simple and familiar (plain SQL-like strings).

**Note**: Both `.select()` and `.order_by()` use Python's `*args` so no brackets needed:
- `.select(KEY, ATTRIBUTES)` not `.select([KEY, ATTRIBUTES])`
- `.order_by(StrAttribute('name'), IntAttribute('age', DESC))` not `.order_by([...])`

## Benefits

1. **Simplicity**: WHERE clauses use familiar SQL syntax - no learning curve
2. **Readability**: Self-documenting code that reads like SQL
3. **Type Safety**: `Attribute()` for ORDER BY provides IDE autocomplete and type checking
4. **Composability**: Build queries programmatically with method chaining
5. **Transparency**: Query strings are passed directly to node - what you see is what you get
6. **Flexibility**: List-based field selection is clearer than bitmask operations
7. **Testability**: Easy to test query building separately from execution

## Open Questions

1. **Error Messages**: How to provide clear error messages when query construction fails?

2. **Performance**: Overhead of building query objects vs. direct string construction?
