# Agent Instructions

Instructions for AI coding agents working on this repository.

## Critical Rules (Read First)

1. **Understand first** – Ensure you understand the problem and we have a shared understanding of what needs to be done or fixed.
2. **Always use `uv run`** for ALL Python commands – never `python`, `pip`, or venv activation
3. **No `.env` file** – remove before running tests (causes flaky tests against wrong endpoint)
4. **Run tests before claiming done** – `uv run pytest tests/test_specific.py -v`
5. **Run full check before commit** – `./scripts/check-all.sh`

## Running Commands

**ALWAYS use `uv run` to execute Python commands.** Never use `python`, `pip`, or activate virtual environments directly.

```bash
# ✅ Correct
uv run pytest tests/test_foo.py -v
uv run mypy --strict src/
uv run python -c "print('hello')"

# ❌ Wrong - never do this
python -m pytest tests/test_foo.py
pip install some-package
.venv/bin/python script.py
```

This applies to ALL Python-related commands: running tests, type checking, linting, scripts, and REPL sessions.

## Workflow for Changes

Follow this workflow for any code changes:

1. **Understand first** – Ensure you understand the problem and we have a shared understanding of what needs to be done or fixed.

2. **Confirm before changing** – Before making changes, ensure there is a clear instruction to actually change anything. If unsure, ask.

3. **Follow existing patterns** – When proposing changes, make sure you understand the coding patterns and align your changes according to the existing patterns.

4. **Minimal changes only** – Before making a change, ensure that the change is minimal and only changes the item that was discussed.

5. **Run relevant tests** – Before suggesting that you have completed the change, run the relevant tests to ensure that the desired new behaviour is observed. Always use `uv run pytest tests/test_specific.py -v`.

6. **Propose missing tests** – Should tests for the new feature/behaviour be missing, make a proposal for which tests you'd add.

7. **Full quality check** – Once local tests confirm the changes work as intended, run `./scripts/check-all.sh` to verify the new code base does not break old tests and conforms to the coding standards.

## Quality Gates

Before any commit:

```bash
./scripts/check-all.sh
```

**IMPORTANT**: Before running the quality check script, ensure no `.env` file exists in the project root. The `.env` file can override the RPC endpoint and cause tests to run against a remote node instead of the local test container, leading to flaky tests, timeouts, or incorrect test behavior.

```bash
# Check for .env file before running tests
if [ -f .env ]; then
    echo "WARNING: .env file found - remove it before running tests"
    exit 1
fi
./scripts/check-all.sh
```

This runs:
1. `pre-commit run --all-files` – linting, formatting, trailing whitespace
2. `mypy --strict src/` – type checking
3. `pytest -n auto` – all tests in parallel (against local testcontainer node)

## Coding Conventions

### Style

- MyPy strict mode enabled
- Ruff for linting and formatting (88 char lines, double quotes, trailing commas)
- Use `logging` module for debug/info output in tests and library code

### Test Naming

- Sync tests: `test_provider_*`, `test_create_entity_*`, etc.
- Async tests: `test_async_provider_*`, `test_async_create_entity_*`, etc.

## Project Overview

**Arkiv SDK** is the official Python library for interacting with Arkiv networks—a permissioned storage system for decentralized apps supporting flexible entities with binary data, attributes, and metadata.

The SDK is built on top of [Web3.py](https://github.com/ethereum/web3.py) and should feel like "web3.py + entities".

## Architecture

### Clients

| Client | Base Class | Provider | HTTP Stack |
|--------|------------|----------|------------|
| `Arkiv` (sync) | `Web3` | `HTTPProvider` | `requests` |
| `AsyncArkiv` (async) | `AsyncWeb3` | `AsyncHTTPProvider` | `aiohttp` |

- Entity operations live under `client.arkiv.*`, following Web3's module pattern (`eth`, `net`, etc.)
- Always use `async with AsyncArkiv(...)` for proper session cleanup

### Key Modules

| Module | Purpose |
|--------|---------|
| `arkiv.client` | `Arkiv` and `AsyncArkiv` clients |
| `arkiv.provider` | `ProviderBuilder` for HTTP/WS providers |
| `arkiv.account` | `NamedAccount` for wallet/key management |
| `arkiv.node` | `ArkivNode` for local containerized nodes |
| `arkiv.module` / `arkiv.module_async` | Entity CRUD, queries, event watching |
| `arkiv.query_builder` | Fluent query API (`QueryBuilder`, `AsyncQueryBuilder`) |
| `arkiv.query_iterator` | Auto-paginating iterators for query results |

## Test Patterns

- Use `delayed_rpc_server` fixture for deterministic timeout tests
- Use invalid hostnames like `https://nonexistent.rpc-node.local` for DNS failure tests
- Sync timeout: expect `requests.exceptions.ReadTimeout`
- Async timeout: expect `asyncio.TimeoutError` or `aiohttp.ClientError`
- Sync DNS failure: expect `requests.exceptions.ConnectionError`
- Async DNS failure: expect `aiohttp.ClientConnectorDNSError`

## Known Issues

- `AsyncArkiv` must call `_disconnect_provider()` on `__aenter__` failure to avoid unclosed `aiohttp.ClientSession` warnings
- WebSocket providers are always async; sync `Arkiv` client rejects them with a clear error message

## Dependencies

- **uv** – Package and version management
- **pytest** + **pytest-asyncio** – Testing framework
- **testcontainers** – Local Arkiv node containers for integration tests
- **Web3.py 7.x** – Underlying Ethereum client library
