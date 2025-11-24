"""
Tests for utils module
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta

from ercot_mcp.utils import (
    normalize_column_names,
    parse_hour_ending,
    add_datetime_column,
    normalize_ercot_dataframe,
    build_query_params,
)


class TestColumnNormalization:
    """Test column name normalization"""

    def test_normalize_column_names_spaces(self):
        """Test removing spaces from column names"""
        df = pd.DataFrame({"Column One": [1], "Column Two": [2]})
        result = normalize_column_names(df)
        assert "ColumnOne" in result.columns
        assert "ColumnTwo" in result.columns

    def test_normalize_column_names_hyphens(self):
        """Test converting hyphens to PascalCase"""
        df = pd.DataFrame({"Column-One": [1], "Column-Two": [2]})
        result = normalize_column_names(df)
        assert "ColumnOne" in result.columns
        assert "ColumnTwo" in result.columns

    def test_normalize_column_names_mixed(self):
        """Test converting mixed spaces and hyphens to PascalCase"""
        df = pd.DataFrame({"Column One-Two": [1]})
        result = normalize_column_names(df)
        assert "ColumnOneTwo" in result.columns

    def test_normalize_column_names_camelcase(self):
        """Test converting camelCase to PascalCase"""
        df = pd.DataFrame({"deliveryDate": [1], "settlementPointPrice": [2]})
        result = normalize_column_names(df)
        assert "DeliveryDate" in result.columns
        assert "SettlementPointPrice" in result.columns


class TestHourEndingParsing:
    """Test hour-ending datetime parsing"""

    def test_parse_hour_ending_integer(self):
        """Test parsing integer hour ending"""
        base_date = datetime(2024, 1, 1)
        result = parse_hour_ending(base_date, 1)
        # Hour 1 = 00:00 - 01:00, ending at 00:00 (start of day)
        assert result == datetime(2024, 1, 1, 0, 0)

    def test_parse_hour_ending_hour_24(self):
        """Test parsing hour ending 24:00"""
        base_date = datetime(2024, 1, 1)
        result = parse_hour_ending(base_date, "24:00")
        # Hour 24 = 23:00 - 24:00, ending at 23:00
        assert result == datetime(2024, 1, 1, 23, 0)

    def test_parse_hour_ending_string(self):
        """Test parsing string hour ending"""
        base_date = datetime(2024, 1, 1)
        result = parse_hour_ending(base_date, "13:00")
        # Hour 13 ending = 12:00
        assert result == datetime(2024, 1, 1, 12, 0)


class TestDatetimeColumnAddition:
    """Test datetime column addition for various ERCOT formats"""

    def test_add_datetime_delivery_interval(self):
        """Test Pattern 1: DeliveryDate + DeliveryHour + DeliveryInterval"""
        df = pd.DataFrame({
            "DeliveryDate": ["2024-01-01"],
            "DeliveryHour": [1],
            "DeliveryInterval": [0]  # 0 = first 5 minutes of hour
        })
        result = add_datetime_column(df)
        assert "DATETIME" in result.columns
        assert result["DATETIME"][0] == pd.Timestamp("2024-01-01 01:00:00")

    def test_add_datetime_interval_ending(self):
        """Test Pattern 2: IntervalEnding"""
        df = pd.DataFrame({
            "IntervalEnding": ["2024-01-01T12:05:00"]
        })
        result = add_datetime_column(df)
        assert "DATETIME" in result.columns
        assert result["DATETIME"][0] == pd.Timestamp("2024-01-01 12:05:00")

    def test_add_datetime_operating_day(self):
        """Test Pattern 3: OperatingDay + HourEnding"""
        df = pd.DataFrame({
            "OperatingDay": ["2024-01-01"],
            "HourEnding": [1]
        })
        result = add_datetime_column(df)
        assert "DATETIME" in result.columns

    def test_add_datetime_delivery_hour(self):
        """Test Pattern 5: DeliveryDate + DeliveryHour"""
        df = pd.DataFrame({
            "DeliveryDate": ["2024-01-01"],
            "DeliveryHour": [13]
        })
        result = add_datetime_column(df)
        assert "DATETIME" in result.columns
        assert result["DATETIME"][0] == pd.Timestamp("2024-01-01 13:00:00")

    def test_add_datetime_sced_timestamp(self):
        """Test Pattern 7: SCEDTimestamp"""
        df = pd.DataFrame({
            "SCEDTimestamp": ["2024-01-01T12:05:00"]
        })
        result = add_datetime_column(df)
        assert "DATETIME" in result.columns
        assert result["DATETIME"][0] == pd.Timestamp("2024-01-01 12:05:00")

    def test_add_datetime_no_columns(self):
        """Test warning when no datetime columns found"""
        df = pd.DataFrame({"SomeColumn": [1, 2, 3]})
        result = add_datetime_column(df)
        assert "DATETIME" not in result.columns


class TestNormalizeErcotDataframe:
    """Test complete normalization pipeline"""

    def test_normalize_ercot_dataframe_complete(self):
        """Test full normalization pipeline"""
        df = pd.DataFrame({
            "Delivery Date": ["2024-01-01"],
            "Delivery Hour": [1],
            "Settlement-Point": ["HB_NORTH"],
            "Price": [50.0]
        })
        result = normalize_ercot_dataframe(df)

        # Check column name normalization (PascalCase)
        assert "DeliveryDate" in result.columns
        assert "DeliveryHour" in result.columns
        assert "SettlementPoint" in result.columns

        # Check datetime was added
        assert "DATETIME" in result.columns


class TestQueryParameterBuilding:
    """Test query parameter construction"""

    def test_build_query_params_basic(self):
        """Test basic query parameter building"""
        params = build_query_params(
            endpoint_name="da_prices",
            date_key="deliveryDate",
            date_from="2024-01-01"
        )
        assert params["deliveryDateFrom"] == "2024-01-01"
        assert params["deliveryDateTo"] == "2024-01-01"

    def test_build_query_params_with_date_to(self):
        """Test with explicit date_to"""
        params = build_query_params(
            endpoint_name="da_prices",
            date_key="deliveryDate",
            date_from="2024-01-01",
            date_to="2024-01-07"
        )
        assert params["deliveryDateFrom"] == "2024-01-01"
        assert params["deliveryDateTo"] == "2024-01-07"

    def test_build_query_params_with_kwargs(self):
        """Test with additional parameters"""
        params = build_query_params(
            endpoint_name="da_prices",
            date_key="deliveryDate",
            date_from="2024-01-01",
            settlementPoint="HB_NORTH",
            size=1000
        )
        assert params["settlementPoint"] == "HB_NORTH"
        assert params["size"] == "1000"

    def test_build_query_params_filters_none(self):
        """Test that None values are filtered out"""
        params = build_query_params(
            endpoint_name="da_prices",
            date_key="deliveryDate",
            date_from="2024-01-01",
            settlementPoint=None,
            size=1000
        )
        assert "settlementPoint" not in params
        assert "size" in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
