# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
