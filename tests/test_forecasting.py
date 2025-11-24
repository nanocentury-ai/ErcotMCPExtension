#!/usr/bin/env python3
"""Test the forecasting functions"""

from ercot_mcp.forecasting import day_ahead_forecast

print('Testing day-ahead forecast for 2024-02-15...')
print('=' * 60)

result = day_ahead_forecast(
    forecast_date='2024-02-15',
    training_days=15,
    polynomial_degree=3
)

print('\n' + '=' * 60)
print('Results:')
print(f'  Forecast hours: {len(result["forecast"])}')
print(f'  Training MAE: ${result["training_performance"]["mae"]:.2f}/MWh')
print(f'  Training R²: {result["training_performance"]["r_squared"]:.3f}')

if not result['forecast'].empty:
    forecast = result['forecast']
    print(f'\nForecast sample:')
    print(forecast[['DATETIME', 'NetLoad', 'PredictedLambda']].head())

print('\n✅ Day-ahead forecast test completed!')
