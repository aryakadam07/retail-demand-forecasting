"""
Unit Test Suite for Week 1 Day 6 Transformed Sales Data Validation Module & Pipeline.
"""

import os
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from src import config
from src.data_ingestion.bq_client import WarehouseClient
from src.preprocessing.validate_transformed import SalesDataValidator
from src.preprocessing.run_day6_pipeline import Day6ValidationPipeline


@pytest.fixture
def sample_transformed_sales_df():
    """Generates a clean synthetic transformed sales DataFrame for testing."""
    dates = ["2011-01-29", "2011-01-30", "2011-01-31", "2011-02-01"]
    items = ["HOBBIES_1_001", "FOODS_1_001"]
    stores = ["CA_1", "TX_1"]

    records = []
    for d in dates:
        for item in items:
            for store in stores:
                dept = "HOBBIES_1" if "HOBBIES" in item else "FOODS_1"
                cat = "HOBBIES" if "HOBBIES" in item else "FOODS"
                state = store.split("_")[0]
                price = 8.26 if "HOBBIES" in item else 3.50
                records.append({
                    "date": d,
                    "item_id": item,
                    "dept_id": dept,
                    "cat_id": cat,
                    "store_id": store,
                    "state_id": state,
                    "sales": 5,
                    "sell_price": price
                })
    return pd.DataFrame(records)


def test_fact_daily_sales_validation_clean(sample_transformed_sales_df):
    """Verifies that clean sample data passes all validation checks."""
    validator = SalesDataValidator(client=WarehouseClient(use_local_duckdb=True))
    metrics = validator.validate_fact_daily_sales(sample_transformed_sales_df)

    assert metrics["row_count"] == 16
    assert metrics["row_count_status"] == "PASS"
    assert metrics["min_date"] == "2011-01-29"
    assert metrics["max_date"] == "2011-02-01"
    assert metrics["unique_items"] == 2
    assert metrics["unique_stores"] == 2
    assert metrics["unique_depts"] == 2
    assert metrics["unique_cats"] == 2
    assert metrics["total_sales"] == 80
    assert metrics["negative_sales_count"] == 0
    assert metrics["negative_sales_status"] == "PASS"
    assert metrics["missing_dates"] == 0
    assert metrics["missing_dates_status"] == "PASS"
    assert metrics["duplicate_combinations"] == 0
    assert metrics["duplicates_status"] == "PASS"
    assert metrics["invalid_prices"] == 0
    assert metrics["invalid_prices_status"] == "PASS"


def test_fact_daily_sales_validation_corrupted(sample_transformed_sales_df):
    """Verifies that negative sales, duplicates, and invalid prices are flagged appropriately."""
    corrupted_df = sample_transformed_sales_df.copy()
    
    # Inject negative sales
    corrupted_df.loc[0, "sales"] = -5
    
    # Inject duplicate combination
    dup_row = corrupted_df.iloc[1:2].copy()
    corrupted_df = pd.concat([corrupted_df, dup_row], ignore_index=True)
    
    # Inject invalid price
    corrupted_df.loc[2, "sell_price"] = -1.0

    validator = SalesDataValidator(client=WarehouseClient(use_local_duckdb=True))
    metrics = validator.validate_fact_daily_sales(corrupted_df)

    assert metrics["negative_sales_count"] > 0
    assert metrics["negative_sales_status"] == "FAIL"
    assert metrics["duplicate_combinations"] > 0
    assert metrics["duplicates_status"] == "FAIL"
    assert metrics["invalid_prices"] > 0
    assert metrics["invalid_prices_status"] == "FAIL"


def test_m5_hierarchy_verification_pass(sample_transformed_sales_df):
    """Verifies that consistent M5 hierarchy passes validation."""
    validator = SalesDataValidator(client=WarehouseClient(use_local_duckdb=True))
    hierarchy = validator.verify_m5_hierarchy(sample_transformed_sales_df)

    assert hierarchy["item_to_dept_status"] == "PASS"
    assert hierarchy["dept_to_cat_status"] == "PASS"
    assert hierarchy["item_to_cat_status"] == "PASS"
    assert hierarchy["store_to_state_status"] == "PASS"
    assert hierarchy["overall_hierarchy_status"] == "PASS"
    assert len(hierarchy["inconsistencies"]) == 0


def test_m5_hierarchy_verification_fail(sample_transformed_sales_df):
    """Verifies that inconsistent hierarchy mappings are detected and reported."""
    broken_df = sample_transformed_sales_df.copy()
    # Map item HOBBIES_1_001 to a second department
    broken_df.loc[0, "dept_id"] = "FOODS_1"
    # Map store CA_1 to a second state (change CA_1 row from CA to TX)
    broken_df.loc[0, "state_id"] = "TX"

    validator = SalesDataValidator(client=WarehouseClient(use_local_duckdb=True))
    hierarchy = validator.verify_m5_hierarchy(broken_df)

    assert hierarchy["item_to_dept_status"] == "FAIL"
    assert hierarchy["store_to_state_status"] == "FAIL"
    assert hierarchy["overall_hierarchy_status"] == "FAIL"
    assert len(hierarchy["inconsistencies"]) >= 2


def test_sales_analysis_calculations(sample_transformed_sales_df):
    """Verifies descriptive sales metrics and aggregation outputs."""
    validator = SalesDataValidator(client=WarehouseClient(use_local_duckdb=True))
    sales_analysis = validator.perform_sales_analysis(sample_transformed_sales_df)

    assert "daily_total_sales" in sales_analysis
    assert "sales_by_store" in sales_analysis
    assert "sales_by_category" in sales_analysis
    assert "sales_by_department" in sales_analysis
    assert "top_selling_items" in sales_analysis
    assert "trends_summary" in sales_analysis

    assert len(sales_analysis["daily_total_sales"]) == 4
    assert len(sales_analysis["sales_by_store"]) == 2
    assert sales_analysis["trends_summary"]["first_day_sales"] == 20
    assert sales_analysis["trends_summary"]["last_day_sales"] == 20


def test_temporal_coverage_analysis(sample_transformed_sales_df):
    """Verifies temporal pattern extraction across day of week and weekend contrast."""
    validator = SalesDataValidator(client=WarehouseClient(use_local_duckdb=True))
    temporal = validator.check_temporal_coverage(sample_transformed_sales_df)

    assert "sales_by_year" in temporal
    assert "sales_by_month" in temporal
    assert "sales_by_day_of_week" in temporal
    assert "weekend_vs_weekday" in temporal

    dow_df = temporal["sales_by_day_of_week"]
    assert not dow_df.empty
    assert set(dow_df["day_name"]).issubset({"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"})


def test_price_information_validation(sample_transformed_sales_df):
    """Verifies price metrics, missing price stats, and item/store price variation."""
    validator = SalesDataValidator(client=WarehouseClient(use_local_duckdb=True))
    price_info = validator.validate_price_information(sample_transformed_sales_df)

    stats = price_info["overall_price_stats"]
    assert stats["min_price"] == 3.50
    assert stats["max_price"] == 8.26
    assert stats["missing_count"] == 0
    assert stats["missing_pct"] == 0.0

    assert "price_by_category" in price_info
    assert "item_store_price_variation" in price_info


def test_validation_report_generation(sample_transformed_sales_df):
    """Verifies report string generation and presence of key sections and statuses."""
    validator = SalesDataValidator(client=WarehouseClient(use_local_duckdb=True))
    report = validator.generate_validation_report(sample_transformed_sales_df, raw_sales_total=80)

    assert "WEEK 1 FINAL ETL & DATA QUALITY VALIDATION REPORT" in report
    assert "[PASS]" in report
    assert "DATASET SIZE & COVERAGE CHECKS" in report
    assert "M5 HIERARCHY RELATIONSHIP VALIDATION" in report
    assert "SELL PRICE DISTRIBUTION & VARIATION" in report


def test_full_day6_pipeline_execution():
    """Verifies end-to-end execution of Day 6 pipeline."""
    pipeline = Day6ValidationPipeline(use_local_duckdb=True)
    res = pipeline.run_pipeline()

    assert res["validation_metrics"]["row_count"] > 0
    assert res["validation_metrics"]["row_count_status"] == "PASS"
    assert res["hierarchy_metrics"]["overall_hierarchy_status"] == "PASS"
    assert len(res["report_text"]) > 0

    report_path = config.PROCESSED_DATA_DIR / "week1_validation_report.txt"
    assert report_path.exists()
