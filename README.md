# Arkiv SDK

Arkiv is a permissioned storage system for decentralized apps, supporting flexible entities with binary data, annotations, and metadata.

The Arkiv SDK is the official Python library for interacting with Arkiv networks. It offers a type-safe, developer-friendly API for managing entities, querying data, subscribing to events, and offchain verification—ideal for both rapid prototyping and production use.

## SDK Architecture

### Principles

SDK should be directly derived from one of the most well known and more recent client libraries.

Highlevel goals:
1. Go with the flow of the language and the library.
2. Whatever works for the library should also work for the SDK
3. Feels like "Library + Entities".

### Underlying Library

As underlying library we use [Web3.py](https://github.com/ethereum/web3.py) (no good alternatives).

### Naming

Github "Home": `arkiv-network`
| Language | Element    | Name           | Comment                 |
|----------|------------|----------------|-------------------------|
| Python   | Repository | `arkiv-sdk-python` | Golem Base repo: `python-sdk` move and rename to `arkiv-python-beta` |
| Python   | PIP        | `pip install arkiv-sdk`   | or `pip install arkiv` as `arkiv` is not available for Rust |


### Arkiv Client

Goal: Make Arkiv feel like "web3.py + entities", maintaining the familiar developer experience that Python web3 developers.

A `client.entities.*` approach for consistency with web3.py's module pattern. It clearly communicates that arkiv is a module extension just like eth, net, etc.

Here's a "Hello World!" example showing how to use the Python Arkiv SDK:

```python
from web3 import HTTPProvider
from arkiv import Arkiv
from arkiv.account import NamedAccount

with open ('wallet_alice.json', 'r') as f:
    wallet = f.read()

# Initialize Arkiv client (extends Web3)
provider = HTTPProvider('https://kaolin.hoodi.arkiv.network/rpc')
account = NamedAccount.from_wallet('Alice', wallet, 's3cret')
client = Arkiv(provider, account = account)

# Check connection
print(f"Connected: {client.is_connected()}")

# Create entity with data and annotations
entity_key, tx_hash = client.arkiv.create_entity(
    payload=b"Hello World!",
    annotations={"type": "greeting", "version": 1},
    btl = 1000
)
print(f"Created entity: {entity_key}")

# Get individual entity and print its details
entity = client.arkiv.get_entity(entity_key)
print(f"Entity: {entity}")

# TODO
# Clean up - delete entities
print("\n=== Cleanup ===")
client.arkiv.delete_entity(entity_key)
print("Entities deleted")

# Verify deletion
exists = client.arkiv.exists(entity_key1)
print(f"Entity 1 exists? {exists}")
```

Arkiv extensions
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
````

Web3 standard
```python
from web3 import HTTPProvider
provider = HTTPProvider('https://kaolin.hoodi.arkiv.network/rpc')

# Arkiv 'is a' Web3 client
client = Arkiv(provider)
balance = client.eth.get_balance(client.eth.default_account)
client.eth.get_transaction(tx_hash)
````

# Development Guide

## Code Quality and Type Safety

This project uses comprehensive linting and type checking to maintain high code quality:

### Tools Used

- **MyPy**: Static type checker with strict configuration
- **Ruff**: Fast linter and formatter (replaces black, isort, flake8, etc.)
- **Pre-commit**: Automated quality checks on git commits

### Quick Commands

```bash
# Run all quality checks
./scripts/check-all.sh

# Individual tools
uv run ruff check . --fix    # Lint and auto-fix
uv run ruff format .         # Format code
uv run mypy src/ tests/      # Type check
uv run pytest tests/ -v     # Run tests
uv run pytest --cov=src   # Run code coverage
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit` and will:
- Fix linting issues with ruff
- Format code consistently
- Run type checking with mypy
- Check file formatting (trailing whitespace, etc.)

To run pre-commit manually:
```bash
uv run pre-commit run --all-files
```

### Type Hints Best Practices

1. **Always use type hints** for function parameters and return values
2. **Use specific types** instead of `Any` when possible
3. **Import types** from `typing` or `collections.abc` as needed
4. **Use Union types** for multiple acceptable types: `str | int`
5. **Generic containers**: `list[str]`, `dict[str, int]`, etc.

### Example Type-Safe Code

```python
from collections.abc import Generator
from typing import Any

def process_data(items: list[dict[str, Any]]) -> Generator[str, None, None]:
    """Process data items and yield formatted strings."""
    for item in items:
        if isinstance(item.get("name"), str):
            yield f"Processing: {item['name']}"
```

### MyPy Configuration

The project uses strict mypy settings:
- `strict = true` - Enable all strict checks
- `no_implicit_reexport = true` - Require explicit re-exports
- `warn_return_any = true` - Warn about returning Any values
- Missing imports are ignored for third-party libraries without type stubs

### Ruff Configuration

Ruff is configured to:
- Use 88 character line length (Black-compatible)
- Target Python 3.12+ features
- Enable comprehensive rule sets (pycodestyle, pyflakes, isort, etc.)
- Auto-fix issues where possible
- Format with double quotes and trailing commas
