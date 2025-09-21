#!/bin/bash
# PATH setup script for Fast Fixup Finder (Unix/Linux/macOS)

echo "🛠️  Fast Fixup Finder PATH Setup (Unix/Linux/macOS)"
echo "=================================================="

# Run the Python setup script
python3 setup_path.py

echo ""
echo "💡 Quick manual setup (if automatic setup failed):"
echo "   Add this line to your ~/.bashrc, ~/.zshrc, or ~/.profile:"
echo "   export PATH=\"\$PATH:\$(python3 -m site --user-base)/bin\""
echo ""
echo "   Then run: source ~/.bashrc (or restart terminal)"