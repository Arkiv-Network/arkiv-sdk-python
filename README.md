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
    payload=b"Hello World!",
    content_type="text/plain",
    attributes={"type": "greeting", "version": 1},
    btl=1000
)

# Check and print entity key
exists = client.arkiv.entity_exists(entity_key)
print(f"Created entity: {entity_key} (exists={exists}), creation TX: {receipt.tx_hash}")

# Get individual entity and print its details
entity = client.arkiv.get_entity(entity_key)
print(f"Entity: {entity}")

# Clean up - delete entity
client.arkiv.delete_entity(entity_key)
print("Entity deleted")
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
            payload=b"Hello Async World!",
            attributes={"type": "greeting", "version": 1},
            btl=1000
        )

        # Get entity and check existence
        entity = await client.arkiv.get_entity(entity_key)
        exists = await client.arkiv.entity_exists(entity_key)

        # Clean up - delete entity
        await client.arkiv.delete_entity(entity_key)

asyncio.run(main())
```

### Web3 Standard Support
```python
from web3 import HTTPProvider
provider = HTTPProvider('https://kaolin.hoodi.arkiv.network/rpc')

# Arkiv 'is a' Web3 client
client = Arkiv(provider)
balance = client.eth.get_balance(client.eth.default_account)
tx = client.eth.get_transaction(tx_hash)
```

### Arkiv Module Extension
```python
from arkiv import Arkiv

# Simple local setup
client = Arkiv()

# Or with custom provider and account
from arkiv.account import NamedAccount
account = NamedAccount.from_wallet('Alice', wallet, 's3cret')
client = Arkiv(provider, account=account)

entity_key, tx_hash = client.arkiv.create_entity(
    payload=b"Hello World!",
    attributes={"type": "greeting", "version": 1},
    btl = 1000
)

entity = client.arkiv.get_entity(entity_key)
exists = client.arkiv.exists(entity_key)
```

## Advanced Features

### Provider Builder

The snippet below demonstrates the creation of various nodes to connect to using the `ProviderBuilder`.

```python
from arkiv import Arkiv
from arkiv.account import NamedAccount
from arkiv.provider import ProviderBuilder

## Advanced Features

### Provider Builder

The snippet below demonstrates the creation of various nodes to connect to using the `ProviderBuilder`.

```python
from arkiv import Arkiv
from arkiv.account import NamedAccount
from arkiv.provider import ProviderBuilder

# Create account from wallet json
with open ('wallet_bob.json', 'r') as f:
    wallet = f.read()

bob = NamedAccount.from_wallet('Bob', wallet, 's3cret')

# Initialize Arkiv client connected to Kaolin (Akriv testnet)
provider = ProviderBuilder().kaolin().build()
client = Arkiv(provider, account=bob)

# Additional builder examples
provider_container = ProviderBuilder().node().build()
provider_kaolin_ws = ProviderBuilder().kaolin().ws().build()
provider_custom = ProviderBuilder().custom("https://my-rpc.io").build()
```

### Query Iterator

The `query_entities` method returns an iterator that automatically handles pagination, making it easy to work with large result sets:

```python
from arkiv import Arkiv
from arkiv.types import QueryOptions, KEY, ATTRIBUTES

client = Arkiv()

# Query entities with automatic pagination
query = 'type = "user" AND age > 18'
options = QueryOptions(fields=KEY | ATTRIBUTES, max_results_per_page=100)

# Iterate over all matching entities
# Pagination is handled automatically by the iterator
for entity in client.arkiv.query_entities(query=query, options=options):
    print(f"Entity {entity.key}: {entity.attributes}")

# Or collect all results into a list
entities = list(client.arkiv.query_entities(query=query, options=options))
print(f"Found {len(entities)} entities")
```

## Arkiv Topics/Features

### BTL

BTL (Blocks-To-Live) should be replaced with explicit `expires_at_block` values for predictability and composability.

Relative `BTL` depends on execution timing and creates unnecessary complexity:
- An entity created with `btl=100` will have different expiration blocks depending on when the transaction is mined
- Extending entity lifetimes requires fetching the entity, calculating remaining blocks, and adding more—a race-prone pattern
- Creates asymmetry between write operations (which use `btl`) and read operations (which return `expires_at_block`)
- Mempool management can accept any value

Absolute `expires_at_block` is predictable, composable, and matches what you get when reading entities:
- Deterministic regardless of execution timing
- Maps directly to `Entity.expires_at_block` field returned by queries
- Enables clean compositional patterns like `replace(entity, expires_at_block=entity.expires_at_block + 100)`
- Aligns write API with read API, making the SDK more intuitive
- Mempool needs to manage/delete tx with expires at values in the past

It's complicated. Deterministic mempool management vs predictable tx management in mempool.

```python
from dataclasses import replace

# Fetch entity
entity = client.arkiv.get_entity(entity_key)

# Modify payload and extend expiration by 100 blocks
updated_entity = replace(
    entity,
    payload=b"new data",
    expires_at_block=entity.expires_at_block + 100
)

# Update entity
client.arkiv.update_entity(updated_entity)
```

### Query DSL

To make querying entities as simple and natural as possible, rely on a suitable and existing query DSL. Since Arkiv currently uses a SQL database backend and is likely to support SQL databases in the future, the Arkiv query DSL is defined as a **subset of the SQL standard**.

**Rationale:**
- Leverages existing SQL knowledge - no new language to learn
- Well-defined semantics and broad tooling support
- Natural fit for relational data structures
- Enables familiar filtering, joining, and aggregation patterns

**Example:**
```python
# Query entities using SQL-like syntax
results = client.arkiv.query_entities(
    "SELECT key, payload WHERE attributes.type = 'user' AND attributes.age > 18 ORDER BY attributes.name"
)
```

### Sorting

Querying entities should support sorting results by one or more fields.

**Requirements:**
- Sort by attributes (string and numeric)
- Sort by metadata (owner, expires_at_block)
- Support ascending and descending order
- Multi-field sorting with priority

**Example:**
```python
# SQL-style sorting
results = client.arkiv.query(
    "SELECT * FROM entities ORDER BY attributes.priority DESC, attributes.name ASC"
)
```

### Other Features

- **Creation Flags**: Entities should support creation-time flags with meaningful defaults.
Flags can only be set at creation and define entity behavior:
  - **Read-only**: Once created, entity data cannot be changed by anyone (immutable)
  - **Unpermissioned extension**: Entity lifetime can be extended by anyone, not just the owner
  ```python
  # Proposed API
  client.arkiv.create_entity(
      payload=b"data",
      attributes={"type": "public"},
      expires_at_block=future_block,
      flags=EntityFlags.READ_ONLY | EntityFlags.PUBLIC_EXTENSION
  )
  ```

- **ETH Transfers**: Arkiv chains should support ETH (or native token like GLM) transfers for gas fees and value transfer.
  ```python
  # Already supported via Web3.py compatibility
  tx_hash = client.eth.send_transaction({
      'to': recipient_address,
      'value': client.to_wei(1, 'ether'),
      'gas': 21000
  })
  ```

- **Offline Entity Verification**: Provide cryptographic verification of entity data without querying the chain.
  - Currently not supported
  - Proposal: Store entity keys (and block number) in smart contracts and work with an optimistic oracle approach (challenger may take entity key and checks claimed data against the data of an Arkiv archival node)

## Development Guide

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
uv run python uv run python -m arkiv.account alice
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
- Target Python 3.12+ features
- Enable comprehensive rule sets (pycodestyle, pyflakes, isort, etc.)
- Auto-fix issues where possible
- Format with double quotes and trailing commas

## Alias

```bash
function gl { git log --format="%C(green)%ad%C(reset) %C(yellow)%h%C(reset)%C(auto)%d%C(reset) %s" --date=format:"%Y-%m-%d_%H:%M:%S" -n ${1:-10}; }
alias gs='git status'
```
