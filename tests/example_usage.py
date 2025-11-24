"""
Example usage of ERCOT MCP client

This demonstrates how to use the client directly (not through MCP protocol)
for testing and development.
"""

from ercot_mcp.client import ErcotAPIClient
from ercot_mcp.endpoints import list_endpoints
import pandas as pd


def example_1_list_endpoints():
    """Example: Browse available endpoints"""
    print("=" * 60)
    print("Example 1: List Available Endpoints")
    print("=" * 60)

    # List all price endpoints
    specs = list_endpoints("prices")
    print(f"\nFound {len(specs)} price endpoints:")
    for spec in specs:
        print(f"  - {spec.name}: {spec.summary}")

    # List all forecasts
    specs = list_endpoints("forecasts")
    print(f"\nFound {len(specs)} forecast endpoints:")
    for spec in specs:
        print(f"  - {spec.name}: {spec.summary}")


def example_2_fetch_day_ahead_prices():
    """Example: Fetch day-ahead prices"""
    print("\n" + "=" * 60)
    print("Example 2: Fetch Day-Ahead Prices")
    print("=" * 60)

    client = ErcotAPIClient()

    # Fetch day-ahead prices for a single day
    df = client.fetch_data(
        endpoint_name="da_prices",
        date_from="2024-02-01",
        size=10000
    )

    print(f"\nFetched {len(df)} records")
    print(f"Columns: {list(df.columns)}")
    print(f"\nFirst few rows:")
    print(df.head())

    if "DATETIME" in df.columns:
        print(f"\nDate range: {df['DATETIME'].min()} to {df['DATETIME'].max()}")


def example_3_fetch_load_forecast():
    """Example: Fetch load forecast"""
    print("\n" + "=" * 60)
    print("Example 3: Fetch Load Forecast")
    print("=" * 60)

    client = ErcotAPIClient()

    # Fetch load forecast for a week
    df = client.fetch_data(
        endpoint_name="ercot_load_forecast",
        date_from="2024-02-01",
        date_to="2024-02-07"
    )

    print(f"\nFetched {len(df)} records")
    print(f"Columns: {list(df.columns)}")

    if "DATETIME" in df.columns and not df.empty:
        print(f"\nDate range: {df['DATETIME'].min()} to {df['DATETIME'].max()}")


def example_4_fetch_rt_prices_at_node():
    """Example: Fetch real-time prices at specific settlement point"""
    print("\n" + "=" * 60)
    print("Example 4: Fetch RT Prices at Settlement Point")
    print("=" * 60)

    client = ErcotAPIClient()

    # Fetch RT prices for HB_NORTH hub
    df = client.fetch_data(
        endpoint_name="rt_prices",
        date_from="2024-02-01",
        settlement_point="HB_NORTH",
        size=50000
    )

    print(f"\nFetched {len(df)} records for HB_NORTH")
    print(f"Columns: {list(df.columns)}")

    if "SettlementPointPrice" in df.columns:
        print(f"\nPrice statistics:")
        print(f"  Min: ${df['SettlementPointPrice'].min():.2f}")
        print(f"  Max: ${df['SettlementPointPrice'].max():.2f}")
        print(f"  Mean: ${df['SettlementPointPrice'].mean():.2f}")


def example_5_compare_da_vs_rt():
    """Example: Compare day-ahead vs real-time prices"""
    print("\n" + "=" * 60)
    print("Example 5: Compare DA vs RT Prices")
    print("=" * 60)

    client = ErcotAPIClient()

    # Fetch DA and RT prices for same day
    da_df = client.fetch_data(
        endpoint_name="da_prices",
        date_from="2024-02-01",
        settlement_point="HB_NORTH"
    )

    rt_df = client.fetch_data(
        endpoint_name="rt_prices",
        date_from="2024-02-01",
        settlement_point="HB_NORTH",
        size=50000
    )

    print(f"\nDA records: {len(da_df)}")
    print(f"RT records: {len(rt_df)}")

    if not da_df.empty and not rt_df.empty:
        print(f"\nDA price range: ${da_df['SettlementPointPrice'].min():.2f} - ${da_df['SettlementPointPrice'].max():.2f}")
        print(f"RT price range: ${rt_df['SettlementPointPrice'].min():.2f} - ${rt_df['SettlementPointPrice'].max():.2f}")


if __name__ == "__main__":
    print("\nERCOT MCP Client - Example Usage")
    print("=" * 60)
    print("\nNOTE: These examples require valid ERCOTUSER and ERCOTPASS")
    print("      environment variables. Copy .env.example to .env and")
    print("      add your credentials before running.")
    print()

    try:
        # Run examples
        example_1_list_endpoints()
        example_2_fetch_day_ahead_prices()
        example_3_fetch_load_forecast()
        example_4_fetch_rt_prices_at_node()
        example_5_compare_da_vs_rt()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("  1. Copied .env.example to .env")
        print("  2. Added your ERCOTUSER and ERCOTPASS credentials")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
