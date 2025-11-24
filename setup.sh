#!/bin/bash
# Setup script for ERCOT MCP Server

set -e

echo "================================================"
echo "ERCOT MCP Server - Setup"
echo "================================================"
echo ""

# Parse arguments
SETUP_MODE="dev"  # default to dev mode
if [ "$1" == "--bundle" ]; then
    SETUP_MODE="bundle"
fi

# Check Python version
echo "Checking Python version..."
python3 --version

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"; then
    echo "❌ Error: Python 3.9 or higher is required"
    exit 1
fi

echo "✓ Python version OK"
echo ""

if [ "$SETUP_MODE" == "bundle" ]; then
    # Bundle mode: Install dependencies to lib/ folder
    echo "Installing dependencies to lib/ folder for bundling..."
    rm -rf lib
    python3 -m pip install --target=lib -r requirements.txt
    echo "✓ Dependencies installed to lib/ ($(du -sh lib | cut -f1))"
    echo ""
    echo "================================================"
    echo "Bundle Setup Complete!"
    echo "================================================"
    echo ""
    echo "Next steps:"
    echo "  1. Package the extension:"
    echo "     make bundle"
    echo "  2. Install in Claude Code:"
    echo "     Settings → Extensions → Install from .mcpb file"
    echo ""
else
    # Dev mode: Create virtual environment
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
    echo ""

    # Activate and install
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "✓ Dependencies installed"
    echo ""
fi

# Setup environment file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your ERCOT API credentials!"
    echo "   ERCOTUSER=your_username"
    echo "   ERCOTPASS=your_password"
else
    echo "✓ .env file already exists"
fi
echo ""

if [ "$SETUP_MODE" == "dev" ]; then
    echo "================================================"
    echo "Dev Setup Complete!"
    echo "================================================"
    echo ""
    echo "Next steps:"
    echo "  1. Edit .env and add your ERCOT credentials"
    echo "  2. Activate the virtual environment:"
    echo "     source venv/bin/activate"
    echo "  3. Run tests:"
    echo "     python3 -m pytest tests/ -v"
    echo "  4. Start MCP server:"
    echo "     python3 -m server"
    echo ""
fi
