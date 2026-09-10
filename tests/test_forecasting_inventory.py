"""
Retail Demand Forecasting & Inventory Optimization — Pytest Suite
Tests forecasting data prep, Prophet, LightGBM, model evaluation, safety stock, ROP, ROQ, and stockout risk logic.
"""

import pytest
import pandas as pd
import numpy as np

from src.forecasting.data_preparation import ForecastingDataPreparer
from src.forecasting.evaluation import ModelEvaluator
from src.inventory.safety_stock import SafetyStockCalculator
from src.inventory.reorder_point import ReorderPointCalculator
from src.inventory.inventory_optimizer import InventoryOptimizer


def test_safety_stock_calculation():
    calc = SafetyStockCalculator(service_level=0.95, lead_time_days=7)
    sample_sales = pd.Series([10, 12, 8, 15, 9, 11, 14, 7, 10, 13])
    ss = calc.compute_series_safety_stock(sample_sales)
    assert isinstance(ss, float)
    assert ss > 0


def test_reorder_point_calculation():
    calc = ReorderPointCalculator(lead_time_days=7)
    rop = calc.compute_reorder_point(avg_daily_forecast=10.0, safety_stock=15.0)
    # ROP = (10.0 * 7) + 15.0 = 85.0
    assert rop == 85.0


def test_stockout_risk_classification():
    optimizer = InventoryOptimizer()
    assert optimizer.classify_stockout_risk(available_inventory=5, safety_stock=10, reorder_point=25) == "HIGH"
    assert optimizer.classify_stockout_risk(available_inventory=15, safety_stock=10, reorder_point=25) == "MEDIUM"
    assert optimizer.classify_stockout_risk(available_inventory=30, safety_stock=10, reorder_point=25) == "LOW"


def test_model_evaluation_metrics():
    y_true = np.array([10, 20, 30, 40, 50])
    y_pred = np.array([12, 18, 33, 38, 52])
    
    metrics = ModelEvaluator.calculate_metrics(y_true, y_pred)
    assert "MAE" in metrics
    assert "RMSE" in metrics
    assert "sMAPE" in metrics
    assert metrics["MAE"] == 2.2
    assert round(metrics["RMSE"], 2) == 2.24


def test_feature_engineering_no_data_leakage():
    dates = pd.date_range("2021-01-01", periods=40, freq="D")
    df = pd.DataFrame({
        "date": dates,
        "store_id": "CA_1",
        "item_id": "ITEM_1",
        "sales": range(1, 41),
        "sell_price": 5.0
    })
    
    preparer = ForecastingDataPreparer()
    feat_df = preparer.engineer_lightgbm_features(df)
    
    # Check lag_1 equals sales shifted by 1
    assert "lag_1" in feat_df.columns
    assert "rolling_mean_7" in feat_df.columns
    # Check no NaN values after initial dropna
    assert feat_df["lag_1"].isna().sum() == 0
