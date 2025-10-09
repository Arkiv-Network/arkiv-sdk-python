#!/bin/bash
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Arkiv SDK Publishing Wizard"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: pyproject.toml not found. Run this from the project root."
    exit 1
fi

# Check for required tokens
MISSING_TOKENS=()
if [ -z "$PYPI_TOKEN" ]; then
    MISSING_TOKENS+=("PYPI_TOKEN")
fi
if [ -z "$TESTPYPI_TOKEN" ]; then
    MISSING_TOKENS+=("TESTPYPI_TOKEN")
fi

if [ ${#MISSING_TOKENS[@]} -gt 0 ]; then
    echo "❌ Error: Required environment variables not set:"
    echo ""
    for token in "${MISSING_TOKENS[@]}"; do
        echo "   ✗ $token"
    done
    echo ""
    echo "📋 Setup Instructions:"
    echo ""
    echo "1. Create accounts (if you haven't already):"
    echo "   • PyPI:     https://pypi.org/account/register/"
    echo "   • TestPyPI: https://test.pypi.org/account/register/"
    echo ""
    echo "2. Generate API tokens:"
    echo "   • PyPI token:     https://pypi.org/manage/account/token/"
    echo "   • TestPyPI token: https://test.pypi.org/manage/account/token/"
    echo ""
    echo "3. Set environment variables:"
    echo "   export PYPI_TOKEN='pypi-AgEIcHlwaS5vcmcC...'"
    echo "   export TESTPYPI_TOKEN='pypi-AgEOdGVzdC5weXBpLm9yZwI...'"
    echo ""
    echo "4. Add to your shell profile (~/.bashrc or ~/.zshrc) to persist:"
    echo "   echo 'export PYPI_TOKEN=\"pypi-...\"' >> ~/.bashrc"
    echo "   echo 'export TESTPYPI_TOKEN=\"pypi-...\"' >> ~/.bashrc"
    echo "   source ~/.bashrc"
    echo ""
    echo "📖 For detailed instructions, see: PYPI_TOKENS.md"
    echo ""
    exit 1
fi

echo "✅ PyPI tokens configured"
echo ""

# Get current version
CURRENT_VERSION=$(grep "^version = " pyproject.toml | cut -d'"' -f2)
echo "📌 Current version: $CURRENT_VERSION"
echo ""

# Run quality checks
echo "🔍 Running quality checks..."
./scripts/check-all.sh
if [ $? -ne 0 ]; then
    echo "❌ Quality checks failed. Fix issues before publishing."
    exit 1
fi
echo "✅ Quality checks passed!"
echo ""

# Clean old builds
echo "🧹 Cleaning old builds..."
rm -rf dist/
echo "✅ Cleaned!"
echo ""

# Build package
echo "🔨 Building package..."
uv build
if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi
echo "✅ Build successful!"
echo ""

# Show built files
echo "📦 Built packages:"
ls -lh dist/
echo ""

# Ask what to do
echo "What would you like to do?"
echo "  1) Publish to TestPyPI (recommended first)"
echo "  2) Publish to PyPI (production)"
echo "  3) Exit"
echo ""
read -p "Choose (1/2/3): " choice

case $choice in
    1)
        echo ""
        echo "📤 Publishing to TestPyPI..."
        uv publish --token "$TESTPYPI_TOKEN" --publish-url https://test.pypi.org/legacy/
        echo ""
        echo "✅ Published to TestPyPI!"
        echo ""
        echo "📥 Test installation:"
        echo "   uv pip install testcontainers
        echo "   uv pip install -i https://test.pypi.org/simple/ arkiv-sdk"
        ;;
    2)
        echo ""
        read -p "⚠️  This will publish to PRODUCTION PyPI. Continue? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            echo "❌ Cancelled"
            exit 0
        fi
        echo ""
        echo "📤 Publishing to PyPI..."
        uv publish --token "$PYPI_TOKEN"
        echo ""
        echo "✅ Published to PyPI!"
        echo ""
        echo "🏷️  Don't forget to tag the release:"
        echo "   git tag -a v$CURRENT_VERSION -m 'Release version $CURRENT_VERSION'"
        echo "   git push origin v$CURRENT_VERSION"
        echo ""
        echo "📥 Users can now install:"
        echo "   pip install arkiv-sdk"
        ;;
    3)
        echo "👋 Goodbye!"
        exit 0
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Done!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
