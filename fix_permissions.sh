#!/bin/bash
# Quick fix for permission issues with user-installed fastfixupfinder

echo "🔧 Fast Fixup Finder Permission Fix"
echo "===================================="

# Get user bin path
USER_BIN=$(python3 -m site --user-base)/bin
FASTFIXUP_EXE="$USER_BIN/fastfixupfinder"

echo "Checking: $FASTFIXUP_EXE"

if [ ! -f "$FASTFIXUP_EXE" ]; then
    echo "✗ Executable not found at $FASTFIXUP_EXE"
    echo "  Make sure you've installed with: pip install --user ."
    exit 1
fi

if [ ! -x "$FASTFIXUP_EXE" ]; then
    echo "⚠  Fixing executable permissions..."
    chmod +x "$FASTFIXUP_EXE"
    if [ $? -eq 0 ]; then
        echo "✓ Fixed permissions for $FASTFIXUP_EXE"
    else
        echo "✗ Failed to fix permissions"
        exit 1
    fi
else
    echo "✓ Permissions are already correct"
fi

# Test the command
echo ""
echo "🧪 Testing command..."
if "$FASTFIXUP_EXE" --version >/dev/null 2>&1; then
    echo "✓ fastfixupfinder command works!"
    echo ""
    echo "You can now use: fastfixupfinder --help"
else
    echo "⚠  Command still not working. Try:"
    echo "   1. Restart your terminal"
    echo "   2. Check PATH with: echo \$PATH | grep -q '$USER_BIN'"
    echo "   3. Use module syntax: python3 -m fastfixupfinder.cli --help"
fi