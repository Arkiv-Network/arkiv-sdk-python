# Arkiv SDK

Arkiv is a permissioned storage system for decentralized apps, supporting flexible entities with binary data, annotations, and metadata.

The Arkiv SDK is the official Python library for interacting with Arkiv networks. It offers a type-safe, developer-friendly API for managing entities, querying data, subscribing to events, and offchain verification—ideal for both rapid prototyping and production use.

## Architecture

Principles:
- The SDK is based on a modern and stable client library.
- The SDK should feel like "Library + Entities"

As underlying library we use [Web3.py](https://github.com/ethereum/web3.py) (no good alternatives for Python).


### Arkiv Client

The Arkiv SDK should feel like "web3.py + entities", maintaining the familiar developer experience that Python web3 developers.

A `client.arkiv.*` approach is in line with web3.py's module pattern.
It clearly communicates that arkiv is a module extension just like eth, net, etc.

## Hello World
Here's a "Hello World!" example showing how to use the Python Arkiv SDK:

```python
from arkiv import Arkiv
from arkiv.account import NamedAccount

# Create account and client that implicitly starts a local Arkiv node
alice = NamedAccount.create('Alice')
client = Arkiv(account=alice)
print(f"Connected: {client.is_connected()}")

# Fund the account
client.node.fund_account(alice)
print(f"Balance: {client.eth.get_balance(alice.address)}")

# Create entity with data and annotations
entity_key, tx_hash = client.arkiv.create_entity(
    payload=b"Hello World!",
    annotations={"type": "greeting", "version": 1},
    btl = 1000
)

# Check and print entity key
exists = client.arkiv.entity_exists(entity_key)
print(f"Created entity: {entity_key}, exists={exists}")

# Get individual entity and print its details
entity = client.arkiv.get_entity(entity_key)
print(f"Entity: {entity}")

# TODO
# Clean up - delete entities
client.arkiv.delete_entity(entity_key)
print("Entities deleted")
```

### Provider Builder

The snippet below demonstrates the creation of various nodes to connect to using the `ProviderBuilder`.

```python
from arkiv import Arkiv
from arkiv.account import NamedAccount
from arkiv.provider import ProviderBuilder

# Create account from wallet json
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
from arkiv.account import NamedAccount

account = NamedAccount.from_wallet('Alice', wallet, 's3cret')
client = Arkiv(provider, account = account)

entity_key, tx_hash = client.arkiv.create_entity(
    payload=b"Hello World!",
    annotations={"type": "greeting", "version": 1},
    btl = 1000
)

entity = client.arkiv.get_entity(entity_key)
exists = client.arkiv.exists(entity_key)
```

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
