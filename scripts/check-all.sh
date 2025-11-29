#!/usr/bin/env bash
# Quality check script - runs all linting type checking and tests
# Usage: ./scripts/check-all.sh

set -e

echo "🔍 Running pre-commit checks..."
uv run --group lint pre-commit run --all-files

echo "🔬 Running type checks with mypy..."
uv run --group lint mypy --strict src/

echo "🧪 Running tests..."
uv run --group test pytest -n auto || {
    echo "⚠️ Some tests failed, retrying failed tests with fresh session..."
    uv run --group test pytest --lf -n 2
}

echo "✅ All quality checks passed!"
