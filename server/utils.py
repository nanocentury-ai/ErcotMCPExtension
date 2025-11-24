"""
Data utilities for ERCOT API responses

Converted from src/utils.jl
Handles DataFrame normalization, datetime parsing, and data cleaning.
"""

from datetime import datetime, time, timedelta
from typing import Optional, Dict, Any
import pandas as pd
import re


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize DataFrame column names.

    Source: utils.jl:7-12 (normalize_columnnames!)

    Converts camelCase/snake_case to PascalCase and removes spaces/hyphens.
    This ensures consistent column naming across all ERCOT endpoints.

    Examples:
        settlementPointPrice -> SettlementPointPrice
        delivery_date -> DeliveryDate
        Hour Ending -> HourEnding

    Args:
        df: Input DataFrame

    Returns:
        DataFrame with cleaned column names in PascalCase
    """
    df = df.copy()

    def to_pascal_case(name: str) -> str:
        """Convert various naming conventions to PascalCase"""
        # Remove special characters and split on boundaries
        name = str(name).replace("-", "_").replace(" ", "_")

        # If already PascalCase, return as-is
        if name and name[0].isupper() and "_" not in name.lower():
            return name

        # Handle camelCase: insert underscore before capitals
        import re
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)

        # Split on underscores and capitalize each part
        parts = [part.capitalize() for part in name.split('_') if part]

        return ''.join(parts)

    df.columns = [to_pascal_case(col) for col in df.columns]
    return df


def parse_hour_ending(date: datetime, hour_ending: Any) -> datetime:
    """
    Parse hour-ending format to proper datetime.

    Source: utils.jl:14-24

    ERCOT uses hour-ending notation where:
    - Hour 1 = 00:00-01:00
    - Hour 24 = 23:00-24:00 (shown as "24:00")

    Args:
        date: Base date
        hour_ending: Hour ending value (int or str like "24:00")

    Returns:
        Datetime at the end of the interval
    """
    if isinstance(hour_ending, str):
        if hour_ending == "24:00":
            # Hour 24 = end of day = next day at midnight - 1 hour = 11 PM today
            return date + timedelta(days=1, hours=0) - timedelta(hours=1)
        else:
            # Parse time string like "13:00"
            hour = int(hour_ending.split(":")[0])
            return date + timedelta(hours=hour) - timedelta(hours=1)
    else:
        # Integer hour ending
        return date + timedelta(hours=int(hour_ending)) - timedelta(hours=1)


def add_datetime_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add standardized DATETIME column based on various ERCOT datetime formats.

    Source: utils.jl:29-58 (add_datetime!)

    ERCOT uses 7 different datetime encoding patterns:
    1. DeliveryDate + DeliveryHour + DeliveryInterval (5-min intervals)
    2. IntervalEnding (direct timestamp)
    3. OperatingDay + HourEnding
    4. OperatingDate + HourEnding
    5. DeliveryDate + DeliveryHour (hourly)
    6. DeliveryDate + HourEnding
    7. SCEDTimestamp / SCEDTimeStamp

    Note: Assumes columns have been normalized to PascalCase.

    Args:
        df: Input DataFrame with ERCOT datetime columns

    Returns:
        DataFrame with added DATETIME column

    Raises:
        Warning if no recognizable datetime columns found
    """
    df = df.copy()

    # Pattern 1: DeliveryInterval (5-minute intervals)
    if "DeliveryInterval" in df.columns:
        df["DATETIME"] = (
            pd.to_datetime(df["DeliveryDate"])
            + pd.to_timedelta(df["DeliveryHour"], unit="h")
            + pd.to_timedelta(df["DeliveryInterval"] * 5, unit="m")
        )
        return df

    # Pattern 2: IntervalEnding (direct timestamp)
    if "IntervalEnding" in df.columns:
        df["DATETIME"] = pd.to_datetime(df["IntervalEnding"])
        return df

    # Pattern 3: OperatingDay + HourEnding
    if "OperatingDay" in df.columns and "HourEnding" in df.columns:
        df["DATETIME"] = df.apply(
            lambda row: parse_hour_ending(
                pd.to_datetime(row["OperatingDay"]), row["HourEnding"]
            ),
            axis=1,
        )
        return df

    # Pattern 4: OperatingDate + HourEnding
    if "OperatingDate" in df.columns and "HourEnding" in df.columns:
        df["DATETIME"] = df.apply(
            lambda row: parse_hour_ending(
                pd.to_datetime(row["OperatingDate"]), row["HourEnding"]
            ),
            axis=1,
        )
        return df

    # Pattern 5: DeliveryDate + DeliveryHour (hourly)
    if "DeliveryHour" in df.columns and "DeliveryDate" in df.columns:
        df["DATETIME"] = pd.to_datetime(df["DeliveryDate"]) + pd.to_timedelta(
            df["DeliveryHour"], unit="h"
        )
        return df

    # Pattern 6: DeliveryDate + HourEnding
    if "DeliveryDate" in df.columns and "HourEnding" in df.columns:
        df["DATETIME"] = df.apply(
            lambda row: parse_hour_ending(
                pd.to_datetime(row["DeliveryDate"]), row["HourEnding"]
            ),
            axis=1,
        )
        return df

    # Pattern 7: SCEDTimestamp or SCEDTimeStamp
    if "SCEDTimestamp" in df.columns:
        df["DATETIME"] = pd.to_datetime(df["SCEDTimestamp"])
        return df
    if "SCEDTimeStamp" in df.columns:
        df["DATETIME"] = pd.to_datetime(df["SCEDTimeStamp"])
        return df

    # No datetime columns found
    print("Warning: No datetime columns found in DataFrame")
    return df


def process_5min_to_hourly(df: pd.DataFrame, settlement_column: str = "SettlementPoint") -> pd.DataFrame:
    """
    Aggregate 5-minute real-time prices to hourly averages.

    Source: utils.jl:76-80 (process_5min_settlements_to_hourly)

    Args:
        df: DataFrame with 5-minute data
        settlement_column: Name of settlement point column for grouping

    Returns:
        DataFrame with hourly aggregated data
    """
    df = df.copy()

    # Ensure DATETIME exists
    if "DATETIME" not in df.columns:
        df = add_datetime_column(df)

    # Create hour column
    df["Hour"] = df["DATETIME"].dt.floor("H")

    # Group by hour and settlement point, calculate mean
    group_cols = ["Hour"]
    if settlement_column in df.columns:
        group_cols.append(settlement_column)

    result = df.groupby(group_cols).agg({"SettlementPointPrice": "mean"}).reset_index()
    result.rename(columns={"Hour": "DATETIME", "SettlementPointPrice": "RTLMP"}, inplace=True)

    return result


def normalize_ercot_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Complete normalization pipeline for ERCOT API responses.

    This is the main utility function that:
    1. Cleans column names
    2. Adds standardized DATETIME column
    3. Ensures proper data types

    Args:
        df: Raw DataFrame from ERCOT API

    Returns:
        Cleaned and normalized DataFrame with DATETIME column
    """
    df = normalize_column_names(df)
    df = add_datetime_column(df)
    return df


def validate_parameters(endpoint_name: str, params: Dict[str, Any], valid_params: list) -> Dict[str, Any]:
    """
    Validate and filter parameters for an endpoint.

    Source: ErcotMagic.jl:163-178

    Args:
        endpoint_name: Name of the endpoint
        params: Input parameters dictionary
        valid_params: List of valid parameter names for this endpoint

    Returns:
        Filtered parameters dictionary containing only valid params

    Side Effects:
        Logs warnings for invalid/skipped parameters
    """
    filtered = {}
    skipped = []

    for key, value in params.items():
        if key in valid_params or key in ["size", "offset"]:  # size/offset are always valid
            filtered[key] = value
        else:
            skipped.append(key)

    if skipped:
        print(f"Warning: Skipped invalid parameters for {endpoint_name}: {', '.join(skipped)}")

    return filtered


def build_query_params(
    endpoint_name: str,
    date_key: str,
    date_from: str,
    date_to: Optional[str] = None,
    **kwargs,
) -> Dict[str, str]:
    """
    Build query parameters for ERCOT API call.

    Source: ErcotMagic.jl:206-247 (get_data logic)

    Args:
        endpoint_name: Name of the endpoint
        date_key: Primary date parameter name (e.g., "deliveryDate")
        date_from: Start date (YYYY-MM-DD format)
        date_to: End date (optional, defaults to date_from)
        **kwargs: Additional parameters (settlementPoint, resourceType, etc.)

    Returns:
        Dictionary of query parameters ready for API call
    """
    params = {}

    # Add date parameters based on date_key
    date_from_param = f"{date_key}From"
    date_to_param = f"{date_key}To"

    params[date_from_param] = date_from
    params[date_to_param] = date_to if date_to else date_from

    # Add any additional parameters
    for key, value in kwargs.items():
        if value is not None:
            params[key] = str(value)

    return params
