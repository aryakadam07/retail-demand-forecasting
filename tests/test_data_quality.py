"""
Retail Demand Forecasting — Automated Tests for Day 4 Data Quality & Standardization
"""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_ingestion.bq_client import WarehouseClient
from src.data_ingestion.bigquery_ingestion import BigQueryIngestionEngine
from src.preprocessing.data_quality import DataQualityChecker, DataQualityReport
from src.preprocessing.clean_calendar import clean_calendar_data
from src.preprocessing.clean_sales import clean_sales_data
from src.preprocessing.clean_prices import clean_prices_data
from src.preprocessing.run_day4_pipeline import Day4DataQualityPipeline


@pytest.fixture(scope="module")
def setup_warehouse():
    """Initializes local warehouse and populates raw tables."""
    client = WarehouseClient(use_local_duckdb=True)
    engine = BigQueryIngestionEngine(use_local_duckdb=True)
    engine.run_full_ingestion()
    return client


def test_calendar_quality_checker():
    """Tests calendar quality checker on synthetic sample data."""
    sample_cal = pd.DataFrame({
        "date": ["2011-01-29", "2011-01-30", "invalid_date", None],
        "wm_yr_wk": [11101, 11101, 11101, 11101],
        "weekday": ["Saturday", "Sunday", "Monday", None],
        "wday": [1, 2, 3, 4],
        "month": [1, 1, 1, 1],
        "year": [2011, 2011, 2011, 2011],
        "event_name_1": [None, "SuperBowl", None, None],
        "event_type_1": [None, "Sporting", "InvalidType", None]
    })
    report = DataQualityChecker.audit_calendar_data(sample_cal)
    assert isinstance(report, DataQualityReport)
    assert report.num_rows == 4
    # Check that missing and invalid date issues were detected
    check_map = {c["name"]: c for c in report.checks}
    assert check_map["Missing Dates"]["passed"] is False
    assert check_map["Valid Date Format"]["passed"] is False
    assert check_map["Unexpected Event Types"]["passed"] is False


def test_sales_quality_checker():
    """Tests sales quality checker on synthetic sample data with negative and missing values."""
    sample_sales = pd.DataFrame({
        "id": ["HOBBIES_1_001_CA_1_validation", "HOBBIES_1_002_CA_1_validation"],
        "item_id": ["HOBBIES_1_001", "HOBBIES_1_002"],
        "dept_id": ["HOBBIES_1", "HOBBIES_1"],
        "cat_id": ["HOBBIES", "HOBBIES"],
        "store_id": ["CA_1", "CA_1"],
        "state_id": ["CA", "CA"],
        "d_1": [5, -2],  # Negative sale
        "d_2": [10, np.nan]  # Missing sale
    })
    report = DataQualityChecker.audit_sales_data(sample_sales)
    assert isinstance(report, DataQualityReport)
    check_map = {c["name"]: c for c in report.checks}
    assert check_map["Negative Sales Volumes"]["passed"] is False
    assert check_map["Missing Sales Values"]["passed"] is False


def test_prices_quality_checker():
    """Tests prices quality checker on sample data with negative and zero prices."""
    sample_prices = pd.DataFrame({
        "store_id": ["CA_1", "CA_1", "CA_1"],
        "item_id": ["HOBBIES_1_001", "HOBBIES_1_001", "HOBBIES_1_002"],
        "wm_yr_wk": [11101, 11101, 11101],  # Duplicate key combo
        "sell_price": [1.99, -0.50, 0.0]  # Negative and zero prices
    })
    report = DataQualityChecker.audit_prices_data(sample_prices)
    assert isinstance(report, DataQualityReport)
    check_map = {c["name"]: c for c in report.checks}
    assert check_map["Duplicate Store-Item-Week Keys"]["passed"] is False
    assert check_map["Negative Prices"]["passed"] is False
    assert check_map["Zero Prices"]["passed"] is False


def test_clean_calendar_module(setup_warehouse):
    """Tests clean_calendar module against warehouse tables."""
    client = setup_warehouse
    clean_df, success = clean_calendar_data(client=client)
    assert success is True
    assert len(clean_df) > 0
    assert "date" in clean_df.columns
    # Check date column is standardized ISO string format
    assert pd.to_datetime(clean_df["date"], errors="coerce").notnull().all()

    verification = client.verify_table("clean_calendar")
    assert verification["exists"] is True
    assert verification["row_count"] == len(clean_df)


def test_clean_sales_module(setup_warehouse):
    """Tests clean_sales module against warehouse tables."""
    client = setup_warehouse
    clean_df, success = clean_sales_data(client=client)
    assert success is True
    assert len(clean_df) > 0

    d_cols = [c for c in clean_df.columns if c.startswith("d_")]
    assert len(d_cols) > 0
    # Ensure all sales values are non-negative integers
    sales_matrix = clean_df[d_cols]
    assert (sales_matrix >= 0).all().all()

    verification = client.verify_table("clean_sales_train_validation")
    assert verification["exists"] is True
    assert verification["row_count"] == len(clean_df)


def test_clean_prices_module(setup_warehouse):
    """Tests clean_prices module against warehouse tables."""
    client = setup_warehouse
    clean_df, success = clean_prices_data(client=client)
    assert success is True
    assert len(clean_df) > 0
    assert "sell_price" in clean_df.columns
    assert pd.api.types.is_numeric_dtype(clean_df["sell_price"])

    verification = client.verify_table("clean_sell_prices")
    assert verification["exists"] is True
    assert verification["row_count"] == len(clean_df)


def test_full_day4_pipeline(setup_warehouse):
    """Tests complete Day4DataQualityPipeline execution."""
    pipeline = Day4DataQualityPipeline(use_local_duckdb=True)
    results = pipeline.run_pipeline()

    assert "calendar_report" in results
    assert "sales_report" in results
    assert "prices_report" in results
    assert "verification" in results

    assert results["verification"]["clean_calendar"]["exists"] is True
    assert results["verification"]["clean_sales_train_validation"]["exists"] is True
    assert results["verification"]["clean_sell_prices"]["exists"] is True
