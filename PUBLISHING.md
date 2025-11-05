# Publishing the Arkiv SDK

This guide covers how to publish the Arkiv SDK to PyPI for public use.

## Pre-Publishing Checklist

### 1. Version Management

**Current versions:**
- `pyproject.toml`: `1.0.0a1` (alpha)
- `src/arkiv/__init__.py`: version("arkiv-sdk") # dynamic versioning via pyproject.toml

**Version progression:** Sync versions and choose release type:
- `1.0.0a1` - Alpha (current)
- `1.0.0b1` - Beta (feature complete, testing)
- `1.0.0rc1` - Release candidate (final testing)
- `1.0.0` - Stable release

Use `uv version --bump ... ` to increase version numbers

### 2. Check Required Files

- **README.md** - Comprehensive with examples: Adjusted as needed
- **CHANGELOG.md** - Amended as needed
- **LICENSE** - MIT License
- **pyproject.toml** - Package metadata configured and checked

---

## Pre-Publishing Actions

### 1. Update Version Numbers

**Update `pyproject.toml`:**
```toml
version = "1.0.0a1"  # Choose appropriate version
```

In terminal check current version and update it using `uv` as shown below.

```bash
grep '^version' pyproject.toml
uv version --bump alpha
```

### 2. Update CHANGELOG.md

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [<latest-version>] - <version-date>

### Added
- ...

### Features
- ...

[<latest-version>]: https://github.com/Arkiv-Network/arkiv-sdk-python/releases/tag/latest-version
```

### 3. Update Package Metadata

Check/update fields in `pyproject.toml`:

```toml
[project]
name = "arkiv-sdk"
version = "1.0.0a1"
# ... other existing fields ...
classifiers = [
    "Development Status :: 3 - Alpha",
    # ...
]

# ... check/fix URLs
[project.urls]
# ...
```

### 4. Final Quality Checks

Run full quality check (iterate until all green)

```bash
./scripts/check-all.sh
```

---

## PyPI Account Setup

### 1. Create PyPI Account
- Main PyPI: https://pypi.org/account/register/
- TestPyPI: https://test.pypi.org/account/register/

### 2. API Tokens Management

Export your API token as shell variables

```bash
export PYPI_TOKEN="pypi-..."
export TESTPYPI_TOKEN="pypi-..."
```

---

## Publishing Workflow

### Publish to TestPyPi

1. Ensure you're on the correct branch with latest changes

```bash
git checkout v1-dev
git pull
```

2. Update version in pyproject.toml

```toml
version = "1.0.0a2"  # or next version
```

3. Update CHANGELOG.md with changes

4. (Re)check current state

Run full quality check (iterate until all green)

```bash
./scripts/check-all.sh
```

5. Commit version changes

```bash
git status # check that this matches with your expectation
git add .
git commit -m "chore: prepare for <latest-version>  release"
git push
```

6. Run the publishing wizard
```bash
./scripts/publish.sh
```

The script will:

- Show current version
- Run all quality checks (./scripts/check-all.sh)
- Clean old builds
- Build the package (uv build)
- Show built files
- Prompt you to choose:
    1) Publish to TestPyPI (recommended first)
    2) Publish to PyPI (production)
    3) Exit

7. First time: Choose option 1 (TestPyPI)
Enter your TESTPYPI_TOKEN when prompted (if not in environment)

8. Test installation from TestPyPI
Open a terminal outside the IDE.
When the package arkiv-sdk is installed already remove it first.

```bash
uv pip uninstall arkiv-sdk testcontainers
```

Install the dependencies for local development.

```bash
uv pip install testcontainers
uv pip install -i https://test.pypi.org/simple/ arkiv-sdk
uv run python -c "from arkiv import Arkiv, __version__; print(f'Version: {__version__}')"
```

9. Do some optional smoke tests using the library

Check the package interactively.

```bash
uv run python
```

Python session in interactive shell.

```python
from arkiv import Arkiv
client = Arkiv()
entity_key, _ = client.arkiv.create_entity(payload=b'Hello world!', btl=1000)
client.arkiv.get_entity(entity_key)
```

In case of errors/issues analyize and fix them, then repeat publish to TestPyPi.
Once all checks pass, publish to PyPi (production).

### Publish to PyPi (Production)

1. If all good on TestPyPi, run publish script again for production

```bash
./scripts/publish.sh
````

Choose option 2 (PyPI)


2. Create Git tag

```bash
git tag -a v1.0.0a2 -m "Release version 1.0.0a2"
git push origin v1.0.0a2
```

# 11. Create GitHub release
gh release create v1.0.0a2 \
  --title "Arkiv SDK v1.0.0a2" \
  --notes-file CHANGELOG.md \
  dist/*
```

### Alternative: Manual Publishing (Advanced)

If you prefer manual control or need to customize the process:

```bash
# 1. Ensure you're on the correct branch
git checkout v1-dev
git pull

# 2. Update version numbers
# Edit: pyproject.toml (version is dynamically loaded in __init__.py)

# 3. Run quality checks
./scripts/check-all.sh

# 4. Build the package
uv build
# Creates: dist/arkiv_sdk-1.0.0a1-py3-none-any.whl
#          dist/arkiv_sdk-1.0.0a1.tar.gz

# 5. Check the build
ls -lh dist/

# 6. Test on TestPyPI first
uv publish --token $TESTPYPI_TOKEN --publish-url https://test.pypi.org/legacy/

# 7. Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple arkiv-sdk

# 8. Verify it works
python -c "from arkiv import Arkiv; print(Arkiv.__version__)"

# 9. If all good, publish to PyPI
uv publish --token $PYPI_TOKEN

# 10. Create GitHub release
gh release create v1.0.0a1 \
  --title "Arkiv SDK v1.0.0a1" \
  --notes "Initial alpha release - see CHANGELOG.md" \
  dist/*
```

### Environment Setup for Publishing

Before running the publish script, ensure your tokens are configured:

**Option 1: Environment Variables (Recommended)**
```bash
# Add to ~/.bashrc or ~/.zshrc
export PYPI_TOKEN="pypi-AgEIcHlwaS5vcmcC..."
export TESTPYPI_TOKEN="pypi-AgEOdGVzdC5weXBpLm9yZwI..."

# Reload shell
source ~/.bashrc  # or source ~/.zshrc
```

**Option 2: Manual Entry**
- The script will prompt you to enter tokens if they're not set
- Tokens are only used for that session (not saved)

**For detailed token setup, see:** [PYPI_TOKENS.md](PYPI_TOKENS.md)

---

## Post-Publishing

### 1. Verify Package

```bash
# Install from PyPI
pip install arkiv-sdk

# Test basic functionality
python -c "from arkiv import Arkiv; client = Arkiv(); print(client.is_connected())"
```

### 2. Update Documentation

- Add PyPI badge to README.md:
  ```markdown
  [![PyPI version](https://badge.fury.io/py/arkiv-sdk.svg)](https://badge.fury.io/py/arkiv-sdk)
  ```

- Update installation instructions:
  ```markdown
  ## Installation

  ```bash
  pip install arkiv-sdk
  ```

### 3. Announce Release

- GitHub Discussions/Releases
- Twitter/X
- Discord/Community channels
- Blog post

---

## Version Strategy

### Semantic Versioning (SemVer)

**Format:** `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (1.0.0 → 2.0.0)
- **MINOR**: New features, backward compatible (1.0.0 → 1.1.0)
- **PATCH**: Bug fixes, backward compatible (1.0.0 → 1.0.1)

### Pre-Release Versions

- `0.1.0` - Development/preview
- `1.0.0a1` - Alpha (early testing)
- `1.0.0b1` - Beta (feature complete)
- `1.0.0rc1` - Release candidate
- `1.0.0` - Stable release

### Recommendation

**For initial public sharing:**
- Use `0.1.0` (signals early development, breaking changes expected)
- Or `0.2.0` if you've already had internal `0.1.0`

**For production use:**
- Use `1.0.0` when API is stable and ready for production

---

## Continuous Publishing

### Automate with GitHub Actions

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v2

      - name: Set up Python
        run: uv python install 3.12

      - name: Build package
        run: uv build

      - name: Publish to PyPI
        run: uv publish --token ${{ secrets.PYPI_TOKEN }}
```

Then publishing is as simple as:
```bash
git tag v0.2.0
git push origin v0.2.0
gh release create v0.2.0 --generate-notes
# GitHub Action automatically publishes to PyPI
```

---

## Troubleshooting

### Common Issues

**"Package already exists"**
- Can't republish same version - increment version number

**"Invalid credentials"**
- Check token is correct and not expired
- Ensure using `__token__` as username

**"File already exists"**
- Clear `dist/` folder: `rm -rf dist/`
- Rebuild: `uv build`

**Import errors after install**
- Check package structure in `dist/*.whl` (it's a zip)
- Verify `src/arkiv/__init__.py` exists
- Ensure `pyproject.toml` has correct `where = ["src"]`

---

## Quick Reference

### Using scripts/publish.sh (Recommended)

```bash
# First time setup: Configure tokens (see PYPI_TOKENS.md)
export PYPI_TOKEN="pypi-..."
export TESTPYPI_TOKEN="pypi-..."

# Complete publishing workflow
# 1. Update version in pyproject.toml
# 2. Update CHANGELOG.md
# 3. Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "chore: prepare for v1.0.0a2 release"
git push

# 4. Run publish script - test on TestPyPI first
./scripts/publish.sh  # Choose option 1 (TestPyPI)

# 5. Test the package
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple arkiv-sdk

# 6. If all good, publish to production
./scripts/publish.sh  # Choose option 2 (PyPI)

# 7. Tag and create release
git tag -a v1.0.0a2 -m "Release version 1.0.0a2"
git push origin v1.0.0a2
gh release create v1.0.0a2 --notes-file CHANGELOG.md dist/*
```

### Manual Commands (Advanced)

```bash
# If you need manual control
./scripts/check-all.sh                    # Quality checks
uv build                                   # Build package
uv publish --token $TESTPYPI_TOKEN --publish-url https://test.pypi.org/legacy/
uv publish --token $PYPI_TOKEN            # Publish to PyPI
git tag v1.0.0a2 && git push origin v1.0.0a2  # Tag release
```

**Next version publish:**
```bash
# 1. Update version in pyproject.toml (e.g., "1.0.0a3")
# 2. Update CHANGELOG.md
# 3. Commit and push
# 4. Run: ./scripts/publish.sh
# 5. Tag release
```
