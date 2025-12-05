# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0b1] - 2025-12-05

### Added Features
- Add query builder (see readme)
- Add batch processing (see readme)

### Changes
- Iterations on AGENTS.md

## [1.0.0a10] - 2025-11-29

### Added Features
- Add  `timeout()` to `ProviderBuilder`,

### Changes
- Add AGENTS.md
- Minor cleanups/test additions

## [1.0.0a9] - 2025-11-18

### Changes
- Check for existence of default accountin (Async)Arkiv before attempting to execute a transaction"
- Add active filter cleanup for AsyncArkiv

## [1.0.0a8] - 2025-11-14

### Changes
- Breaking: rename extend_entity parameter number_of_blocks to extend_by (in seconds).

## [1.0.0a7] - 2025-11-13

### Added Features
- Add sorting support for query results with `OrderByAttribute` (string and numeric, ascending/descending)
- Add multi-attribute sorting with priority-based ordering
- Add `to_seconds()` and `to_blocks()` utility methods to (Async)Arkiv for time/block conversions

### Other Changes
- Breaking: Changed expires_in parameter from blocks to seconds across all entity operations
- Migrated from `btl` (blocks to live) to `expires_in` (seconds) for clearer, more intuitive API
- Consolidated configuration constants (BLOCK_TIME_SECONDS, EXPIRES_IN_DEFAULT, CONTENT_TYPE_DEFAULT) to ArkivModuleBase

## [1.0.0a6] - 2025-11-10

### Added Features
- Switch to iterator pattern for query_entities

### Other Changes
- Add README sections for querying
- Renamings and refactorings for the iterator approach
- Add query tests for select, paging and query language

## [1.0.0a5] - 2025-11-05

### Added Features
- Add change_owner to Arkiv and AsyncArkiv
- Add watch_owner_changed to Arkiv and AsyncArkiv

### Other Changes
- Upgrade to latest Arkiv node state including compression of TX data using brotli

## [1.0.0a4] - 2025-10-30

### Added Features
- Added AsyncArkiv

### Other Changes
- Major refactorings introducing base classes for code shared between Arkiv and AsyncArkiv
- Docstrings for entity methods pushed to ArkivModuleBase

### Known Bugs
- Entity extension broken with latest Arkiv Node version

## [1.0.0a3] - 2025-10-09

- Minor changes only

## [1.0.0a2] - 2025-10-09

### Documentation
- README fixed

### Developer Experience
- Default blocks to live values at 1000, parameter may be omitted for simple prototyping

## [1.0.0a1] - 2025-10-08

### Added

#### Core Features
- Full entity CRUD operations (create, read, update, delete, extend)
- Simplified `Arkiv()` client with auto-managed local node and default account
- Web3.py compatibility layer - drop-in replacement for Web3 client
- Type-safe API with comprehensive type hints and mypy strict mode
- Named account management for multi-account workflows
- Provider builder for easy connection setup (localhost, Kaolin testnet, custom)

#### Entity Management
- Create entities with payload, annotations, and expiration
- Update entity payload and annotations
- Extend entity lifetime with additional blocks
- Delete entities
- Bulk operations support for all CRUD operations
- Entity existence checking
- Field projections (payload, annotations, metadata)

#### Querying & Events
- Query support for filtering entities by annotations
- Event watching: EntityCreated, EntityUpdated, EntityDeleted, EntityExtended
- Filter management with automatic cleanup
- Block-based event subscription (latest, specific block numbers)

#### Developer Experience
- Automatic local node management with Docker/testcontainers
- Auto-funded test accounts on local nodes
- Comprehensive error handling with typed exceptions
- 214 passing tests with 100% critical path coverage
- Developer documentation with examples
- USE_CASES.md with 7 concrete use cases for Arkiv
- Dev container configuration for VS Code
- Pre-commit hooks for code quality

#### Documentation
- Comprehensive README with quickstart guide
- API documentation with examples
- Architecture overview
- Development guide
- Use case examples (NFTs, Gaming, Social, DAOs, DeFi, Supply Chain, AI/ML)

### Technical Details
- Python 3.12+ required
- Web3.py 7.13.0 integration
- UV package manager support
- Ruff linting and formatting
- MyPy strict type checking
- Pytest with parallel test execution

### Notes
- This is an alpha release (1.0.0a1) - API may change before 1.0.0 stable
- Replaces the previous 0.x SDK with a complete rewrite
- Production use not recommended until 1.0.0 stable release

[Unreleased]: https://github.com/Arkiv-Network/arkiv-sdk-python/compare/v1.0.0a1...HEAD
[1.0.0a1]: https://github.com/Arkiv-Network/arkiv-sdk-python/releases/tag/v1.0.0a1
