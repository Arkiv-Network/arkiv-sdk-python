#!/usr/bin/env bash
# Quality check script - runs all linting type checking and tests
# Usage: ./scripts/check-all.sh

set -e

echo "🔍 Running pre-commit checks..."
uv run --group lint pre-commit run --all-files

echo "🧪 Running tests..."
uv run --group test pytest tests/ -n auto -v

echo "✅ All quality checks passed!"
