"""
Load forecast utilities for ERCOT data

This module provides functions for retrieving vintage forecasts and calculating
net load forecasts (load minus renewable generation).

Ported from Julia ErcotMagic package forecast functions.
"""

from typing import Optional, Union
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np

from .client import ErcotAPIClient


def filter_forecast_by_posted(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter forecast data to keep only the most recent forecast for each datetime.

    For each DATETIME, keeps the row with the latest PostedDatetime value.

    Args:
        df: DataFrame with DATETIME and PostedDatetime columns

    Returns:
        Filtered DataFrame with one row per DATETIME (most recent forecast)
    """
    if df.empty:
        return df

    # Ensure PostedDatetime is datetime type
    if "PostedDatetime" in df.columns:
        df["PostedDatetime"] = pd.to_datetime(df["PostedDatetime"])

    # Sort by DATETIME and PostedDatetime, then keep last (most recent) for each DATETIME
    df = df.sort_values(["DATETIME", "PostedDatetime"])
    df = df.groupby("DATETIME").last().reset_index()

    return df


def get_vintage_forecast(
    endpoint_name: str,
    date_from: Union[str, date],
    date_to: Optional[Union[str, date]] = None,
    client: Optional[ErcotAPIClient] = None,
    **kwargs
) -> pd.DataFrame:
    """
    Get previously posted forecast for a date or date range.

    This function retrieves forecast data ensuring it's from the latest acceptable
    forecast (7am the prior day). Works with solar, wind, and load forecasts.

    Source: Julia get_vintage_forecast function

    Args:
        endpoint_name: Name of forecast endpoint:
            - "solar_system_forecast" for solar generation
            - "wind_system_forecast" for wind generation
            - "ercot_zone_load_forecast" for load forecast
        date_from: Start date (str "YYYY-MM-DD" or date object)
        date_to: End date (optional, defaults to date_from)
        client: Optional ErcotAPIClient instance
        **kwargs: Additional parameters passed to fetch_data

    Returns:
        DataFrame with vintage forecast data filtered to most recent posting

    Examples:
        >>> # Solar forecast for single day
        >>> df = get_vintage_forecast("solar_system_forecast", "2024-02-01")

        >>> # Wind forecast for date range
        >>> df = get_vintage_forecast("wind_system_forecast",
        ...                          "2024-02-01", "2024-02-07", size=100000)

        >>> # Load forecast
        >>> df = get_vintage_forecast("ercot_zone_load_forecast", "2024-02-01")
    """
    if client is None:
        client = ErcotAPIClient()

    # Convert dates to strings if needed
    if isinstance(date_from, date):
        date_from = date_from.strftime("%Y-%m-%d")
    if date_to is None:
        date_to = date_from
    elif isinstance(date_to, date):
        date_to = date_to.strftime("%Y-%m-%d")

    # Calculate posted datetime cutoff (7am the day before date_to)
    # This gets the "day-ahead" forecast posted before 7am on the day before delivery
    end_date = datetime.strptime(date_to, "%Y-%m-%d")
    posted_datetime_cutoff = (end_date - timedelta(days=1) + timedelta(hours=7)).strftime("%Y-%m-%dT%H:%M:%S")

    # Fetch the data with postedDatetimeTo filter
    dat = client.fetch_data(
        endpoint_name,
        date_from=date_from,
        date_to=date_to,
        postedDatetimeTo=posted_datetime_cutoff,
        **kwargs
    )

    if dat.empty:
        return dat

    # Special handling for load forecast endpoint
    if endpoint_name == "ercot_zone_load_forecast":
        # Select relevant columns for load
        cols_pattern = dat.columns[dat.columns.str.contains("DATETIME|Model|SystemTotal|Posted", case=False)]
        dat = dat[cols_pattern]

        # Group by Model and filter each group by posted datetime
        datout = pd.DataFrame()
        for model, group in dat.groupby("Model"):
            filtered = filter_forecast_by_posted(group)
            datout = pd.concat([datout, filtered], ignore_index=True)

        # Pivot to wide format with models as columns
        datout = datout.pivot_table(
            index="DATETIME",
            columns="Model",
            values="SystemTotal",
            aggfunc="first"
        ).reset_index()

        # Calculate median load forecast from E*, A*, M*, X* models
        model_cols = [col for col in datout.columns
                     if isinstance(col, str) and
                     (col.startswith("E") or col.startswith("A") or
                      col.startswith("M") or col.startswith("X"))
                     and len(col) > 1 and col[1].isdigit()]

        if model_cols:
            datout["MedianLoadForecast"] = datout[model_cols].median(axis=1)
        else:
            # Fallback: use all non-DATETIME columns
            numeric_cols = datout.select_dtypes(include=[np.number]).columns
            datout["MedianLoadForecast"] = datout[numeric_cols].median(axis=1)

        return datout[["DATETIME", "MedianLoadForecast"]]

    else:
        # For solar and wind, just filter by posted datetime
        datout = filter_forecast_by_posted(dat)

        # Drop unnecessary columns if they exist
        drop_cols = ["DSTFlag", "HourEnding", "DeliveryDate"]
        cols_to_drop = [col for col in drop_cols if col in datout.columns]
        if cols_to_drop:
            datout = datout.drop(columns=cols_to_drop)

        return datout


def get_net_load_forecast(
    date_from: Optional[Union[str, date]] = None,
    date_to: Optional[Union[str, date]] = None,
    client: Optional[ErcotAPIClient] = None,
    **kwargs
) -> pd.DataFrame:
    """
    Get net load forecast (load minus renewable generation).

    Retrieves solar, wind, and load forecasts and calculates:
    - Total renewable generation (solar + wind)
    - Net load (load - renewables)

    Source: Julia get_net_load_forecast function

    Args:
        date_from: Start date (defaults to tomorrow). Can be str "YYYY-MM-DD" or date object
        date_to: End date (optional, for date ranges)
        client: Optional ErcotAPIClient instance
        **kwargs: Additional parameters passed to forecast endpoints

    Returns:
        DataFrame with columns:
        - DATETIME: Hour-ending timestamp
        - SolarHSLSystemWide: Solar generation forecast (MW)
        - WindHSLSystemWide: Wind generation forecast (MW)
        - MedianLoadForecast: Load forecast (MW)
        - Renewables: Total renewable generation (MW)
        - NetLoad: Load minus renewables (MW)

    Examples:
        >>> # Get forecast for tomorrow
        >>> df = get_net_load_forecast()

        >>> # Get forecast for specific date
        >>> df = get_net_load_forecast(date_from="2024-02-01")

        >>> # Get forecast for date range
        >>> df = get_net_load_forecast(date_from="2024-02-01",
        ...                            date_to="2024-02-07",
        ...                            size=100000)
    """
    if client is None:
        client = ErcotAPIClient()

    # Default to tomorrow if no date provided
    if date_from is None:
        date_from = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
    elif isinstance(date_from, date):
        date_from = date_from.strftime("%Y-%m-%d")

    if date_to is not None and isinstance(date_to, date):
        date_to = date_to.strftime("%Y-%m-%d")

    # Log what we're fetching
    if date_to:
        print(f"📅 Getting net load forecast for range: {date_from} to {date_to}")
    else:
        print(f"📅 Getting net load forecast for: {date_from}")

    # Get solar forecast
    solar_gen = get_vintage_forecast(
        "solar_system_forecast",
        date_from,
        date_to,
        client=client,
        **kwargs
    )
    solar_cols = [col for col in solar_gen.columns if "COPHSL" in col and "SystemWide" in col]
    if solar_cols:
        solar_gen = solar_gen[["DATETIME"] + solar_cols]
        solar_gen = solar_gen.rename(columns={solar_cols[0]: "SolarHSLSystemWide"})
    else:
        print("⚠️  Warning: Could not find COPHSLSystemWide column in solar data")
        solar_gen = solar_gen[["DATETIME"]]
        solar_gen["SolarHSLSystemWide"] = 0

    # Get wind forecast
    wind_gen = get_vintage_forecast(
        "wind_system_forecast",
        date_from,
        date_to,
        client=client,
        **kwargs
    )
    wind_cols = [col for col in wind_gen.columns if "COPHSL" in col and "SystemWide" in col]
    if wind_cols:
        wind_gen = wind_gen[["DATETIME"] + wind_cols]
        wind_gen = wind_gen.rename(columns={wind_cols[0]: "WindHSLSystemWide"})
    else:
        print("⚠️  Warning: Could not find COPHSLSystemWide column in wind data")
        wind_gen = wind_gen[["DATETIME"]]
        wind_gen["WindHSLSystemWide"] = 0

    # Get load forecast
    load_forecast = get_vintage_forecast(
        "ercot_zone_load_forecast",
        date_from,
        date_to,
        client=client,
        **kwargs
    )

    # Join all forecasts by DATETIME
    dat = solar_gen.merge(wind_gen, on="DATETIME", how="left")
    dat = dat.merge(load_forecast, on="DATETIME", how="left")

    # Calculate total renewables (solar + wind)
    hsl_cols = [col for col in dat.columns if "HSLSystemWide" in col]
    dat["Renewables"] = dat[hsl_cols].sum(axis=1)

    # Calculate net load (load - renewables)
    dat["NetLoad"] = dat["MedianLoadForecast"] - dat["Renewables"]

    return dat
