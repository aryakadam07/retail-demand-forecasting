"""
Unit & Integration Tests for Week 1 Day 5 Sales Data Transformation Module
Tests wide-to-long unpivoting, date mapping, sell price joining, data standardization, and table creation.
"""

import pytest
import pandas as pd
import numpy as np
from src.data_ingestion.bq_client import WarehouseClient
from src.preprocessing.transform_sales import SalesTransformer
from src.preprocessing.run_day5_pipeline import Day5TransformationPipeline


@pytest.fixture
def mock_sales_wide():
    return pd.DataFrame({
        "id": ["HOBBIES_1_001_CA_1_validation", "HOBBIES_1_002_CA_1_validation"],
        "item_id": ["HOBBIES_1_001", "HOBBIES_1_002"],
        "dept_id": ["HOBBIES_1", "HOBBIES_1"],
        "cat_id": ["HOBBIES", "HOBBIES"],
        "store_id": ["CA_1", "CA_1"],
        "state_id": ["CA", "CA"],
        "d_1": [0, 5],
        "d_2": [2, 10],
        "d_3": [1, 0]
    })


@pytest.fixture
def mock_calendar():
    return pd.DataFrame({
        "date": ["2011-01-29", "2011-01-30", "2011-01-31"],
        "wm_yr_wk": [11101, 11101, 11101],
        "weekday": ["Saturday", "Sunday", "Monday"],
        "wday": [1, 2, 3],
        "month": [1, 1, 1],
        "year": [2011, 2011, 2011],
        "d": ["d_1", "d_2", "d_3"]
    })


@pytest.fixture
def mock_prices():
    return pd.DataFrame({
        "store_id": ["CA_1", "CA_1"],
        "item_id": ["HOBBIES_1_001", "HOBBIES_1_002"],
        "wm_yr_wk": [11101, 11101],
        "sell_price": [8.26, 3.97]
    })


def test_melt_sales(mock_sales_wide):
    transformer = SalesTransformer(client=None)
    long_df = transformer.melt_sales(mock_sales_wide)

    # Verify rows: 2 items * 3 days = 6 rows
    assert len(long_df) == 6
    assert set(long_df.columns).issuperset({"item_id", "dept_id", "cat_id", "store_id", "state_id", "d", "sales"})
    assert long_df["sales"].dtype in [np.int64, np.int32, int]
    assert (long_df["sales"] >= 0).all()


def test_map_dates(mock_sales_wide, mock_calendar):
    transformer = SalesTransformer(client=None)
    long_df = transformer.melt_sales(mock_sales_wide)
    mapped_df = transformer.map_dates(long_df, mock_calendar)

    assert "date" in mapped_df.columns
    assert "wm_yr_wk" in mapped_df.columns
    assert mapped_df["date"].isnull().sum() == 0
    # d_1 mapped to 2011-01-29
    d1_records = mapped_df[mapped_df["d"] == "d_1"]
    assert (d1_records["date"] == "2011-01-29").all()


def test_join_sell_prices(mock_sales_wide, mock_calendar, mock_prices):
    transformer = SalesTransformer(client=None)
    long_df = transformer.melt_sales(mock_sales_wide)
    mapped_df = transformer.map_dates(long_df, mock_calendar)
    final_df = transformer.join_sell_prices(mapped_df, mock_prices)

    assert "sell_price" in final_df.columns
    assert final_df["sell_price"].isnull().sum() == 0
    
    h1_price = final_df[final_df["item_id"] == "HOBBIES_1_001"]["sell_price"].iloc[0]
    assert h1_price == 8.26


def test_sales_sum_conservation(mock_sales_wide, mock_calendar, mock_prices):
    transformer = SalesTransformer(client=None)
    raw_sum = mock_sales_wide[["d_1", "d_2", "d_3"]].values.sum()
    
    transformed_df = transformer.transform(mock_sales_wide, mock_calendar, mock_prices)
    transformed_sum = transformed_df["sales"].sum()

    assert raw_sum == transformed_sum


def test_key_uniqueness(mock_sales_wide, mock_calendar, mock_prices):
    transformer = SalesTransformer(client=None)
    transformed_df = transformer.transform(mock_sales_wide, mock_calendar, mock_prices)

    dup_count = transformed_df.duplicated(subset=["date", "item_id", "store_id"]).sum()
    assert dup_count == 0


def test_day5_pipeline_execution():
    client = WarehouseClient()
    pipeline = Day5TransformationPipeline(use_local_duckdb=client.use_local_duckdb)
    result = pipeline.run_pipeline(target_table="fact_daily_sales")

    assert result["success"] is True
    assert result["metrics"]["total_records"] > 0
    assert result["metrics"]["sales_match"] is True
    assert result["verification"]["exists"] is True
