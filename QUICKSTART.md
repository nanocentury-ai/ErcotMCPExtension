# ERCOT MCP Server - Quick Start Guide

## Installation

### 1. Prerequisites

- Python 3.10 or higher
- ERCOT public API credentials ([register here](https://apiexplorer.ercot.com/))

### 2. Install Package

```bash
cd python_mcp

# Create and activate virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install in development mode
python3 -m pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

### 3. Configure Credentials

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your credentials
# ERCOTUSER=your_username
# ERCOTPASS=your_password
```

## Usage

### Option 1: Run as MCP Server

This is the primary use case - running as an MCP server for Claude Code or other MCP clients.

```bash
# Start the server
python -m ercot_mcp

# Or using make
make run
```

The server will listen on stdin/stdout following MCP protocol.

### Option 2: Use Client Directly (Testing)

For development and testing, you can use the client directly:

```python
from ercot_mcp.client import ErcotAPIClient

# Initialize client
client = ErcotAPIClient()

# Fetch data
df = client.fetch_data(
    endpoint_name="da_prices",
    date_from="2024-01-01"
)

print(df.head())
```

Run the example script:
```bash
python example_usage.py
```

## Quick Examples

### 1. List Available Endpoints

```python
from ercot_mcp.endpoints import list_endpoints

# List all endpoints
specs = list_endpoints("all")
for spec in specs:
    print(f"{spec.name}: {spec.summary}")

# List only price endpoints
price_specs = list_endpoints("prices")
```

### 2. Fetch Day-Ahead Prices

```python
from ercot_mcp.client import ErcotAPIClient

client = ErcotAPIClient()

# Single day
df = client.fetch_data(
    endpoint_name="da_prices",
    date_from="2024-02-01"
)

# Date range
df = client.fetch_data(
    endpoint_name="da_prices",
    date_from="2024-02-01",
    date_to="2024-02-07"
)

# Specific settlement point
df = client.fetch_data(
    endpoint_name="da_prices",
    date_from="2024-02-01",
    settlement_point="HB_NORTH"
)
```

### 3. Fetch Load Forecast

```python
# Get system load forecast
df = client.fetch_data(
    endpoint_name="ercot_load_forecast",
    date_from="2024-02-01",
    date_to="2024-02-07"
)

# Check the forecast models
print(df["Model"].unique())
```

### 4. Fetch Real-Time Prices

```python
# RT prices (5-minute intervals)
df = client.fetch_data(
    endpoint_name="rt_prices",
    date_from="2024-02-01",
    settlement_point="HB_NORTH",
    size=50000  # 5-min data needs higher limit
)

# Check the granularity
print(f"Records: {len(df)}")
print(f"Date range: {df['DATETIME'].min()} to {df['DATETIME'].max()}")
```

### 5. Get Endpoint Information

```python
from ercot_mcp.endpoints import get_endpoint_spec

# Inspect an endpoint before using
spec = get_endpoint_spec("da_prices")
print(f"URL: {spec.url}")
print(f"Date key: {spec.date_key}")
print(f"Valid params: {spec.valid_parameters}")
```

## Testing

### Run All Tests

```bash
# Using pytest
pytest

# Using make
make test

# Verbose output
pytest -v

# Run specific test file
pytest tests/test_auth.py
```

### Run Specific Test Categories

```bash
# Only fast unit tests (no API calls)
pytest -v

# Skip slow tests
pytest -m "not slow"
```

## Development

### Code Formatting

```bash
# Format code
make format

# Or directly
black ercot_mcp/ tests/
```

### Linting

```bash
# Lint code
make lint

# Or directly
ruff check ercot_mcp/ tests/
```

### Clean Build Artifacts

```bash
make clean
```

## Common Issues

### Issue: Authentication Failed

**Error:** `ValueError: Authentication failed - check credentials`

**Solution:**
1. Verify `.env` file exists with correct credentials
2. Check that ERCOTUSER and ERCOTPASS are set correctly
3. Test credentials at https://apiexplorer.ercot.com/

### Issue: Endpoint Not Found

**Error:** `ValueError: Unknown endpoint: xyz`

**Solution:**
Use `list_endpoints()` to see available endpoints:
```python
from ercot_mcp.endpoints import list_endpoints
specs = list_endpoints("all")
print([s.name for s in specs])
```

### Issue: No Data Returned

**Possible causes:**
1. Date range too far in the past (data retention limits)
2. Date format incorrect (use YYYY-MM-DD)
3. Invalid settlement point name

**Debug:**
```python
# Check endpoint info
spec = get_endpoint_spec("da_prices")
print(spec.valid_parameters)

# Try with minimal parameters first
df = client.fetch_data("da_prices", date_from="2024-01-01")
```

### Issue: Token Expired During Long Session

**Solution:** Tokens automatically refresh after 1 hour. If you see authentication errors during long-running processes, the next API call will automatically fetch a new token.

## MCP Configuration

To use with Claude Code or other MCP clients, add to your MCP settings:

```json
{
  "mcpServers": {
    "ercot": {
      "command": "python",
      "args": ["-m", "ercot_mcp"],
      "env": {
        "ERCOTUSER": "your_username",
        "ERCOTPASS": "your_password"
      }
    }
  }
}
```

Or use a `.env` file and reference it:

```json
{
  "mcpServers": {
    "ercot": {
      "command": "python",
      "args": ["-m", "ercot_mcp"],
      "cwd": "/path/to/python_mcp"
    }
  }
}
```

## Available Endpoints

### Prices (5 endpoints)
- `da_prices` - Day-ahead settlement point prices
- `rt_prices` - Real-time settlement point prices (5-min)
- `ancillary_prices` - Ancillary service prices
- `da_system_lambda` - Day-ahead system lambda
- `rt_system_lambda` - Real-time system lambda (5-min)

### Forecasts (4 endpoints)
- `ercot_load_forecast` - System load forecast by model
- `ercot_zone_load_forecast` - Zone load forecast by model
- `solar_system_forecast` - Solar generation forecast
- `wind_system_forecast` - Wind generation forecast

### Actuals (3 endpoints)
- `ercot_actual_load` - Actual system load
- `wind_prod_5min` - Actual wind production (5-min)
- `solar_prod_5min` - Actual solar production (5-min)

### Market Data (12 endpoints)
- `sixty_dam_energy_only_offers` - 60-day DAM offers
- `sixty_dam_awards` - 60-day DAM awards
- `energybids` - 60-day energy bids
- `gen_data` - 60-day generation resource data
- `twodayAS` - 2-day ancillary service offers
- And 7 more SCED-related endpoints...

### Other (2 endpoints)
- `ercot_outages` - Resource outage capacity
- `binding_constraints` - Transmission constraint shadow prices

## Next Steps

1. **Explore the data:** Run `example_usage.py` to see various fetching patterns
2. **Read the architecture:** See `ARCHITECTURE.md` for Julia→Python mapping
3. **Check the mapping:** See `../MCP_TOOLS_MAPPING.md` for full tool specifications
4. **Phase 2 features:** Batch fetching and advanced forecasting (coming soon)

## Getting Help

- **Julia source:** Compare with `/src/` directory for reference implementation
- **ERCOT API docs:** https://developer.ercot.com/
- **API Explorer:** https://apiexplorer.ercot.com/
- **MCP Specification:** https://modelcontextprotocol.io/

## Performance Tips

1. **Use `size` parameter:** Default is 100,000 records. Adjust as needed.
2. **Filter by settlement point:** Reduces response size significantly
3. **Batch large date ranges:** For Phase 2, use `batch_fetch_ercot_data`
4. **Cache results:** Store DataFrames locally for repeated analysis

## Data Format

All DataFrames include a standardized `DATETIME` column regardless of the original ERCOT format. The normalization handles 7 different datetime encoding patterns automatically.

```python
df = client.fetch_data("da_prices", date_from="2024-01-01")

# Always has DATETIME column
assert "DATETIME" in df.columns

# Always cleaned column names (no spaces or hyphens)
assert all(" " not in col for col in df.columns)
assert all("-" not in col for col in df.columns)
```
