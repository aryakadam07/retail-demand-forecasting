"""
Retail Demand Forecasting — Data Preprocessing & Unpivoting
Transforms wide M5 sales data into an analytical long format.
"""

import pandas as pd
import numpy as np
from typing import Optional
from src import config
from src.data_ingestion.bq_client import WarehouseClient


class DataPreprocessor:
    """Preprocesses raw M5 data and converts wide daily sales columns to long format."""

    def __init__(self):
        self.client = WarehouseClient()

    def validate_data_quality(self, calendar_df: pd.DataFrame, sales_df: pd.DataFrame, prices_df: pd.DataFrame) -> bool:
        """Executes data quality and sanity checks on raw tables."""
        print("[Quality Check] Starting raw data quality validation...")
        
        # Check required columns
        req_sales_cols = {"id", "item_id", "dept_id", "cat_id", "store_id", "state_id"}
        if not req_sales_cols.issubset(sales_df.columns):
            raise ValueError(f"Sales table missing mandatory columns: {req_sales_cols - set(sales_df.columns)}")

        req_cal_cols = {"date", "wm_yr_wk", "d", "event_name_1", "snap_CA", "snap_TX", "snap_WI"}
        if not req_cal_cols.issubset(calendar_df.columns):
            raise ValueError(f"Calendar table missing mandatory columns: {req_cal_cols - set(calendar_df.columns)}")

        req_price_cols = {"store_id", "item_id", "wm_yr_wk", "sell_price"}
        if not req_price_cols.issubset(prices_df.columns):
            raise ValueError(f"Prices table missing mandatory columns: {req_price_cols - set(prices_df.columns)}")

        # Check nulls in primary identifiers
        if sales_df["id"].isnull().any():
            raise ValueError("Found null identifiers in raw sales data.")

        print("[Quality Check] All data quality checks passed successfully!")
        return True

    def melt_sales_data(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        """Unpivots wide columns (d_1 ... d_N) into long format rows."""
        id_vars = ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]
        d_cols = [c for c in sales_df.columns if c.startswith("d_")]

        print(f"[Melting] Unpivoting {len(d_cols)} day columns across {len(sales_df)} items...")
        long_df = pd.melt(
            sales_df,
            id_vars=id_vars,
            value_vars=d_cols,
            var_name="d",
            value_name="sales"
        )
        long_df["sales"] = long_df["sales"].fillna(0).astype(int)
        return long_df

    def process_and_join(self, max_items: Optional[int] = None) -> pd.DataFrame:
        """Fetch raw tables, melt sales, join calendar & prices, and produce tidy dataframe."""
        dataset = self.client.dataset_id

        print("[Preprocessing] Fetching raw tables from warehouse...")
        calendar_df = self.client.query(f"SELECT * FROM {dataset}.raw_calendar")
        sales_df = self.client.query(f"SELECT * FROM {dataset}.raw_sales_train")
        prices_df = self.client.query(f"SELECT * FROM {dataset}.raw_sell_prices")

        self.validate_data_quality(calendar_df, sales_df, prices_df)

        if max_items:
            sales_df = sales_df.head(max_items)

        # 1. Melt Sales
        long_sales = self.melt_sales_data(sales_df)

        # 2. Join Calendar Metadata
        print("[Preprocessing] Merging calendar metadata...")
        long_sales = long_sales.merge(
            calendar_df[["d", "date", "wm_yr_wk", "weekday", "wday", "month", "year", 
                         "event_name_1", "event_type_1", "snap_CA", "snap_TX", "snap_WI"]],
            on="d",
            how="left"
        )

        # 3. Join Sell Prices
        print("[Preprocessing] Merging unit pricing...")
        long_sales = long_sales.merge(
            prices_df[["store_id", "item_id", "wm_yr_wk", "sell_price"]],
            on=["store_id", "item_id", "wm_yr_wk"],
            how="left"
        )

        # Handle missing prices via backward/forward fill per item-store
        long_sales["sell_price"] = long_sales.groupby(["store_id", "item_id"])["sell_price"].transform(
            lambda g: g.bfill().ffill()
        ).fillna(0.0)

        # Convert date to datetime
        long_sales["date"] = pd.to_datetime(long_sales["date"])
        long_sales = long_sales.sort_values(by=["store_id", "item_id", "date"]).reset_index(drop=True)

        print(f"[Preprocessing] Finished! Final dataset contains {len(long_sales):,} rows.")
        return long_sales

    def run_preprocessing_pipeline(self) -> None:
        """Executes full preprocessing and saves analytical staging table stg_sales_long."""
        processed_df = self.process_and_join()
        
        # Save snapshot locally for fast access
        try:
            parquet_path = config.PROCESSED_DATA_DIR / "stg_sales_long.parquet"
            processed_df.to_parquet(parquet_path, index=False)
            print(f"[Preprocessing] Saved parquet snapshot to {parquet_path}")
        except Exception:
            csv_path = config.PROCESSED_DATA_DIR / "stg_sales_long.csv"
            processed_df.to_csv(csv_path, index=False)
            print(f"[Preprocessing] Saved CSV snapshot to {csv_path}")

        # Store in Data Warehouse
        print(f"[Preprocessing] Ingesting 'stg_sales_long' table into warehouse...")
        self.client.load_dataframe(processed_df, "stg_sales_long", if_exists="replace")


if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    preprocessor.run_preprocessing_pipeline()
