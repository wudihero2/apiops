#!/bin/bash
set -e

echo "=========================================="
echo "Installing opsctl"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Install opsctl
echo ""
echo "📦 Installing opsctl..."
pip3 install -e .

echo ""
echo "=========================================="
echo "✅ Installation complete!"
echo "=========================================="
echo ""
echo "📝 Next steps:"
echo ""
echo "1. Configure opsctl:"
echo "   opsctl config set --api-url <url> --api-key <key>"
echo ""
echo "2. Test the connection:"
echo "   opsctl config check"
echo ""
echo "3. Get help:"
echo "   opsctl --help"
echo ""
