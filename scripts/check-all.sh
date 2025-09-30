#!/usr/bin/env bash
# Quality check script - runs all linting and type checking

set -e

echo "🔍 Running Ruff linter..."
uv run ruff check . --fix

echo "✨ Running Ruff formatter..."
uv run ruff format .

echo "🏷️  Running MyPy type checker..."
uv run mypy src/ tests/

echo "🧪 Running tests..."
uv run pytest tests/ -v

echo "✅ All quality checks passed!"
