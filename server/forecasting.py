"""
Price forecasting utilities for ERCOT data

This module provides functions for forecasting day-ahead system lambda (energy prices)
using polynomial regression on net load forecasts.

Ported from Julia ErcotMagic package forecasting functions.
"""

from typing import Optional, Dict, Tuple, List, Union
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .client import ErcotAPIClient
from .load import get_net_load_forecast


def day_ahead_forecast(
    forecast_date: Optional[Union[str, date]] = None,
    training_days: int = 15,
    polynomial_degree: int = 3,
    client: Optional[ErcotAPIClient] = None,
) -> Dict:
    """
    Generate a day-ahead price forecast using the last N days of data.

    This is designed for operational use - train on recent data and forecast tomorrow.

    Source: Julia day_ahead_forecast function

    Args:
        forecast_date: Date to forecast (default: tomorrow). Can be str "YYYY-MM-DD" or date object
        training_days: Number of recent days to train on (default: 15)
        polynomial_degree: Degree of polynomial features (default: 3)
        client: Optional ErcotAPIClient instance

    Returns:
        Dictionary with:
        - forecast: DataFrame with predicted prices
        - model: Trained sklearn model
        - training_performance: Dict with MAE, RMSE, R²
        - parameters: Dict with forecast settings

    Example:
        >>> # Forecast for tomorrow using last 15 days
        >>> result = day_ahead_forecast()
        >>> forecast_df = result['forecast']
        >>> print(f"Average forecast: ${forecast_df['PredictedLambda'].mean():.2f}/MWh")
    """
    if client is None:
        client = ErcotAPIClient()

    # Default to tomorrow
    if forecast_date is None:
        forecast_date = (datetime.now().date() + timedelta(days=1))
    elif isinstance(forecast_date, str):
        forecast_date = datetime.strptime(forecast_date, "%Y-%m-%d").date()

    print(f"🌅 Generating day-ahead forecast for {forecast_date}")
    print(f"   📅 Training on last {training_days} days")
    print(f"   📊 Polynomial degree: {polynomial_degree}")

    # Define training period (last N days before forecast date)
    training_end = forecast_date - timedelta(days=1)
    training_start = training_end - timedelta(days=training_days - 1)

    print(f"   📈 Training period: {training_start} to {training_end}")

    # Get training data
    net_load_data = get_net_load_forecast(
        date_from=training_start,
        date_to=training_end,
        client=client,
        size=10000000
    )

    lambda_data = client.fetch_data(
        "da_system_lambda",
        date_from=training_start.strftime("%Y-%m-%d"),
        date_to=training_end.strftime("%Y-%m-%d"),
        size=10000000
    )
    lambda_data = lambda_data[["DATETIME", "SystemLambda"]]

    # Join training data
    training_data = net_load_data.merge(lambda_data, on="DATETIME", how="inner")
    print(f"   ✅ Loaded {len(training_data)} hours of training data")

    # Create polynomial features for training
    X_train = np.column_stack([
        training_data["NetLoad"].values ** degree
        for degree in range(1, polynomial_degree + 1)
    ])
    y_train = training_data["SystemLambda"].values

    # Train model
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Calculate training performance
    y_train_pred = model.predict(X_train)
    train_residuals = y_train - y_train_pred
    train_mae = mean_absolute_error(y_train, y_train_pred)
    train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
    train_r2 = r2_score(y_train, y_train_pred)

    print(f"   📊 Training Performance:")
    print(f"      MAE: ${train_mae:.2f}/MWh")
    print(f"      RMSE: ${train_rmse:.2f}/MWh")
    print(f"      R²: {train_r2:.3f}")

    # Generate forecast for target date
    print(f"   🔮 Generating forecast...")
    try:
        forecast_net_load = get_net_load_forecast(
            date_from=forecast_date,
            client=client,
            size=10000000
        )

        # Create polynomial features for forecast
        X_forecast = np.column_stack([
            forecast_net_load["NetLoad"].values ** degree
            for degree in range(1, polynomial_degree + 1)
        ])

        # Generate predictions
        forecast_net_load["PredictedLambda"] = model.predict(X_forecast)
        forecast_net_load["Date"] = forecast_date

        print(f"   ✅ Forecast generated for {len(forecast_net_load)} hours")
        print(f"   💰 Average forecast price: ${forecast_net_load['PredictedLambda'].mean():.2f}/MWh")
        print(f"   📊 Price range: ${forecast_net_load['PredictedLambda'].min():.2f} - ${forecast_net_load['PredictedLambda'].max():.2f}/MWh")

        return {
            "forecast": forecast_net_load,
            "model": model,
            "training_performance": {
                "mae": train_mae,
                "rmse": train_rmse,
                "r_squared": train_r2,
            },
            "parameters": {
                "forecast_date": forecast_date,
                "training_days": training_days,
                "training_period": (training_start, training_end),
                "polynomial_degree": polynomial_degree,
            },
        }

    except Exception as e:
        print(f"   ❌ Error generating forecast: {e}")
        return {
            "forecast": pd.DataFrame(),
            "model": model,
            "training_performance": {
                "mae": train_mae,
                "rmse": train_rmse,
                "r_squared": train_r2,
            },
            "parameters": {
                "forecast_date": forecast_date,
                "training_days": training_days,
                "training_period": (training_start, training_end),
                "polynomial_degree": polynomial_degree,
            },
        }


def create_rolling_splits(
    data: pd.DataFrame,
    initial_training_days: int,
    expanding_window: bool = True
) -> List[Tuple[pd.DataFrame, pd.DataFrame, date]]:
    """
    Reusable time-series cross-validation data splitter.

    Splits data by day for rolling forecasts where you train on first n days
    and test on subsequent days one at a time.

    Source: Julia create_rolling_splits function

    Args:
        data: DataFrame with Date column
        initial_training_days: Number of initial days to train on
        expanding_window: If True, expand training window; if False, use fixed window

    Returns:
        List of (train_data, test_data, test_date) tuples

    Raises:
        ValueError: If not enough days in data
    """
    # Ensure data has Date column
    if "Date" not in data.columns:
        data["Date"] = pd.to_datetime(data["DATETIME"]).dt.date

    unique_dates = sorted(data["Date"].unique())
    n_dates = len(unique_dates)

    if n_dates <= initial_training_days:
        raise ValueError(
            f"Not enough days in data. Need more than {initial_training_days} days, "
            f"but only have {n_dates} days."
        )

    splits = []

    # Start forecasting after initial training period
    for i in range(initial_training_days, n_dates):
        test_date = unique_dates[i]

        if expanding_window:
            # Expanding window: use all data from start to day before test
            train_dates = unique_dates[:i]
        else:
            # Fixed window: use last initial_training_days before test
            start_idx = max(0, i - initial_training_days)
            train_dates = unique_dates[start_idx:i]

        train_data = data[data["Date"].isin(train_dates)].copy()
        test_data = data[data["Date"] == test_date].copy()

        if len(train_data) > 0 and len(test_data) > 0:
            splits.append((train_data, test_data, test_date))

    return splits


def rolling_forecast_cv(
    start_date: Optional[Union[str, date]] = None,
    end_date: Optional[Union[str, date]] = None,
    initial_training_days: int = 15,
    polynomial_degree: int = 3,
    expanding_window: bool = True,
    client: Optional[ErcotAPIClient] = None,
) -> Dict:
    """
    Rolling forecast cross-validation using polynomial regression model.

    Source: Julia rolling_forecast_cv function

    Args:
        start_date: Start date of the dataset (default: 30 days ago)
        end_date: End date of the dataset (default: yesterday)
        initial_training_days: Number of initial days to train on (default: 15)
        polynomial_degree: Degree of polynomial features (default: 3)
        expanding_window: If True, expand training window (default: True)
        client: Optional ErcotAPIClient instance

    Returns:
        Dictionary with:
        - predictions: DataFrame with all predictions
        - daily_metrics: DataFrame with per-day performance
        - overall_performance: Dict with aggregate metrics
        - parameters: Dict with CV settings

    Example:
        >>> # Run cross-validation on last 30 days
        >>> result = rolling_forecast_cv(
        ...     start_date="2024-02-01",
        ...     end_date="2024-02-28",
        ...     initial_training_days=15
        ... )
        >>> print(f"Overall MAE: ${result['overall_performance']['mae']:.2f}/MWh")
    """
    if client is None:
        client = ErcotAPIClient()

    # Default dates
    if start_date is None:
        start_date = datetime.now().date() - timedelta(days=30)
    elif isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

    if end_date is None:
        end_date = datetime.now().date() - timedelta(days=1)
    elif isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    print("📊 Starting rolling forecast cross-validation...")
    print(f"   📅 Data period: {start_date} to {end_date}")
    print(f"   🎯 Initial training days: {initial_training_days}")
    print(f"   📈 Window type: {'expanding' if expanding_window else 'fixed'}")
    print(f"   📊 Polynomial degree: {polynomial_degree}")

    # Get all data upfront
    print("   📥 Loading all data...")
    all_net_load = get_net_load_forecast(
        date_from=start_date,
        date_to=end_date,
        client=client,
        size=10000000
    )

    all_lambda = client.fetch_data(
        "da_system_lambda",
        date_from=start_date.strftime("%Y-%m-%d"),
        date_to=end_date.strftime("%Y-%m-%d"),
        size=10000000
    )
    all_lambda = all_lambda[["DATETIME", "SystemLambda"]]

    # Join data
    all_data = all_net_load.merge(all_lambda, on="DATETIME", how="inner")
    all_data["Date"] = pd.to_datetime(all_data["DATETIME"]).dt.date
    all_data = all_data.sort_values("DATETIME").reset_index(drop=True)

    print(f"   ✅ Loaded {len(all_data)} hours of data")

    # Create rolling splits
    splits = create_rolling_splits(all_data, initial_training_days, expanding_window=expanding_window)
    print(f"   🔄 Created {len(splits)} rolling forecast periods")

    # Storage for results
    all_predictions = []
    daily_metrics = []

    # Run cross-validation
    for i, (train_data, test_data, test_date) in enumerate(splits, 1):
        print(f"   🎯 Day {i}/{len(splits)} ({test_date})...", end=" ")

        try:
            # Create polynomial features for training
            X_train = np.column_stack([
                train_data["NetLoad"].values ** degree
                for degree in range(1, polynomial_degree + 1)
            ])
            y_train = train_data["SystemLambda"].values

            # Fit model
            model = LinearRegression()
            model.fit(X_train, y_train)

            # Create features for test data
            X_test = np.column_stack([
                test_data["NetLoad"].values ** degree
                for degree in range(1, polynomial_degree + 1)
            ])
            y_test = test_data["SystemLambda"].values

            # Make predictions
            y_pred = model.predict(X_test)

            # Store predictions
            test_results = test_data[["DATETIME", "Date", "SystemLambda", "NetLoad"]].copy()
            test_results["PredictedLambda"] = y_pred

            all_predictions.append(test_results)

            # Calculate metrics
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)

            daily_metrics.append({
                "date": test_date,
                "mae": mae,
                "rmse": rmse,
                "r_squared": r2,
                "hours": len(test_data),
            })

            print(f"MAE: ${mae:.2f}")

        except Exception as e:
            print(f"❌ Error: {e}")
            continue

    # Combine all predictions
    all_predictions_df = pd.concat(all_predictions, ignore_index=True)

    # Calculate overall performance
    overall_mae = mean_absolute_error(
        all_predictions_df["SystemLambda"],
        all_predictions_df["PredictedLambda"]
    )
    overall_rmse = np.sqrt(mean_squared_error(
        all_predictions_df["SystemLambda"],
        all_predictions_df["PredictedLambda"]
    ))
    overall_r2 = r2_score(
        all_predictions_df["SystemLambda"],
        all_predictions_df["PredictedLambda"]
    )

    print("\n📊 Cross-Validation Summary:")
    print(f"   🎯 Total forecast hours: {len(all_predictions_df)}")
    print(f"   📈 Overall MAE: ${overall_mae:.2f}/MWh")
    print(f"   📈 Overall RMSE: ${overall_rmse:.2f}/MWh")
    print(f"   📈 Overall R²: {overall_r2:.3f}")

    return {
        "predictions": all_predictions_df,
        "daily_metrics": pd.DataFrame(daily_metrics),
        "overall_performance": {
            "mae": overall_mae,
            "rmse": overall_rmse,
            "r_squared": overall_r2,
            "total_hours": len(all_predictions_df),
            "forecast_days": len(daily_metrics),
        },
        "parameters": {
            "start_date": start_date,
            "end_date": end_date,
            "initial_training_days": initial_training_days,
            "polynomial_degree": polynomial_degree,
            "expanding_window": expanding_window,
        },
    }
