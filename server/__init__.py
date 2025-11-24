"""
ERCOT MCP Server - Model Context Protocol server for ERCOT public API
"""

__version__ = "0.1.0"

# Export main client and utilities
from .client import ErcotAPIClient, fetch_ercot_data
from .endpoints import list_endpoints, get_endpoint_spec
from .load import get_vintage_forecast, get_net_load_forecast
from .forecasting import day_ahead_forecast, rolling_forecast_cv, create_rolling_splits

__all__ = [
    "ErcotAPIClient",
    "fetch_ercot_data",
    "list_endpoints",
    "get_endpoint_spec",
    "get_vintage_forecast",
    "get_net_load_forecast",
    "day_ahead_forecast",
    "rolling_forecast_cv",
    "create_rolling_splits",
]
