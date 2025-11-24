"""
ERCOT API Client

Core functionality for making API calls and parsing responses.
Converted from ErcotMagic.jl:ercot_api_call and parse_ercot_response
"""

from typing import Optional, Dict, Any
import os
import requests
import pandas as pd
from datetime import date

from .auth import ErcotAuth, get_global_auth
from .endpoints import get_endpoint_spec, validate_endpoint, get_date_key, get_url
from .utils import (
    normalize_ercot_dataframe,
    build_query_params,
    validate_parameters,
)


class ErcotAPIClient:
    """
    Client for interacting with ERCOT public API.

    Source: ErcotMagic.jl:108-247

    Usage:
        client = ErcotAPIClient()
        df = client.fetch_data("da_prices", date_from="2024-01-01")
    """

    def __init__(self, auth: Optional[ErcotAuth] = None):
        """
        Initialize ERCOT API client.

        Args:
            auth: Optional ErcotAuth instance. If None, uses global auth.
        """
        self.auth = auth or get_global_auth()

    def ercot_api_call(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Make authenticated API call to ERCOT.

        Source: ErcotMagic.jl:108-120 (ercot_api_call)

        Args:
            url: Full API endpoint URL
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            JSON response as dictionary

        Raises:
            requests.HTTPError: If API call fails
            TimeoutError: If request times out
        """
        headers = self.auth.get_auth_headers()
        headers["Accept"] = "application/json"

        # Add subscription key (required by ERCOT API)
        subscription_key = os.getenv("ERCOTKEY")
        if not subscription_key:
            raise ValueError(
                "ERCOT API subscription key not found. "
                "When using as MCP extension, configure API Key in extension settings. "
                "When using standalone, set ERCOTKEY environment variable."
            )
        headers["Ocp-Apim-Subscription-Key"] = subscription_key

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ValueError(
                    "Authentication failed - token may have expired. Try again."
                ) from e
            elif e.response.status_code == 404:
                raise ValueError(f"Endpoint not found: {url}") from e
            elif e.response.status_code == 400:
                raise ValueError(
                    f"Bad request - check parameters: {params}"
                ) from e
            else:
                raise

        except requests.exceptions.Timeout:
            raise TimeoutError(
                f"API request timed out after {timeout} seconds"
            ) from None

    def parse_ercot_response(self, response: Dict[str, Any]) -> pd.DataFrame:
        """
        Parse ERCOT API JSON response to DataFrame.

        Source: ErcotMagic.jl:122-161 (parse_ercot_response)

        ERCOT API returns data in format:
        {
            "fields": [{"name": "col1", ...}, ...],
            "data": [[val1, val2, ...], ...],
            "_meta": {...}
        }

        Args:
            response: JSON response from API

        Returns:
            Pandas DataFrame with parsed data

        Raises:
            ValueError: If response format is unexpected
        """
        if not isinstance(response, dict):
            raise ValueError("Expected dictionary response from API")

        # Check for data key
        if "data" not in response:
            raise ValueError(
                f"Expected 'data' key in response. Got keys: {list(response.keys())}"
            )

        data = response["data"]

        # Handle empty response
        if not data:
            return pd.DataFrame()

        # Extract column names from fields metadata
        if "fields" in response and isinstance(response["fields"], list):
            columns = [field["name"] for field in response["fields"]]
            df = pd.DataFrame(data, columns=columns)
        else:
            # Fallback to default column names if fields not available
            df = pd.DataFrame(data)

        # Normalize the DataFrame
        df = normalize_ercot_dataframe(df)

        return df

    def fetch_data(
        self,
        endpoint_name: str,
        date_from: str,
        date_to: Optional[str] = None,
        settlement_point: Optional[str] = None,
        resource_type: Optional[str] = None,
        size: int = 100000,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Fetch data from ERCOT API endpoint.

        Source: ErcotMagic.jl:206-247 (get_data variants)

        This is the primary interface for retrieving ERCOT data.

        Args:
            endpoint_name: Name of endpoint (e.g., "da_prices", "ercot_load_forecast")
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format (optional, defaults to date_from)
            settlement_point: Settlement point filter (for price endpoints)
            resource_type: Resource type filter (for SCED endpoints)
            size: Maximum number of records to retrieve (default 100000)
            **kwargs: Additional endpoint-specific parameters

        Returns:
            DataFrame with requested data and standardized DATETIME column

        Raises:
            ValueError: If endpoint_name is invalid or parameters are incorrect

        Examples:
            # Get day-ahead prices for a single day
            df = client.fetch_data("da_prices", date_from="2024-01-01")

            # Get real-time prices for a date range at a specific node
            df = client.fetch_data(
                "rt_prices",
                date_from="2024-01-01",
                date_to="2024-01-07",
                settlement_point="HB_NORTH"
            )

            # Get load forecast
            df = client.fetch_data("ercot_load_forecast", date_from="2024-01-01")
        """
        # Validate endpoint
        if not validate_endpoint(endpoint_name):
            raise ValueError(
                f"Unknown endpoint: {endpoint_name}. "
                f"Use list_endpoints() to see available endpoints."
            )

        # Get endpoint specification
        spec = get_endpoint_spec(endpoint_name)

        # Build query parameters
        params = build_query_params(
            endpoint_name=endpoint_name,
            date_key=spec.date_key,
            date_from=date_from,
            date_to=date_to,
            settlementPoint=settlement_point,
            resourceType=resource_type,
            size=size,
            **kwargs,
        )

        # Validate parameters
        params = validate_parameters(
            endpoint_name, params, spec.valid_parameters
        )

        # Make API call
        response = self.ercot_api_call(spec.url, params)

        # Parse response
        df = self.parse_ercot_response(response)

        return df

    def list_endpoints(self, category: str = "all") -> pd.DataFrame:
        """
        List available ERCOT API endpoints.

        Args:
            category: Filter by category ("prices", "forecasts", "actuals", "market_data", "all")

        Returns:
            DataFrame with endpoint information
        """
        from .endpoints import list_endpoints

        specs = list_endpoints(category)
        return pd.DataFrame([spec.dict() for spec in specs])


# Convenience function for direct use
def fetch_ercot_data(
    endpoint_name: str,
    date_from: str,
    date_to: Optional[str] = None,
    **kwargs,
) -> pd.DataFrame:
    """
    Convenience function to fetch ERCOT data without instantiating client.

    Args:
        endpoint_name: Name of endpoint
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD, optional)
        **kwargs: Additional parameters

    Returns:
        DataFrame with requested data
    """
    client = ErcotAPIClient()
    return client.fetch_data(endpoint_name, date_from, date_to, **kwargs)
