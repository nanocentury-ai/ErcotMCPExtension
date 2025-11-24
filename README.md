# ERCOT MCP Extension

A Model Context Protocol (MCP) extension for Claude Code providing tools to access ERCOT (Electric Reliability Council of Texas) public API data and forecasting capabilities.

## Features

- **7 MCP Tools**: Complete access to ERCOT data and forecasting
- **Authentication**: Automatic token management with caching and refresh
- **34+ Endpoints**: Comprehensive access to prices, forecasts, load, wind, solar, and actuals
- **Data Normalization**: Automatic cleaning and standardization of API responses
- **Price Forecasting**: Machine learning-based next-day price predictions
- **Bundled Dependencies**: All Python packages included - no pip install needed!

## Quick Install

1. Download `ErcotMCPExtension.mcpb` (90MB)
2. Install in Claude Code: Settings → Extensions → Install from .mcpb file
3. Configure your ERCOT API credentials in extension settings
4. Start using the tools!

See [INSTALLATION.md](INSTALLATION.md) for detailed instructions.

## Configuration

Get your free ERCOT API credentials at: https://apiexplorer.ercot.com/

Configure in Claude Code extension settings:
- **API User Name**: Your ERCOT username
- **API Password**: Your ERCOT password
- **API Key**: Your ERCOT API key

## Available Tools

1. **fetch_ercot_data**: Fetch data from any of 34+ ERCOT endpoints (prices, load, wind, solar, etc.)
2. **list_available_endpoints**: Browse all available endpoints with descriptions
3. **normalize_ercot_dataframe**: Clean and standardize API responses
4. **get_endpoint_info**: Get detailed information about a specific endpoint
5. **get_net_load_forecast**: Get ERCOT's official net load forecast
6. **day_ahead_price_forecast**: Machine learning-based next-day price predictions
7. **rolling_forecast_cross_validation**: Evaluate forecast accuracy with cross-validation

## Development

For developers wanting to modify the extension:

### Local Development Setup

```bash
# Setup development environment (creates venv)
./setup.sh
# or
make setup-dev

# Activate virtual environment
source venv/bin/activate

# Run tests
make test

# Run server locally
make run
```

### Building the Extension Bundle

```bash
# Install dependencies to lib/ folder and create .mcpb bundle
make bundle

# This will:
# 1. Install all dependencies to lib/ folder (304MB)
# 2. Create ErcotMCPExtension.mcpb (90MB compressed)
# 3. Generate SHA256 checksum
```

The `lib/` folder is not committed to git - it's generated during the build process.

## Architecture

- **Server**: Python MCP server with 7 tools
- **Dependencies**: Bundled in `lib/` folder (304MB uncompressed, 90MB in .mcpb)
- **Forecasting**: Linear regression on hour-of-day features
- **Authentication**: Bearer token with automatic refresh
