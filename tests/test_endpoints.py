"""
Tests for endpoints module
"""

import pytest
from ercot_mcp.endpoints import (
    get_endpoint_spec,
    list_endpoints,
    validate_endpoint,
    get_date_key,
    get_url,
    ANNOTATED_ENDPOINTS,
    ENDPOINT_CATEGORIES,
)


class TestEndpointSpecs:
    """Test endpoint specification functions"""

    def test_annotated_endpoints_count(self):
        """Test we have all 23 endpoints"""
        assert len(ANNOTATED_ENDPOINTS) == 23

    def test_get_endpoint_spec_valid(self):
        """Test getting spec for valid endpoint"""
        spec = get_endpoint_spec("da_prices")
        assert spec.name == "da_prices"
        assert spec.date_key == "deliveryDate"
        assert "dam_stlmnt_pnt_prices" in spec.url
        assert spec.category == "prices"

    def test_get_endpoint_spec_invalid(self):
        """Test error on invalid endpoint"""
        with pytest.raises(ValueError, match="Unknown endpoint"):
            get_endpoint_spec("invalid_endpoint")

    def test_validate_endpoint(self):
        """Test endpoint validation"""
        assert validate_endpoint("da_prices") is True
        assert validate_endpoint("rt_prices") is True
        assert validate_endpoint("invalid_endpoint") is False

    def test_get_date_key(self):
        """Test getting date key for endpoints"""
        assert get_date_key("da_prices") == "deliveryDate"
        assert get_date_key("rt_system_lambda") == "SCEDTimestamp"
        assert get_date_key("ercot_actual_load") == "operatingDay"

    def test_get_date_key_invalid(self):
        """Test error on invalid endpoint"""
        with pytest.raises(ValueError, match="Unknown endpoint"):
            get_date_key("invalid_endpoint")

    def test_get_url(self):
        """Test getting URL for endpoints"""
        url = get_url("da_prices")
        assert url.startswith("https://api.ercot.com")
        assert "dam_stlmnt_pnt_prices" in url

    def test_get_url_invalid(self):
        """Test error on invalid endpoint"""
        with pytest.raises(ValueError, match="Unknown endpoint"):
            get_url("invalid_endpoint")


class TestEndpointCategories:
    """Test endpoint categorization"""

    def test_categories_exist(self):
        """Test all expected categories exist"""
        expected_categories = ["prices", "forecasts", "actuals", "market_data", "other"]
        for cat in expected_categories:
            assert cat in ENDPOINT_CATEGORIES

    def test_prices_category(self):
        """Test prices category endpoints"""
        prices = ENDPOINT_CATEGORIES["prices"]
        assert "da_prices" in prices
        assert "rt_prices" in prices
        assert "da_system_lambda" in prices
        assert "rt_system_lambda" in prices

    def test_forecasts_category(self):
        """Test forecasts category endpoints"""
        forecasts = ENDPOINT_CATEGORIES["forecasts"]
        assert "ercot_load_forecast" in forecasts
        assert "solar_system_forecast" in forecasts
        assert "wind_system_forecast" in forecasts

    def test_actuals_category(self):
        """Test actuals category endpoints"""
        actuals = ENDPOINT_CATEGORIES["actuals"]
        assert "ercot_actual_load" in actuals
        assert "wind_prod_5min" in actuals
        assert "solar_prod_5min" in actuals

    def test_list_endpoints_all(self):
        """Test listing all endpoints"""
        specs = list_endpoints("all")
        assert len(specs) == 23
        assert all(hasattr(s, "name") for s in specs)
        assert all(hasattr(s, "url") for s in specs)

    def test_list_endpoints_prices(self):
        """Test listing price endpoints"""
        specs = list_endpoints("prices")
        assert len(specs) == 5
        assert all(s.category == "prices" for s in specs)

    def test_list_endpoints_forecasts(self):
        """Test listing forecast endpoints"""
        specs = list_endpoints("forecasts")
        assert len(specs) == 4
        assert all(s.category == "forecasts" for s in specs)

    def test_list_endpoints_invalid_category(self):
        """Test error on invalid category"""
        with pytest.raises(ValueError, match="Unknown category"):
            list_endpoints("invalid_category")


class TestEndpointMetadata:
    """Test endpoint metadata and summaries"""

    def test_all_endpoints_have_summaries(self):
        """Test that all endpoints have summary descriptions"""
        from ercot_mcp.endpoints import ENDPOINT_SUMMARIES

        for endpoint_name in ANNOTATED_ENDPOINTS.keys():
            assert endpoint_name in ENDPOINT_SUMMARIES
            assert len(ENDPOINT_SUMMARIES[endpoint_name]) > 0

    def test_endpoint_spec_includes_summary(self):
        """Test that endpoint specs include summaries"""
        spec = get_endpoint_spec("da_prices")
        assert spec.summary != ""
        assert "day-ahead" in spec.summary.lower()

    def test_endpoint_spec_includes_valid_parameters(self):
        """Test that endpoint specs include valid parameters"""
        spec = get_endpoint_spec("da_prices")
        assert len(spec.valid_parameters) > 0
        # All delivery date endpoints should have these params
        assert "deliveryDateFrom" in spec.valid_parameters
        assert "deliveryDateTo" in spec.valid_parameters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
