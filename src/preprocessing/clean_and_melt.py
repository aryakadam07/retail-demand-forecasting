"""
Retail Demand Forecasting — Data Preprocessing & Unpivoting
Transforms wide M5 sales data into an analytical long format.
Delegates to SalesTransformer for Week 1 Day 5 standardized analytical table creation.
"""

import pandas as pd
from typing import Optional
from src import config
from src.data_ingestion.bq_client import WarehouseClient
from src.preprocessing.transform_sales import SalesTransformer


class DataPreprocessor:
    """Preprocesses raw M5 data and converts wide daily sales columns to long format."""

    def __init__(self, client: Optional[WarehouseClient] = None):
        self.client = client if client is not None else WarehouseClient()
        self.transformer = SalesTransformer(client=self.client)

    def validate_data_quality(self, calendar_df: pd.DataFrame, sales_df: pd.DataFrame, prices_df: pd.DataFrame) -> bool:
        """Executes data quality and sanity checks on raw tables."""
        print("[Quality Check] Starting raw data quality validation...")
        
        # Check required columns
        req_sales_cols = {"item_id", "dept_id", "cat_id", "store_id", "state_id"}
        if not req_sales_cols.issubset(sales_df.columns):
            raise ValueError(f"Sales table missing mandatory columns: {req_sales_cols - set(sales_df.columns)}")

        req_cal_cols = {"date", "wm_yr_wk", "d"}
        if not req_cal_cols.issubset(calendar_df.columns):
            raise ValueError(f"Calendar table missing mandatory columns: {req_cal_cols - set(calendar_df.columns)}")

        req_price_cols = {"store_id", "item_id", "wm_yr_wk", "sell_price"}
        if not req_price_cols.issubset(prices_df.columns):
            raise ValueError(f"Prices table missing mandatory columns: {req_price_cols - set(prices_df.columns)}")

        print("[Quality Check] All data quality checks passed successfully!")
        return True

    def melt_sales_data(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        """Unpivots wide columns (d_1 ... d_N) into long format rows."""
        return self.transformer.melt_sales(sales_df)

    def process_and_join(self, max_items: Optional[int] = None) -> pd.DataFrame:
        """Fetch raw/clean tables, melt sales, join calendar & prices, and produce tidy dataframe."""
        dataset = self.client.dataset_id

        print("[Preprocessing] Fetching tables from warehouse...")
        sales_tbls = ["clean_sales_train_validation", "raw_sales_train_validation", "raw_sales_train"]
        sales_df = None
        for tbl in sales_tbls:
            try:
                res = self.client.query(f"SELECT * FROM {dataset}.{tbl}")
                if not res.empty:
                    sales_df = res
                    break
            except Exception:
                continue

        cal_tbls = ["raw_calendar", "clean_calendar"]
        calendar_df = None
        for tbl in cal_tbls:
            try:
                res = self.client.query(f"SELECT * FROM {dataset}.{tbl}")
                if not res.empty:
                    calendar_df = res
                    break
            except Exception:
                continue

        price_tbls = ["raw_sell_prices", "clean_sell_prices"]
        prices_df = None
        for tbl in price_tbls:
            try:
                res = self.client.query(f"SELECT * FROM {dataset}.{tbl}")
                if not res.empty:
                    prices_df = res
                    break
            except Exception:
                continue

        self.validate_data_quality(calendar_df, sales_df, prices_df)

        if max_items:
            sales_df = sales_df.head(max_items)

        transformed_df = self.transformer.transform(sales_df, calendar_df, prices_df)
        print(f"[Preprocessing] Finished! Final dataset contains {len(transformed_df):,} rows.")
        return transformed_df

    def run_preprocessing_pipeline(self) -> None:
        """Executes full preprocessing and saves analytical staging table stg_sales_long and fact_daily_sales."""
        transformed_df, success = self.transformer.transform_and_load(table_name="fact_daily_sales")
        print(f"[Preprocessing] Preprocessing pipeline completed successfully: {success}")


if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    preprocessor.run_preprocessing_pipeline()
