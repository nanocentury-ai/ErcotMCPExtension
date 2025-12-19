#!/bin/bash
# Test script to evaluate rolling forecast quality

set -e

echo "================================================"
echo "ERCOT Rolling Forecast - Quality Evaluation"
echo "================================================"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo ""
    echo "Please create a .env file with your ERCOT credentials:"
    echo "  ERCOTUSER=your_username"
    echo "  ERCOTPASS=your_password"
    echo "  ERCOTKEY=your_api_key (optional)"
    echo ""
    exit 1
fi

# Load environment variables from .env
echo "Loading credentials from .env..."
export $(grep -v '^#' .env | xargs)

# Verify credentials are set
if [ -z "$ERCOTUSER" ] || [ -z "$ERCOTPASS" ]; then
    echo "❌ Error: ERCOTUSER or ERCOTPASS not set in .env file"
    exit 1
fi

echo "✅ Credentials loaded"
echo ""

# Set PYTHONPATH to include lib folder
export PYTHONPATH="$(pwd):$(pwd)/lib"

echo "Starting Rolling Forecast Quality Test..."
echo "================================================"
echo ""

# Run the test
python3 << 'EOF'
import sys
sys.path.insert(0, '.')

from server.forecasting import rolling_forecast_cv
from server.client import ErcotAPIClient
from datetime import datetime, timedelta
import json

print("ROLLING FORECAST CROSS-VALIDATION TEST")
print("=" * 70)
print()

# Test configuration
end_date = (datetime.now() - timedelta(days=1)).date()
start_date = end_date - timedelta(days=14)  # 15 days total

print("Configuration:")
print(f"  Date range: {start_date} to {end_date}")
print(f"  Total days: 15")
print(f"  Initial training days: 7")
print(f"  Expected CV iterations: 8 (days 8-15)")
print(f"  Polynomial degree: 3")
print(f"  Window type: Expanding")
print()
print("=" * 70)
print()

try:
    client = ErcotAPIClient()

    result = rolling_forecast_cv(
        start_date=start_date,
        end_date=end_date,
        initial_training_days=7,
        polynomial_degree=3,
        expanding_window=True,
        client=client
    )

    print()
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print()

    # Overall Performance
    perf = result['overall_performance']
    print("Overall Performance Metrics:")
    print(f"  Total Forecast Hours: {perf['total_hours']}")
    print(f"  Forecast Days: {perf['forecast_days']}")
    print(f"  Mean Absolute Error (MAE): ${perf['mae']:.2f}/MWh")
    print(f"  Root Mean Squared Error (RMSE): ${perf['rmse']:.2f}/MWh")
    print(f"  R-Squared (R²): {perf['r_squared']:.4f}")
    print()

    # Quality Assessment
    print("Quality Assessment:")
    if perf['r_squared'] > 0.8:
        print("  ✅ EXCELLENT - R² > 0.8 (model explains >80% of variance)")
    elif perf['r_squared'] > 0.6:
        print("  ✅ GOOD - R² > 0.6 (model explains >60% of variance)")
    elif perf['r_squared'] > 0.4:
        print("  ⚠️  FAIR - R² > 0.4 (model explains >40% of variance)")
    else:
        print("  ❌ POOR - R² < 0.4 (model explains <40% of variance)")

    if perf['mae'] < 20:
        print("  ✅ EXCELLENT - MAE < $20/MWh")
    elif perf['mae'] < 30:
        print("  ✅ GOOD - MAE < $30/MWh")
    elif perf['mae'] < 50:
        print("  ⚠️  FAIR - MAE < $50/MWh")
    else:
        print("  ❌ POOR - MAE > $50/MWh")
    print()

    # Daily Performance
    print("Daily Performance (per forecast day):")
    print()
    daily = result['daily_metrics']
    print(f"{'Date':<12} {'MAE ($)':<10} {'RMSE ($)':<10} {'R²':<8} {'Hours':<6}")
    print("-" * 70)
    for _, row in daily.iterrows():
        print(f"{str(row['date']):<12} {row['mae']:<10.2f} {row['rmse']:<10.2f} {row['r_squared']:<8.4f} {row['hours']:<6}")
    print()

    # Statistics on daily metrics
    print("Daily Metrics Statistics:")
    print(f"  MAE - Min: ${daily['mae'].min():.2f}, Max: ${daily['mae'].max():.2f}, Std: ${daily['mae'].std():.2f}")
    print(f"  R² - Min: {daily['r_squared'].min():.4f}, Max: {daily['r_squared'].max():.4f}, Std: {daily['r_squared'].std():.4f}")
    print()

    # Data integrity checks
    print("Data Integrity Checks:")
    preds = result['predictions']
    print(f"  Total prediction rows: {len(preds)}")
    print(f"  Columns: {list(preds.columns)}")
    print(f"  Any NaN in predictions: {preds['PredictedLambda'].isna().any()}")
    print(f"  Any NaN in actuals: {preds['SystemLambda'].isna().any()}")
    print(f"  NetLoad range: {preds['NetLoad'].min():.2f} to {preds['NetLoad'].max():.2f} MW")
    print(f"  Predicted price range: ${preds['PredictedLambda'].min():.2f} to ${preds['PredictedLambda'].max():.2f}/MWh")
    print(f"  Actual price range: ${preds['SystemLambda'].min():.2f} to ${preds['SystemLambda'].max():.2f}/MWh")
    print()

    # Save detailed results to file
    output_file = 'forecast_quality_results.json'
    results_to_save = {
        'test_date': datetime.now().isoformat(),
        'configuration': result['parameters'],
        'overall_performance': result['overall_performance'],
        'daily_metrics': result['daily_metrics'].to_dict('records'),
        'sample_predictions': result['predictions'].head(10).to_dict('records')
    }

    with open(output_file, 'w') as f:
        json.dump(results_to_save, f, indent=2, default=str)

    print(f"Detailed results saved to: {output_file}")
    print()

    print("=" * 70)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 70)

    # Exit code based on quality
    if perf['r_squared'] > 0.5 and perf['mae'] < 40:
        print("\n✅ Model quality is acceptable for production use")
        sys.exit(0)
    else:
        print("\n⚠️  Model quality may need improvement")
        sys.exit(1)

except Exception as e:
    print()
    print("=" * 70)
    print("❌ TEST FAILED")
    print("=" * 70)
    print(f"\nError: {e}")
    print()
    import traceback
    traceback.print_exc()
    sys.exit(2)

EOF

echo ""
echo "================================================"
echo "Test script completed"
echo "================================================"
