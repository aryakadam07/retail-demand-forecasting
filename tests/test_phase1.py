"""
Retail Demand Forecasting — Phase 1 Automated Tests
Verifies Data Ingestion, Data Preprocessing, Unpivoting, and Warehouse Connectivity.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import pandas as pd
import numpy as np
from src import config
from src.data_ingestion.bq_client import WarehouseClient
from src.data_ingestion.m5_loader import M5DataLoader
from src.preprocessing.clean_and_melt import DataPreprocessor


@pytest.fixture
def warehouse_client():
    """Initializes local DuckDB warehouse client for testing."""
    return WarehouseClient(use_local_duckdb=True)


@pytest.fixture
def sample_m5_data():
    """Generates synthetic M5 test datasets."""
    loader = M5DataLoader()
    return loader.generate_synthetic_m5_data(num_items=5, num_days=14)


def test_warehouse_client_connection(warehouse_client):
    """Verifies that warehouse client creates schema and executes queries."""
    warehouse_client.create_dataset()
    df_sample = pd.DataFrame({"id": [1, 2], "val": ["X", "Y"]})
    assert warehouse_client.load_dataframe(df_sample, "test_table", if_exists="replace") is True

    res = warehouse_client.query(f"SELECT * FROM {warehouse_client.dataset_id}.test_table")
    assert len(res) == 2
    assert res.iloc[0]["val"] == "X"


def test_m5_synthetic_data_generator(sample_m5_data):
    """Verifies shape and columns of synthetic M5 datasets."""
    calendar_df, sales_df, prices_df = sample_m5_data
    
    assert "d" in calendar_df.columns
    assert "date" in calendar_df.columns
    assert len(sales_df) == 5
    assert "d_1" in sales_df.columns
    assert "d_14" in sales_df.columns
    assert "sell_price" in prices_df.columns


def test_preprocessing_unpivoting_logic(sample_m5_data):
    """Verifies melting logic converts wide (5 items x 14 days) to 70 long rows."""
    calendar_df, sales_df, prices_df = sample_m5_data
    preprocessor = DataPreprocessor()
    
    assert preprocessor.validate_data_quality(calendar_df, sales_df, prices_df) is True
    
    melted_df = preprocessor.melt_sales_data(sales_df)
    expected_rows = len(sales_df) * 14  # 5 items * 14 days = 70
    assert len(melted_df) == expected_rows
    assert set(melted_df.columns) == {"id", "item_id", "dept_id", "cat_id", "store_id", "state_id", "d", "sales"}


def test_full_phase1_pipeline(warehouse_client, sample_m5_data):
    """End-to-end integration test for Phase 1 ingestion & preprocessing pipeline."""
    calendar_df, sales_df, prices_df = sample_m5_data
    
    # 1. Ingest raw data into warehouse
    warehouse_client.load_dataframe(calendar_df, "clean_calendar", if_exists="replace")
    warehouse_client.load_dataframe(sales_df, "clean_sales_train_validation", if_exists="replace")
    warehouse_client.load_dataframe(prices_df, "clean_sell_prices", if_exists="replace")

    # 2. Run preprocessing
    preprocessor = DataPreprocessor()
    preprocessor.client = warehouse_client
    stg_sales = preprocessor.process_and_join()

    assert len(stg_sales) == 70
    assert "sales" in stg_sales.columns
    assert "sell_price" in stg_sales.columns
    assert "date" in stg_sales.columns
    assert stg_sales["sales"].isnull().sum() == 0
