"""
Retail Demand Forecasting — Exploratory Data Analysis (EDA)
Profiles M5 sales patterns, category distributions, zero-sales ratios, and price elasticity.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from src import config
from src.data_ingestion.bq_client import WarehouseClient


def run_eda():
    """Performs EDA on the processed sales dataset."""
    client = WarehouseClient()
    dataset = client.dataset_id

    print("==================================================")
    print("      RETAIL DEMAND FORECASTING — EDA REPORT      ")
    print("==================================================\n")

    # Fetch snapshot from stg_sales_long table
    query = f"SELECT * FROM {dataset}.stg_sales_long"
    try:
        df = client.query(query)
    except Exception as e:
        print(f"Error querying table {dataset}.stg_sales_long: {e}")
        print("Ensure Phase 1 preprocessing script has been run first.")
        return

    print(f"Dataset Dimensions: {df.shape[0]:,} rows x {df.shape[1]} columns")
    print(f"Date Range: {df['date'].min()} to {df['date'].max()}")
    print(f"Unique Items: {df['item_id'].nunique():,}")
    print(f"Unique Stores: {df['store_id'].nunique()}")
    print(f"Categories: {df['cat_id'].unique().tolist()}")

    # 1. Total & Average Sales by Category
    print("\n--- 1. Sales Performance by Category ---")
    cat_summary = df.groupby("cat_id")["sales"].agg(["sum", "mean", "std", "max"]).reset_index()
    cat_summary.columns = ["Category", "Total Sales", "Mean Daily Sales", "Std Sales", "Max Daily Sales"]
    print(cat_summary.to_string(index=False))

    # 2. Sales by Store
    print("\n--- 2. Sales Performance by Store ---")
    store_summary = df.groupby("store_id")["sales"].agg(["sum", "mean"]).reset_index()
    store_summary.columns = ["Store ID", "Total Sales", "Mean Daily Sales"]
    print(store_summary.to_string(index=False))

    # 3. Zero Sales Analysis
    total_records = len(df)
    zero_sales_count = (df["sales"] == 0).sum()
    zero_ratio = (zero_sales_count / total_records) * 100
    print(f"\n--- 3. Zero Sales Sparsity ---")
    print(f"Zero Sales Days: {zero_sales_count:,} / {total_records:,} ({zero_ratio:.2f}%)")

    # 4. Pricing Summary
    print("\n--- 4. Pricing Summary ---")
    price_summary = df.groupby("cat_id")["sell_price"].agg(["min", "mean", "max"]).reset_index()
    price_summary.columns = ["Category", "Min Price", "Mean Price", "Max Price"]
    print(price_summary.to_string(index=False))

    # 5. Day of Week Seasonality
    print("\n--- 5. Day of Week Sales Pattern ---")
    dow_summary = df.groupby("weekday")["sales"].mean().reindex(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    ).reset_index()
    dow_summary.columns = ["Weekday", "Average Sales"]
    print(dow_summary.to_string(index=False))

    print("\n==================================================")
    print("              EDA COMPLETED SUCCESSFULLY          ")
    print("==================================================")


if __name__ == "__main__":
    run_eda()
