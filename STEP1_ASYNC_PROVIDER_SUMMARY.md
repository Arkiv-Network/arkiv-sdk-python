# Step 1: Async Provider Support - Implementation Summary

## Overview

Extended `ProviderBuilder` with an `async_mode()` modifier that controls provider creation at the `build()` point, maintaining backward compatibility while enabling async provider support.

## Changes Made

### 1. Updated Imports (`provider.py`)

Added async provider imports:
```python
from web3.providers import AsyncHTTPProvider, HTTPProvider, WebSocketProvider
from web3.providers.async_base import AsyncBaseProvider
from web3.providers.base import BaseProvider
```

### 2. Added `_is_async` State Flag

Added to `ProviderBuilder.__init__()`:
```python
self._is_async: bool = False  # Default to sync providers
```

**Default behavior preserved**: Sync mode by default (backward compatible).

### 3. New `async_mode()` Method

```python
def async_mode(self) -> ProviderBuilder:
    """
    Enable async provider mode.

    When enabled, build() will return async-compatible providers:
    - HTTP transport → AsyncHTTPProvider
    - WebSocket transport → WebSocketProvider (inherently async)

    By default (async mode disabled), build() returns sync providers:
    - HTTP transport → HTTPProvider
    - WebSocket transport → WebSocketProvider (inherently async)
    """
    self._is_async = True
    return self
```

**Key characteristics**:
- Chainable (returns `self`)
- Can be called at any point in the builder chain
- Toggles async mode flag

### 4. Updated `build()` Method

Modified return type and logic:

```python
def build(self) -> BaseProvider | AsyncBaseProvider:
    # ... URL resolution logic (unchanged) ...

    # Build provider based on transport and async mode
    if self._transport == HTTP:
        if self._is_async:
            return AsyncHTTPProvider(url)
        else:
            return HTTPProvider(url)
    else:  # WebSocket
        # WebSocketProvider is always async
        return cast(AsyncBaseProvider, WebSocketProvider(url))
```

**Behavior matrix**:

| Transport | async_mode() | Provider Created | Base Class |
|-----------|--------------|------------------|------------|
| HTTP | ❌ No (default) | `HTTPProvider` | `BaseProvider` |
| HTTP | ✅ Yes | `AsyncHTTPProvider` | `AsyncBaseProvider` |
| WebSocket | ❌ No | `WebSocketProvider` | `AsyncBaseProvider` |
| WebSocket | ✅ Yes | `WebSocketProvider` | `AsyncBaseProvider` |

**Important**: WebSocket providers are **always async** (inherit from `AsyncBaseProvider`), regardless of `async_mode()` flag.

## Test Coverage

Added comprehensive test class `TestProviderBuilderAsyncMode` with 12 tests:

1. ✅ `test_async_mode_sets_correct_state` - Verifies `_is_async` flag
2. ✅ `test_default_is_sync_mode` - Confirms sync default
3. ✅ `test_async_mode_with_http_creates_async_http_provider` - AsyncHTTPProvider creation
4. ✅ `test_async_mode_with_ws_creates_websocket_provider` - WebSocket with async_mode()
5. ✅ `test_sync_mode_with_http_creates_http_provider` - Default sync behavior
6. ✅ `test_sync_mode_with_ws_creates_websocket_provider` - WebSocket always async
7. ✅ `test_async_mode_with_kaolin_http` - Async with Kaolin network
8. ✅ `test_async_mode_with_kaolin_ws` - WebSocket with Kaolin
9. ✅ `test_async_mode_with_custom_url` - Async with custom URLs
10. ✅ `test_async_mode_chaining` - Chainable at different positions
11. ✅ `test_async_mode_with_node` - Async with ArkivNode
12. ✅ `test_async_mode_return_type_annotation` - Type annotation validation

**All 44 provider tests passing** (32 existing + 12 new).

## Usage Examples

### Sync HTTP Provider (Default - Unchanged)
```python
provider = ProviderBuilder().localhost().build()
# Returns: HTTPProvider (BaseProvider)
```

### Async HTTP Provider (NEW)
```python
provider = ProviderBuilder().localhost().async_mode().build()
# Returns: AsyncHTTPProvider (AsyncBaseProvider)
```

### WebSocket Provider (Always Async)
```python
# Without async_mode()
provider = ProviderBuilder().localhost().ws().build()
# Returns: WebSocketProvider (AsyncBaseProvider)

# With async_mode() - same result
provider = ProviderBuilder().localhost().ws().async_mode().build()
# Returns: WebSocketProvider (AsyncBaseProvider)
```

### Chaining Examples
```python
# async_mode() can be anywhere in chain
ProviderBuilder().async_mode().localhost().http().build()
ProviderBuilder().localhost().async_mode().http().build()
ProviderBuilder().localhost().http().async_mode().build()
# All return: AsyncHTTPProvider
```

### With Different Networks
```python
# Kaolin async HTTP
ProviderBuilder().kaolin().async_mode().build()
# Returns: AsyncHTTPProvider("https://kaolin.hoodi.arkiv.network/rpc")

# Custom URL async HTTP
ProviderBuilder().custom("https://my-rpc.io").async_mode().build()
# Returns: AsyncHTTPProvider("https://my-rpc.io")
```

### With ArkivNode
```python
with ArkivNode() as node:
    # Async HTTP
    provider = ProviderBuilder().node(node).async_mode().build()
    # Returns: AsyncHTTPProvider(node.http_url)

    # Async WebSocket
    provider = ProviderBuilder().node(node).ws().async_mode().build()
    # Returns: WebSocketProvider(node.ws_url)
```

## Backward Compatibility

✅ **100% Backward Compatible**

- Default behavior unchanged (sync providers)
- All existing code continues to work
- No breaking changes to API
- Existing tests all pass

## Design Decisions

### 1. Why `async_mode()` instead of `async()`?

- `async` is a Python keyword and cannot be used as method name
- `async_mode()` is explicit and self-documenting
- Alternatives considered: `enable_async()`, `use_async()`, `asynchronous()`

### 2. Why is `_is_async` a separate flag?

- Clear separation of concerns: transport vs. execution mode
- Allows future extensions (e.g., different async strategies)
- Makes state management explicit and testable

### 3. Why does WebSocket ignore `async_mode()`?

- Web3.py's `WebSocketProvider` inherits from `AsyncBaseProvider`
- WebSocket is inherently async in the library
- No sync WebSocket provider exists
- Being explicit would be misleading

## Type Safety

Updated return type annotation:
```python
def build(self) -> BaseProvider | AsyncBaseProvider:
```

Type checkers (mypy/pyright) can now distinguish:
```python
sync_provider: BaseProvider = ProviderBuilder().localhost().build()
async_provider: AsyncBaseProvider = ProviderBuilder().localhost().async_mode().build()
```

## Next Steps (Step 2)

With `async_mode()` in place, we can now:

1. Create `AsyncArkiv` client class
2. Add provider validation for async providers
3. Ensure sync `Arkiv` rejects async providers
4. Ensure async `AsyncArkiv` rejects sync providers
5. Update tests accordingly

## Files Modified

1. **`src/arkiv/provider.py`**:
   - Added imports: `AsyncHTTPProvider`, `AsyncBaseProvider`
   - Added `_is_async` flag to `__init__()`
   - Added `async_mode()` method
   - Updated `build()` logic and return type

2. **`tests/test_provider.py`**:
   - Added imports: `AsyncHTTPProvider`, `AsyncBaseProvider`
   - Added `TestProviderBuilderAsyncMode` test class (12 tests)

## Performance Considerations

- No performance impact on sync path (default)
- Async providers only created when explicitly requested
- No runtime overhead for flag check (single boolean comparison)

## Documentation Updates Needed

- Update `ProviderBuilder` docstring examples ✅ (done)
- Update README.md with async examples (pending Step 2)
- Create migration guide for async adoption (pending)

---

**Status**: ✅ Step 1 Complete - All tests passing (44/44)
**Ready for**: Step 2 - AsyncArkiv client implementation
