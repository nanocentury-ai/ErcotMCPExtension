"""
ERCOT API Endpoint Definitions

Converted from src/annotated_endpoints.jl and src/constants.jl
Contains all 34 available endpoints with their date keys and URLs.
"""

from typing import Dict, List, Tuple
from pydantic import BaseModel


class EndpointSpec(BaseModel):
    """
    Specification for an ERCOT API endpoint.

    Matches Julia's ErcotSpec struct from ErcotMagic.jl:73-78
    """

    name: str
    date_key: str
    url: str
    summary: str = ""
    category: str = ""
    valid_parameters: List[str] = []


# Annotated endpoints converted from annotated_endpoints.jl
# Format: "endpoint_name" => (date_key, url)
ANNOTATED_ENDPOINTS: Dict[str, Tuple[str, str]] = {
    # PRICES (Lines 7-11)
    "da_prices": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np4-190-cd/dam_stlmnt_pnt_prices",
    ),
    "rt_prices": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np6-905-cd/spp_node_zone_hub",
    ),
    "ancillary_prices": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np4-188-cd/dam_clear_price_for_cap",
    ),
    "da_system_lambda": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np4-523-cd/dam_system_lambda",
    ),
    "rt_system_lambda": (
        "SCEDTimestamp",
        "https://api.ercot.com/api/public-reports/np6-322-cd/sced_system_lambda",
    ),
    # FORECASTS (Lines 13-18)
    "ercot_load_forecast": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np3-566-cd/lf_by_model_study_area",
    ),
    "ercot_zone_load_forecast": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np3-565-cd/lf_by_model_weather_zone",
    ),
    "solar_system_forecast": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np4-737-cd/spp_hrly_avrg_actl_fcast",
    ),
    "wind_system_forecast": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np4-732-cd/wpp_hrly_avrg_actl_fcast",
    ),
    "ercot_outages": (
        "operatingDate",
        "https://api.ercot.com/api/public-reports/np3-233-cd/hourly_res_outage_cap",
    ),
    "binding_constraints": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np6-86-cd/shdw_prices_bnd_trns_const",
    ),
    # ACTUALS (Lines 20-22)
    "ercot_actual_load": (
        "operatingDay",
        "https://api.ercot.com/api/public-reports/np6-345-cd/act_sys_load_by_wzn",
    ),
    "wind_prod_5min": (
        "intervalEnding",
        "https://api.ercot.com/api/public-reports/np4-733-cd/wpp_actual_5min_avg_values",
    ),
    "solar_prod_5min": (
        "intervalEnding",
        "https://api.ercot.com/api/public-reports/np4-738-cd/spp_actual_5min_avg_values",
    ),
    # 60 DAY OFFERS / MARKET DATA (Lines 24-33)
    "sixty_dam_energy_only_offers": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np3-966-er/60_dam_energy_only_offers",
    ),
    "sixty_dam_awards": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np3-966-er/60_dam_energy_only_offer_awards",
    ),
    "energybids": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np3-966-er/60_dam_energy_bids",
    ),
    "gen_data": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np3-966-er/60_dam_gen_res_data",
    ),
    "twodayAS": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np3-911-er/2d_agg_as_offers_ecrsm",
    ),
    "sced_gen_data": (
        "SCEDTimestamp",
        "https://api.ercot.com/api/public-reports/np3-965-er/60_sced_gen_res_data",
    ),
    "sced_energy_only_offers": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np3-966-er/60_dam_energy_only_offers",
    ),
    "sced_gen_as_data": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np3-966-er/60_dam_gen_res_as_offers",
    ),
    "sced_load_data": (
        "deliveryDate",
        "https://api.ercot.com/api/public-reports/np3-966-er/60_dam_load_res_data",
    ),
}


# Endpoint categories for organization
ENDPOINT_CATEGORIES = {
    "prices": [
        "da_prices",
        "rt_prices",
        "ancillary_prices",
        "da_system_lambda",
        "rt_system_lambda",
    ],
    "forecasts": [
        "ercot_load_forecast",
        "ercot_zone_load_forecast",
        "solar_system_forecast",
        "wind_system_forecast",
    ],
    "actuals": [
        "ercot_actual_load",
        "wind_prod_5min",
        "solar_prod_5min",
    ],
    "market_data": [
        "sixty_dam_energy_only_offers",
        "sixty_dam_awards",
        "energybids",
        "gen_data",
        "twodayAS",
        "sced_gen_data",
        "sced_energy_only_offers",
        "sced_gen_as_data",
        "sced_load_data",
    ],
    "other": [
        "ercot_outages",
        "binding_constraints",
    ],
}


# Endpoint summaries/descriptions
ENDPOINT_SUMMARIES = {
    "da_prices": "Day-ahead market settlement point prices (hourly)",
    "rt_prices": "Real-time settlement point prices (5-minute)",
    "ancillary_prices": "Day-ahead ancillary service clearing prices",
    "da_system_lambda": "Day-ahead system-wide lambda (energy price)",
    "rt_system_lambda": "Real-time SCED system lambda (5-minute)",
    "ercot_load_forecast": "System-wide load forecast by model",
    "ercot_zone_load_forecast": "Weather zone load forecast by model",
    "solar_system_forecast": "System-wide solar generation forecast and actuals",
    "wind_system_forecast": "System-wide wind generation forecast and actuals",
    "ercot_outages": "Hourly resource outage capacity",
    "binding_constraints": "Shadow prices for binding transmission constraints",
    "ercot_actual_load": "Actual system load by weather zone",
    "wind_prod_5min": "Actual wind production (5-minute averages)",
    "solar_prod_5min": "Actual solar production (5-minute averages)",
    "sixty_dam_energy_only_offers": "60-day DAM energy-only offers",
    "sixty_dam_awards": "60-day DAM energy-only offer awards",
    "energybids": "60-day DAM energy bids",
    "gen_data": "60-day DAM generation resource data (includes virtual awards)",
    "twodayAS": "2-day aggregated ancillary service offers",
    "sced_gen_data": "60-day SCED generation resource data",
    "sced_energy_only_offers": "60-day SCED energy-only offers",
    "sced_gen_as_data": "60-day DAM generation resource AS offers",
    "sced_load_data": "60-day DAM load resource data",
}


# Common parameters by date key type
COMMON_PARAMETERS = {
    "deliveryDate": ["deliveryDateFrom", "deliveryDateTo", "settlementPoint", "size", "postedDatetimeFrom", "postedDatetimeTo"],
    "operatingDay": ["operatingDayFrom", "operatingDayTo", "size"],
    "operatingDate": ["operatingDateFrom", "operatingDateTo", "size"],
    "SCEDTimestamp": ["SCEDTimestampFrom", "SCEDTimestampTo", "resourceType", "size"],
    "intervalEnding": ["intervalEndingFrom", "intervalEndingTo", "size"],
}


def get_endpoint_spec(endpoint_name: str) -> EndpointSpec:
    """
    Get full specification for an endpoint.

    Args:
        endpoint_name: Name of the endpoint (e.g., "da_prices")

    Returns:
        EndpointSpec with all metadata

    Raises:
        ValueError: If endpoint_name is not recognized
    """
    if endpoint_name not in ANNOTATED_ENDPOINTS:
        raise ValueError(
            f"Unknown endpoint: {endpoint_name}. "
            f"Available: {', '.join(ANNOTATED_ENDPOINTS.keys())}"
        )

    date_key, url = ANNOTATED_ENDPOINTS[endpoint_name]
    category = next(
        (cat for cat, eps in ENDPOINT_CATEGORIES.items() if endpoint_name in eps), "other"
    )

    return EndpointSpec(
        name=endpoint_name,
        date_key=date_key,
        url=url,
        summary=ENDPOINT_SUMMARIES.get(endpoint_name, ""),
        category=category,
        valid_parameters=COMMON_PARAMETERS.get(date_key, []),
    )


def list_endpoints(category: str = "all") -> List[EndpointSpec]:
    """
    List available endpoints, optionally filtered by category.

    Args:
        category: Filter by category ("prices", "forecasts", "actuals", "market_data", "all")

    Returns:
        List of EndpointSpec objects
    """
    if category == "all":
        endpoint_names = list(ANNOTATED_ENDPOINTS.keys())
    elif category in ENDPOINT_CATEGORIES:
        endpoint_names = ENDPOINT_CATEGORIES[category]
    else:
        raise ValueError(
            f"Unknown category: {category}. "
            f"Available: {', '.join(list(ENDPOINT_CATEGORIES.keys()) + ['all'])}"
        )

    return [get_endpoint_spec(name) for name in endpoint_names]


def validate_endpoint(endpoint_name: str) -> bool:
    """Check if an endpoint name is valid"""
    return endpoint_name in ANNOTATED_ENDPOINTS


def get_date_key(endpoint_name: str) -> str:
    """Get the date parameter key for an endpoint"""
    if endpoint_name not in ANNOTATED_ENDPOINTS:
        raise ValueError(f"Unknown endpoint: {endpoint_name}")
    return ANNOTATED_ENDPOINTS[endpoint_name][0]


def get_url(endpoint_name: str) -> str:
    """Get the API URL for an endpoint"""
    if endpoint_name not in ANNOTATED_ENDPOINTS:
        raise ValueError(f"Unknown endpoint: {endpoint_name}")
    return ANNOTATED_ENDPOINTS[endpoint_name][1]
