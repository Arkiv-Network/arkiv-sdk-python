# Arkiv SDK

Arkiv is a permissioned storage system for decentralized apps, supporting flexible entities with binary data, attributes, and metadata.

The Arkiv SDK is the official Python library for interacting with Arkiv networks. It offers a type-safe, developer-friendly API for managing entities, querying data, subscribing to events, and offchain verification—ideal for both rapid prototyping and production use.

## Architecture

Principles:
- The SDK is based on a modern and stable client library.
- The SDK should feel like "Library + Entities"

As underlying library we use [Web3.py](https://github.com/ethereum/web3.py) (no good alternatives for Python).


### Arkiv Client

The Arkiv SDK should feel like "web3.py + entities", maintaining the familiar developer experience that Python web3 developers expect.

A `client.arkiv.*` approach is in line with web3.py's module pattern.
It clearly communicates that arkiv is a module extension just like eth, net, etc.

## Hello World

### Synchronous API
Here's a "Hello World!" example showing how to use the Python Arkiv SDK:

```python
from arkiv import Arkiv

# Create Arkiv client with default settings:
# - starting and connecting to a containerized Arkiv node
# - creating a funded default account
client = Arkiv()
print(f"Client: {client}, connected: {client.is_connected()}")
print(f"Account: {client.eth.default_account}")
print(f"Balance: {client.from_wei(client.eth.get_balance(client.eth.default_account), 'ether')} ETH")

# Create entity with data and attributes
entity_key, receipt = client.arkiv.create_entity(
    payload = b"Hello World!",
    content_type = "text/plain",
    attributes = {"type": "greeting", "version": 1},
    expires_in = client.arkiv.to_seconds(days=1)
)

# Get individual entity and print its details
entity = client.arkiv.get_entity(entity_key)
print(f"Creation TX: {receipt.tx_hash}")
print(f"Entity: {entity}")
```

### Asynchronous API
For async/await support, use `AsyncArkiv`:

```python
import asyncio
from arkiv import AsyncArkiv

async def main():
    # Create async client with default settings
    async with AsyncArkiv() as client:
        # Create entity with data and attributes
        entity_key, tx_hash = await client.arkiv.create_entity(
            payload = b"Hello Async World!",
            content_type = "text/plain",
            attributes = {"type": "greeting", "version": 1},
            expires_in = client.arkiv.to_seconds(days=1)
        )

        # Get entity and check existence
        entity = await client.arkiv.get_entity(entity_key)
        exists = await client.arkiv.entity_exists(entity_key)

asyncio.run(main())
```

### Web3 Standard Support
```python
from web3 import HTTPProvider
provider = HTTPProvider('https://mendoza.hoodi.arkiv.network/rpc')

# Arkiv 'is a' Web3 client
client = Arkiv(provider)
balance = client.eth.get_balance(client.eth.default_account)
tx = client.eth.get_transaction(tx_hash)
```

### Entity Operations

Beyond creating and reading entities, Arkiv supports updating, extending, transferring ownership, and deleting entities.

#### Update Entity

Modify an entity's payload, attributes, or expiration:

```python
# Update entity with new payload and attributes
entity_key, receipt = client.arkiv.update_entity(
    entity_key,
    payload=b"Updated content",
    attributes={"type": "greeting", "version": 2},
    expires_in=client.arkiv.to_seconds(days=7)
)
```

#### Extend Entity Lifetime

Extend an entity's expiration without modifying its content:

```python
# Extend entity lifetime by 30 days
entity_key, receipt = client.arkiv.extend_entity(
    entity_key,
    extend_by=client.arkiv.to_seconds(days=30)
)
```

#### Change Entity Owner

Transfer ownership of an entity to another address:

```python
# Transfer entity to a new owner
new_owner = "0x1234567890abcdef1234567890abcdef12345678"
entity_key, receipt = client.arkiv.change_owner(entity_key, new_owner)
```

#### Delete Entity

Permanently remove an entity (only the owner can delete):

```python
# Delete entity
receipt = client.arkiv.delete_entity(entity_key)
```

## Advanced Features

### Query Builder

The query builder provides a clean, chainable API for querying entities. It wraps the lower-level `query_entities` method with a SQL-like interface.

#### Basic Usage

```python
from arkiv import Arkiv, StrAttr
from arkiv.types import KEY, ATTRIBUTES

client = Arkiv()

# Define typed attributes
entity_type = StrAttr("type")
status = StrAttr("status")

# Simple query - select all fields
results = client.arkiv.select().where(entity_type == "user").fetch()
for entity in results:
    print(f"Entity: {entity.key}")

# Select specific fields
results = client.arkiv.select(KEY, ATTRIBUTES).where(status == "active").fetch()

# Count matching entities
count = client.arkiv.select().where(entity_type == "user").count()
print(f"Found {count} users")
```

#### Expressions with IntAttr/StrAttr

The expression builder generates SQL-like query strings under the hood, providing a type-safe Python API for constructing filter conditions. The `.where()` method accepts either an `Expr` object from the expression builder or a raw SQL-like query string (see [Query Language](#query-language) below).

For dynamic query building with runtime type checking, use the expression builder:

```python
from arkiv import Arkiv, IntAttr, StrAttr, IntSort, DESC

client = Arkiv()

# Define typed attributes
age = IntAttr("age")
status = StrAttr("status")
role = StrAttr("role")

# Build expressions with operators
results = client.arkiv.select() \
    .where((age >= 18) & (status == "active")) \
    .order_by(IntSort("age", DESC)) \
    .fetch()

# Complex expressions with OR and AND
results = client.arkiv.select() \
    .where((role == "admin") | (role == "moderator") & (status == "active")) \
    .fetch()

# NOT operator
results = client.arkiv.select() \
    .where((age >= 18) & ~(status == "banned")) \
    .fetch()

# Type checking catches errors early
age == "18"  # TypeError: IntAttr 'age' requires int, got str
status == 1  # TypeError: StrAttr 'status' requires str, got int
```

**Expression Operators:**
- `&` - AND
- `|` - OR
- `~` - NOT

**Note:** Always use parentheses around comparisons when combining with `&`, `|`, or `~` due to Python operator precedence.

#### Sorting with IntSort/StrSort

Use type-specific sort classes for ORDER BY clauses:

```python
from arkiv import Arkiv, IntSort, StrSort, StrAttr, DESC

client = Arkiv()

# Define typed attributes
entity_type = StrAttr("type")
status = StrAttr("status")

# Define sorting_criteria
status_asc = StrSort("status")
age_desc = IntSort("age", DESC)

# Sort by age descending
results = client.arkiv.select() \
    .where(entity_type == "user") \
    .order_by(age_desc) \
    .fetch()

# Multi-field sorting: status ascending, then age descending
results = client.arkiv.select() \
    .where(status == "active") \
    .order_by(status_asc, age_desc) \
    .fetch()
```

#### Limiting Results

Use `.limit()` to restrict the total number of results and `.max_page_size()` to control pagination:

```python
from arkiv import Arkiv, IntSort, StrAttr, DESC

client = Arkiv()

# Define typed attribute
entity_type = StrAttr("type")

# Get first 10 matching entities
results = client.arkiv.select() \
    .where(entity_type == "user") \
    .limit(10) \
    .fetch()

# Top 5 users by age
results = client.arkiv.select() \
    .where(entity_type == "user") \
    .order_by(IntSort("age", DESC)) \
    .limit(5) \
    .fetch()

# Control page size for large entities (smaller pages = less memory per request)
results = client.arkiv.select() \
    .where(entity_type == "document") \
    .max_page_size(10) \
    .fetch()

# Combine limit and page size
results = client.arkiv.select() \
    .where(entity_type == "user") \
    .limit(100) \
    .max_page_size(25) \
    .fetch()
```

### Batch Operations

Batch operations allow you to group multiple entity operations (create, update, extend, delete, change_owner) into a single atomic transaction. This is more efficient and ensures all operations either succeed or fail together.

#### Basic Usage

```python
from arkiv import Arkiv

client = Arkiv()

# Using context manager (recommended)
with client.arkiv.batch() as batch:
    batch.create_entity(payload=b"item 1", expires_in=3600)
    batch.create_entity(payload=b"item 2", expires_in=3600)
    batch.create_entity(payload=b"item 3", expires_in=3600)

# Batch is automatically executed on exit
print(f"Created {len(batch.receipt.creates)} entities")

# Access created entity keys
for create_event in batch.receipt.creates:
    print(f"Created: {create_event.key}")
```

#### Loop-Based Creation

Batch operations work naturally with loops:

```python
items = [
    {"name": "alice", "role": "admin"},
    {"name": "bob", "role": "user"},
    {"name": "charlie", "role": "user"},
]

with client.arkiv.batch() as batch:
    for item in items:
        batch.create_entity(
            payload=item["name"].encode(),
            attributes={"role": item["role"]},
            expires_in=3600,
        )

print(f"Created {len(batch.receipt.creates)} users")
```

#### Mixed Operations

A single batch can contain different operation types:

```python
with client.arkiv.batch() as batch:
    # Create new entities
    batch.create_entity(payload=b"new item", expires_in=3600)

    # Update existing entities
    batch.update_entity(existing_key, payload=b"updated", expires_in=3600)

    # Extend entity lifetime
    batch.extend_entity(another_key, extend_by=7200)

    # Change ownership
    batch.change_owner(some_key, new_owner_address)

    # Delete entities
    batch.delete_entity(old_key)

# Check results
print(f"Creates: {len(batch.receipt.creates)}")
print(f"Updates: {len(batch.receipt.updates)}")
print(f"Extensions: {len(batch.receipt.extensions)}")
print(f"Deletes: {len(batch.receipt.deletes)}")
```

#### Manual Execution

For more control, you can execute batches manually:

```python
batch = client.arkiv.batch()
batch.create_entity(payload=b"data", expires_in=3600)
batch.create_entity(payload=b"more data", expires_in=3600)

# Execute explicitly
receipt = batch.execute()
print(f"Transaction: {receipt.tx_hash}")
```

#### Async Support

Batch operations work with `AsyncArkiv`:

```python
async with AsyncArkiv() as client:
    async with client.arkiv.batch() as batch:
        batch.create_entity(payload=b"async item 1", expires_in=3600)
        batch.create_entity(payload=b"async item 2", expires_in=3600)

    print(f"Created {len(batch.receipt.creates)} entities")
```

#### Error Handling

- If an exception occurs inside the context manager, the batch is **not** executed
- Empty batches are silently skipped (no-op)
- All operations in a batch are atomic: if any operation fails, the entire batch is rolled back

```python
try:
    with client.arkiv.batch() as batch:
        batch.create_entity(payload=b"item 1", expires_in=3600)
        raise ValueError("Something went wrong")
        batch.create_entity(payload=b"item 2", expires_in=3600)
except ValueError:
    pass

# Batch was not executed - no entities created
assert batch.receipt is None
```

### Provider Builder

The `ProviderBuilder` provides a fluent API for creating providers to connect to various Arkiv networks:

```python
from arkiv import Arkiv
from arkiv.account import NamedAccount
from arkiv.provider import ProviderBuilder

# Create account from wallet json
with open('wallet_bob.json', 'r') as f:
    wallet = f.read()

bob = NamedAccount.from_wallet('Bob', wallet, 's3cret')

# Initialize Arkiv client connected to Kaolin (Arkiv testnet)
provider = ProviderBuilder().kaolin().build()
client = Arkiv(provider, account=bob)

# Additional builder examples
provider_custom = ProviderBuilder().custom("https://mendoza.hoodi.arkiv.network/rpc").build()
provider_container = ProviderBuilder().node().build()
provider_kaolin_ws = ProviderBuilder().kaolin().ws().build()
```

### Query Language

Arkiv uses a SQL-like query language to filter and retrieve entities based on their attributes. The query language supports standard comparison operators, logical operators, and parentheses for complex conditions.

#### Supported Operators

**Comparison Operators:**
- `=` - Equal to
- `!=` - Not equal to
- `>` - Greater than
- `>=` - Greater than or equal to
- `<` - Less than
- `<=` - Less than or equal to

**Logical Operators:**
- `AND` - Logical AND
- `OR` - Logical OR
- `NOT` - Logical NOT (can also use `!=`)

**Parentheses** can be used to group conditions and control evaluation order.

#### Query Examples

```python
from arkiv import Arkiv

client = Arkiv()

# Simple equality
query = 'type = "user"'
entities = list(client.arkiv.query_entities(query))

# Note that inn the examples below the call to query_entities is omitted

# Multiple conditions with AND
query = 'type = "user" AND status = "active"'

# OR conditions with parentheses
query = 'type = "user" AND (status = "active" OR status = "pending")'

# Comparison operators
query = 'type = "user" AND age >= 18 AND age < 65'

# NOT conditions
query = 'type = "user" AND status != "deleted"'

# Alternative NOT syntax
query = 'type = "user" AND NOT (status = "deleted")'

# Complex nested conditions
query = '(type = "user" OR type = "admin") AND (age >= 18 AND age <= 65)'

# Multiple NOT conditions
query = 'type = "user" AND status != "deleted" AND status != "banned"'

# Pattern matching with GLOB (using * as wildcard)
query = 'name GLOB "John*"'  # Names starting with "John"

# Pattern matching with suffix
query = 'email GLOB "*@example.com"'  # Emails ending with @example.com
```

**Note:** String values in queries must be enclosed in double quotes (`"`). Numeric values do not require quotes. The `GLOB` operator supports pattern matching using `*` as a wildcard character.
Note that the GLOB operator might be replace by a SQL standard LIKE operator in the future.

### Watch Entity Events

Arkiv provides near real-time event monitoring for entity lifecycle changes. You can watch for entity creation, updates, extensions, deletions, and ownership changes using callback-based event filters.

#### Available Event Types

- **`watch_entity_created`** - Monitor when new entities are created
- **`watch_entity_updated`** - Monitor when entities are updated
- **`watch_entity_extended`** - Monitor when entity lifetimes are extended
- **`watch_entity_deleted`** - Monitor when entities are deleted
- **`watch_owner_changed`** - Monitor when entity ownership changes

#### Basic Usage

```python
from arkiv import Arkiv

client = Arkiv()

# Define callback function to handle events
def on_entity_created(event, tx_hash):
    print(f"New entity created: {event.key}")
    print(f"Owner: {event.owner}")
    print(f"Transaction: {tx_hash}")

# Start watching for entity creation events
event_filter = client.arkiv.watch_entity_created(on_entity_created)

# Create an entity - callback will be triggered
entity_key, _ = client.arkiv.create_entity(
    payload=b"Hello World",
    attributes={"type": "greeting"}
)

# Stop watching when done
event_filter.stop()
event_filter.uninstall()
```

#### Watching Multiple Event Types

```python
created_events = []
updated_events = []
deleted_events = []

def on_created(event, tx_hash):
    created_events.append((event, tx_hash))

def on_updated(event, tx_hash):
    updated_events.append((event, tx_hash))

def on_deleted(event, tx_hash):
    deleted_events.append((event, tx_hash))

# Watch multiple event types simultaneously
filter_created = client.arkiv.watch_entity_created(on_created)
filter_updated = client.arkiv.watch_entity_updated(on_updated)
filter_deleted = client.arkiv.watch_entity_deleted(on_deleted)

# Perform operations...
# Events are captured in real-time

# Cleanup all filters
filter_created.uninstall()
filter_updated.uninstall()
filter_deleted.uninstall()
```

#### Historical Events

By default, watchers only capture new events from the current block forward. You can also watch from a specific historical block:

```python
# Watch from a specific block number
event_filter = client.arkiv.watch_entity_created(
    on_entity_created,
    from_block=1000
)

# Watch from the beginning of the chain
event_filter = client.arkiv.watch_entity_created(
    on_entity_created,
    from_block=0
)
```

#### Automatic Cleanup

When using Arkiv as a context manager, all event filters are automatically cleaned up on exit:

```python
with Arkiv() as client:
    # Create event filters
    filter1 = client.arkiv.watch_entity_created(callback1)
    filter2 = client.arkiv.watch_entity_updated(callback2)

    # Perform operations...
    # Filters are automatically stopped and uninstalled when exiting context
```

You can also manually clean up all active filters:

```python
client.arkiv.cleanup_filters()
```

**Note:** Event watching requires polling the node for new events. The SDK handles this automatically in the background.

## Development Guide

### Setup

Requirements
- Python: Version 3.10 or higher
- Install:
    - `pip install --pre arkiv-sdk`
    - `pip install testcontainers websockets`
- RPC: `https://mendoza.hoodi.arkiv.network/rpc`

### Branches, Versions, Changes

#### Branches

The current stable branch on Git is `main`.
Currently `main` hosts the initial SDK implementation.

The branch `v1-dev` hosts the future V1.0 SDK release.

#### Versions

For version management the [uv](https://github.com/astral-sh/uv) package and project manger is used.
Use the command below to display the current version
```bash
uv version
```

SDK versions are tracked in the following files:
- `pyproject.toml`
- `uv.lock`

### Testing

Pytest is used for unit and integration testing.
```bash
uv run pytest # Run all tests
uv run pytest -k test_create_entity_simple --log-cli-level=info # Specific tests via keyword, print at info log level
```

If an `.env` file is present the unit tests are run against the specifice RPC coordinates and test accounts.
An example wallet file is provided in `.env.testing`
Make sure that the specified test accounts are properly funded before running the tests.

Otherwise, the tests are run against a testcontainer containing an Arkiv RPC Node.
Test accounts are created on the fly and using the CLI inside the local RPC Nonde.

Account wallets for such tests can be created via the command shown below.
The provided example creates the wallet file `wallet_alice.json` using the password provided during the execution of the command.

```bash
uv run python -m arkiv.account alice
```

### Code Quality

This project uses comprehensive unit testing, linting and type checking to maintain high code quality:

#### Quick Commands

Before any commit run quality checks:
```bash
./scripts/check-all.sh
```

#### Tools Used

- **MyPy**: Static type checker with strict configuration
- **Ruff**: Fast linter and formatter (replaces black, isort, flake8, etc.)
- **Pre-commit**: Automated quality checks on git commits

#### Individual commands
```bash
uv run ruff check . --fix    # Lint and auto-fix
uv run ruff format .         # Format code
uv run mypy src/ tests/      # Type check
uv run pytest tests/ -v     # Run tests
uv run pytest --cov=src   # Run code coverage
uv run pre-commit run --all-files # Manual pre commit checks
```

#### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit` and will:
- Fix linting issues with ruff
- Format code consistently
- Run type checking with mypy
- Check file formatting (trailing whitespace, etc.)

#### MyPy Settings

- `strict = true` - Enable all strict checks
- `no_implicit_reexport = true` - Require explicit re-exports
- `warn_return_any = true` - Warn about returning Any values
- Missing imports are ignored for third-party libraries without type stubs

#### Ruff Configuration

- Use 88 character line length (Black-compatible)
- Target Python 3.10+ features
- Enable comprehensive rule sets (pycodestyle, pyflakes, isort, etc.)
- Auto-fix issues where possible
- Format with double quotes and trailing commas

## Alias

```bash
function gl { git log --format="%C(green)%ad%C(reset) %C(yellow)%h%C(reset)%C(auto)%d%C(reset) %s" --date=format:"%Y-%m-%d_%H:%M:%S" -n ${1:-10}; }
alias gs='git status'
```
