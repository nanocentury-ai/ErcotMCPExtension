"""
ERCOT MCP Server

Model Context Protocol server providing tools for ERCOT public API access.
"""

import asyncio
import json
from typing import Any, Dict, Optional
from datetime import datetime

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
import mcp.server.stdio

from .client import ErcotAPIClient, fetch_ercot_data
from .endpoints import list_endpoints, get_endpoint_spec
from .utils import normalize_ercot_dataframe
from .forecasting import day_ahead_forecast, rolling_forecast_cv
from .load import get_net_load_forecast
import pandas as pd


# Initialize server
app = Server("ercot-mcp-server")

# Initialize client (will be created on first use)
_client: Optional[ErcotAPIClient] = None


def get_client() -> ErcotAPIClient:
    """Get or create global API client"""
    global _client
    if _client is None:
        _client = ErcotAPIClient()
    return _client


def df_to_json_string(df: pd.DataFrame, max_rows: int = 1000) -> str:
    """
    Convert DataFrame to formatted JSON string for MCP response.

    Args:
        df: DataFrame to convert
        max_rows: Maximum rows to include (prevents huge responses)

    Returns:
        Formatted JSON string
    """
    if len(df) > max_rows:
        result = {
            "warning": f"Result truncated to {max_rows} rows (total: {len(df)} rows)",
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "columns": list(df.columns),
            "data": df.head(max_rows).to_dict(orient="records"),
        }
    else:
        result = {
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "columns": list(df.columns),
            "data": df.to_dict(orient="records"),
        }

    return json.dumps(result, indent=2, default=str)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available MCP tools.

    Phase 1 (MVP) tools as defined in MCP_TOOLS_MAPPING.md
    """
    return [
        Tool(
            name="fetch_ercot_data",
            description="""Fetch data from ERCOT public API endpoints.

Primary data fetching interface for ERCOT market data including prices, forecasts, and actuals.

Parameters:
- endpoint_name: Endpoint identifier (e.g., "da_prices", "ercot_load_forecast")
- date_from: Start date in YYYY-MM-DD format
- date_to: End date in YYYY-MM-DD format (optional, defaults to date_from)
- settlement_point: Settlement point filter for price endpoints (optional, e.g., "HB_NORTH")
- resource_type: Resource type filter for SCED endpoints (optional)
- size: Maximum records to retrieve (default 100000)

Returns DataFrame with standardized DATETIME column and requested data.

Examples:
- Day-ahead prices: fetch_ercot_data("da_prices", "2024-01-01")
- Load forecast: fetch_ercot_data("ercot_load_forecast", "2024-01-01", "2024-01-07")
- RT prices at node: fetch_ercot_data("rt_prices", "2024-01-01", settlement_point="HB_NORTH")
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "endpoint_name": {
                        "type": "string",
                        "description": "ERCOT endpoint name (e.g., 'da_prices', 'ercot_load_forecast')",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (optional)",
                    },
                    "settlement_point": {
                        "type": "string",
                        "description": "Settlement point filter (optional, e.g., 'HB_NORTH')",
                    },
                    "resource_type": {
                        "type": "string",
                        "description": "Resource type filter for SCED endpoints (optional)",
                    },
                    "size": {
                        "type": "integer",
                        "description": "Maximum records to retrieve (default 100000)",
                        "default": 100000,
                    },
                },
                "required": ["endpoint_name", "date_from"],
            },
        ),
        Tool(
            name="list_available_endpoints",
            description="""List available ERCOT API endpoints with metadata.

Browse the 34+ available endpoints organized by category.

Parameters:
- category: Filter by category (optional)
  - "prices": Day-ahead and real-time prices, system lambda
  - "forecasts": Load, wind, and solar forecasts
  - "actuals": Actual load and generation data
  - "market_data": 60-day offers, bids, awards, SCED data
  - "all": All endpoints (default)

Returns DataFrame with:
- name: Endpoint identifier
- url: API endpoint URL
- summary: Description
- date_key: Primary date parameter name
- category: Category grouping
- valid_parameters: Accepted query parameters

Use this to discover available data sources before calling fetch_ercot_data.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category",
                        "enum": ["all", "prices", "forecasts", "actuals", "market_data", "other"],
                        "default": "all",
                    },
                },
            },
        ),
        Tool(
            name="normalize_ercot_dataframe",
            description="""Clean and standardize ERCOT API response DataFrame.

Applies complete normalization pipeline:
1. Remove spaces and hyphens from column names
2. Construct standardized DATETIME column from various ERCOT date formats
3. Ensure proper data types

ERCOT uses 7 different datetime encoding patterns - this tool automatically
detects and normalizes them into a single DATETIME column.

Parameters:
- dataframe_json: DataFrame as JSON string (from previous API call)

Returns:
- Normalized DataFrame with clean column names and DATETIME column

Typically used when you need to post-process raw API responses, but
fetch_ercot_data already applies this automatically.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataframe_json": {
                        "type": "string",
                        "description": "DataFrame as JSON string to normalize",
                    },
                },
                "required": ["dataframe_json"],
            },
        ),
        Tool(
            name="get_endpoint_info",
            description="""Get detailed information about a specific ERCOT endpoint.

Returns complete specification including:
- URL and date key
- Valid parameters
- Summary description
- Category

Parameters:
- endpoint_name: Name of the endpoint to inspect

Use this before calling fetch_ercot_data to understand what parameters
an endpoint accepts.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "endpoint_name": {
                        "type": "string",
                        "description": "ERCOT endpoint name",
                    },
                },
                "required": ["endpoint_name"],
            },
        ),
        Tool(
            name="get_net_load_forecast",
            description="""Get net load forecast (load minus renewable generation).

Net load = System Load - Wind Generation - Solar Generation

This is a critical metric for price forecasting as it represents the
demand that must be met by dispatchable generation.

Parameters:
- date_from: Start date in YYYY-MM-DD format (default: tomorrow)
- date_to: End date in YYYY-MM-DD format (optional)

Returns DataFrame with:
- DATETIME: Timestamp
- MedianLoadForecast: System load forecast
- Renewables: Combined wind + solar forecast
- NetLoad: Load - Renewables

Example:
- Tomorrow's net load: get_net_load_forecast()
- Week ahead: get_net_load_forecast("2024-01-01", "2024-01-07")
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (optional, defaults to tomorrow)",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (optional)",
                    },
                },
            },
        ),
        Tool(
            name="day_ahead_price_forecast",
            description="""Generate day-ahead price forecast using polynomial regression.

Trains on recent historical data to predict system lambda (energy prices)
based on net load forecasts. Uses polynomial regression to capture the
non-linear relationship between load and price.

Parameters:
- forecast_date: Date to forecast in YYYY-MM-DD format (default: tomorrow)
- training_days: Number of recent days to train on (default: 15, range: 7-30)
- polynomial_degree: Degree of polynomial features (default: 3, range: 1-5)

Returns:
- forecast: DataFrame with hourly price predictions
- training_performance: MAE, RMSE, R² on training data
- parameters: Forecast configuration used

Model details:
- Features: NetLoad^1, NetLoad^2, ..., NetLoad^degree
- Target: System Lambda ($/MWh)
- Algorithm: Linear regression on polynomial features

Example:
- Forecast tomorrow with defaults: day_ahead_price_forecast()
- Custom config: day_ahead_price_forecast("2024-01-15", training_days=20, polynomial_degree=4)
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "forecast_date": {
                        "type": "string",
                        "description": "Date to forecast in YYYY-MM-DD format (optional, defaults to tomorrow)",
                    },
                    "training_days": {
                        "type": "integer",
                        "description": "Number of recent days to train on (default: 15)",
                        "default": 15,
                    },
                    "polynomial_degree": {
                        "type": "integer",
                        "description": "Degree of polynomial features (default: 3)",
                        "default": 3,
                    },
                },
            },
        ),
        Tool(
            name="rolling_forecast_cross_validation",
            description="""Run rolling forecast cross-validation to evaluate model performance.

Performs time-series cross-validation by training on historical data and
testing on subsequent days. Useful for validating forecasting approach
before deploying operationally.

Parameters:
- start_date: Start date in YYYY-MM-DD format (default: 30 days ago)
- end_date: End date in YYYY-MM-DD format (default: yesterday)
- initial_training_days: Number of initial days to train on (default: 15)
- polynomial_degree: Degree of polynomial features (default: 3)
- expanding_window: If True, expand training window; if False, use fixed window (default: True)

Returns:
- predictions: DataFrame with all hourly predictions vs actuals
- daily_metrics: Per-day MAE, RMSE, R² performance
- overall_performance: Aggregate metrics across all forecasts
- parameters: CV configuration used

Cross-validation strategy:
- Expanding window: Train on day 1-N, predict N+1; then 1-(N+1), predict N+2, etc.
- Fixed window: Train on last N days, predict next day; slide forward

Example:
- Validate on last 30 days: rolling_forecast_cross_validation()
- Custom period: rolling_forecast_cross_validation("2024-01-01", "2024-01-31", initial_training_days=20)
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (optional, defaults to 30 days ago)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (optional, defaults to yesterday)",
                    },
                    "initial_training_days": {
                        "type": "integer",
                        "description": "Number of initial days to train on (default: 15)",
                        "default": 15,
                    },
                    "polynomial_degree": {
                        "type": "integer",
                        "description": "Degree of polynomial features (default: 3)",
                        "default": 3,
                    },
                    "expanding_window": {
                        "type": "boolean",
                        "description": "If True, expand training window; if False, use fixed window (default: True)",
                        "default": True,
                    },
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """
    Handle tool execution.
    """
    try:
        if name == "fetch_ercot_data":
            # Extract parameters
            endpoint_name = arguments.get("endpoint_name")
            date_from = arguments.get("date_from")
            date_to = arguments.get("date_to")
            settlement_point = arguments.get("settlement_point")
            resource_type = arguments.get("resource_type")
            size = arguments.get("size", 100000)

            # Fetch data
            client = get_client()
            df = client.fetch_data(
                endpoint_name=endpoint_name,
                date_from=date_from,
                date_to=date_to,
                settlement_point=settlement_point,
                resource_type=resource_type,
                size=size,
            )

            # Format response
            result = df_to_json_string(df)
            return [
                TextContent(
                    type="text",
                    text=f"Successfully fetched {len(df)} rows from {endpoint_name}\n\n{result}",
                )
            ]

        elif name == "list_available_endpoints":
            category = arguments.get("category", "all")

            # Get endpoint list
            specs = list_endpoints(category)
            df = pd.DataFrame([spec.dict() for spec in specs])

            # Format response
            result = df_to_json_string(df)
            return [
                TextContent(
                    type="text",
                    text=f"Found {len(df)} endpoints in category '{category}'\n\n{result}",
                )
            ]

        elif name == "normalize_ercot_dataframe":
            dataframe_json = arguments.get("dataframe_json")

            # Parse JSON to DataFrame
            data = json.loads(dataframe_json)
            if isinstance(data, dict) and "data" in data:
                df = pd.DataFrame(data["data"])
            else:
                df = pd.DataFrame(data)

            # Normalize
            df = normalize_ercot_dataframe(df)

            # Format response
            result = df_to_json_string(df)
            return [
                TextContent(
                    type="text",
                    text=f"Normalized DataFrame with {len(df)} rows\n\n{result}",
                )
            ]

        elif name == "get_endpoint_info":
            endpoint_name = arguments.get("endpoint_name")

            # Get spec
            spec = get_endpoint_spec(endpoint_name)

            # Format response
            info = {
                "name": spec.name,
                "url": spec.url,
                "summary": spec.summary,
                "date_key": spec.date_key,
                "category": spec.category,
                "valid_parameters": spec.valid_parameters,
            }

            return [
                TextContent(
                    type="text",
                    text=f"Endpoint Information: {endpoint_name}\n\n{json.dumps(info, indent=2)}",
                )
            ]

        elif name == "get_net_load_forecast":
            date_from = arguments.get("date_from")
            date_to = arguments.get("date_to")

            # Get net load forecast
            client = get_client()
            df = get_net_load_forecast(
                date_from=date_from,
                date_to=date_to,
                client=client,
                size=10000000
            )

            # Format response
            result = df_to_json_string(df)
            return [
                TextContent(
                    type="text",
                    text=f"Net Load Forecast: {len(df)} hours\n\n{result}",
                )
            ]

        elif name == "day_ahead_price_forecast":
            forecast_date = arguments.get("forecast_date")
            training_days = arguments.get("training_days", 15)
            polynomial_degree = arguments.get("polynomial_degree", 3)

            # Generate forecast
            client = get_client()
            forecast_result = day_ahead_forecast(
                forecast_date=forecast_date,
                training_days=training_days,
                polynomial_degree=polynomial_degree,
                client=client
            )

            # Extract forecast DataFrame
            forecast_df = forecast_result["forecast"]

            # Format complete result
            response_data = {
                "forecast_date": str(forecast_result["parameters"]["forecast_date"]),
                "training_period": {
                    "start": str(forecast_result["parameters"]["training_period"][0]),
                    "end": str(forecast_result["parameters"]["training_period"][1]),
                    "days": training_days
                },
                "training_performance": forecast_result["training_performance"],
                "forecast": {
                    "hours": len(forecast_df),
                    "avg_price": float(forecast_df["PredictedLambda"].mean()) if not forecast_df.empty else None,
                    "max_price": float(forecast_df["PredictedLambda"].max()) if not forecast_df.empty else None,
                    "min_price": float(forecast_df["PredictedLambda"].min()) if not forecast_df.empty else None,
                    "data": forecast_df.to_dict(orient="records") if not forecast_df.empty else []
                }
            }

            return [
                TextContent(
                    type="text",
                    text=f"Day-Ahead Price Forecast\n\n{json.dumps(response_data, indent=2, default=str)}",
                )
            ]

        elif name == "rolling_forecast_cross_validation":
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            initial_training_days = arguments.get("initial_training_days", 15)
            polynomial_degree = arguments.get("polynomial_degree", 3)
            expanding_window = arguments.get("expanding_window", True)

            # Run cross-validation
            client = get_client()
            cv_result = rolling_forecast_cv(
                start_date=start_date,
                end_date=end_date,
                initial_training_days=initial_training_days,
                polynomial_degree=polynomial_degree,
                expanding_window=expanding_window,
                client=client
            )

            # Format complete result
            response_data = {
                "parameters": {
                    "start_date": str(cv_result["parameters"]["start_date"]),
                    "end_date": str(cv_result["parameters"]["end_date"]),
                    "initial_training_days": initial_training_days,
                    "polynomial_degree": polynomial_degree,
                    "expanding_window": expanding_window
                },
                "overall_performance": cv_result["overall_performance"],
                "daily_metrics": cv_result["daily_metrics"].to_dict(orient="records"),
                "predictions_sample": cv_result["predictions"].head(100).to_dict(orient="records")
            }

            return [
                TextContent(
                    type="text",
                    text=f"Rolling Forecast Cross-Validation Results\n\n{json.dumps(response_data, indent=2, default=str)}",
                )
            ]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
