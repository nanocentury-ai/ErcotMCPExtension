#!/bin/bash
# Test script to run MCP inspector with proper environment setup

set -e

echo "================================================"
echo "ERCOT MCP Extension - Inspector Test"
echo "================================================"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo ""
    echo "Please create a .env file with your ERCOT credentials:"
    echo "  ERCOTUSER=your_username"
    echo "  ERCOTPASS=your_password"
    echo "  ERCOTKEY=your_api_key (optional)"
    echo ""
    exit 1
fi

# Load environment variables from .env
echo "Loading credentials from .env..."
export $(grep -v '^#' .env | xargs)

# Verify credentials are set
if [ -z "$ERCOTUSER" ] || [ -z "$ERCOTPASS" ]; then
    echo "❌ Error: ERCOTUSER or ERCOTPASS not set in .env file"
    exit 1
fi

echo "✅ Credentials loaded"
echo ""

# Set PYTHONPATH to include lib folder
export PYTHONPATH="$(pwd):$(pwd)/lib"

echo "Starting MCP Inspector..."
echo "This will open a web UI where you can test the tools"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================================"
echo ""

# Run the MCP inspector
npx @modelcontextprotocol/inspector python3 -m server
