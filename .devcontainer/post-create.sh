#!/bin/bash
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 Setting up Arkiv SDK development environment..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Clean up any existing .venv that may have wrong ownership (e.g., from root user)
if [ -d ".venv" ]; then
    echo ""
    echo "🧹 Cleaning up existing .venv directory..."
    sudo rm -rf .venv
fi

echo ""
echo "📦 Installing Python dependencies with uv..."
uv sync --all-groups

echo ""
echo "⚙️  Configuring git editor..."
git config --global core.editor nano

echo ""
echo "✅ Verifying installation..."
echo "   Python: $(python --version)"
echo "   UV: $(uv --version)"
echo "   Pytest: $(uv run pytest --version)"
echo "   Ruff: $(uv run ruff --version)"
echo "   Mypy: $(uv run mypy --version)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Dev container is ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Quick start commands:"
echo "  • ./scripts/check-all.sh     # Run all quality checks"
echo "  • uv run pytest -n auto      # Run all tests (parallel mode)"
echo "  • uv run ruff check .        # Lint code"
echo "  • uv run mypy src/ tests/    # Type check"
echo ""
