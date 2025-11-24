#!/usr/bin/env python3
"""Debug script to inspect actual API response structure"""
from ercot_mcp.client import ErcotAPIClient
from ercot_mcp.endpoints import get_endpoint_spec
import json

client = ErcotAPIClient()

# Test with da_prices endpoint
print("Testing da_prices endpoint...")
spec = get_endpoint_spec("da_prices")
print(f"URL: {spec.url}")

params = {
    "deliveryDateFrom": "2024-02-01",
    "deliveryDateTo": "2024-02-01",
    "size": 5
}

print(f"Params: {params}")

try:
    response = client.ercot_api_call(spec.url, params)
    print("\nRaw API Response structure:")
    print(f"Response type: {type(response)}")
    print(f"Response keys: {response.keys() if isinstance(response, dict) else 'N/A'}")

    if 'fields' in response:
        print(f"\nFields: {response['fields']}")

    if 'data' in response:
        print(f"\nData length: {len(response['data'])}")
        print(f"First data item type: {type(response['data'][0])}")
        print(f"First data item: {response['data'][0]}")

        if len(response['data']) > 1:
            print(f"Second data item: {response['data'][1]}")

    print("\n\nFull response (pretty printed):")
    print(json.dumps(response, indent=2, default=str)[:2000])

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
