#!/usr/bin/env python3
"""Test the rolling cross-validation"""

from ercot_mcp.forecasting import rolling_forecast_cv

print('Testing rolling cross-validation...')
print('=' * 60)

# Test with a short period (last 25 days, train on 10, test on rest)
result = rolling_forecast_cv(
    start_date='2024-02-01',
    end_date='2024-02-15',
    initial_training_days=7,
    polynomial_degree=3,
    expanding_window=True
)

print('\n' + '=' * 60)
print('Cross-Validation Results:')
print(f'  Total predictions: {len(result["predictions"])} hours')
print(f'  Forecast days: {result["overall_performance"]["forecast_days"]}')
print(f'  Overall MAE: ${result["overall_performance"]["mae"]:.2f}/MWh')
print(f'  Overall RMSE: ${result["overall_performance"]["rmse"]:.2f}/MWh')
print(f'  Overall R²: {result["overall_performance"]["r_squared"]:.3f}')

print('\nDaily metrics sample:')
print(result['daily_metrics'].head())

print('\n✅ Rolling CV test completed!')
