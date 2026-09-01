"""
Retail Demand Forecasting — Sales Data Transformation Module
Transforms wide M5 sales datasets into a standardized long analytical table (`fact_daily_sales`).
Maps day IDs (d_1...d_N) to calendar dates and integrates weekly sell prices.
"""

import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import config
from src.data_ingestion.bq_client import WarehouseClient

logger = logging.getLogger(__name__)


class SalesTransformer:
    """Transforms wide M5 daily sales data into long analytical fact table format."""

    def __init__(self, client: Optional[WarehouseClient] = None):
        self.client = client if client is not None else WarehouseClient()
        self.dataset_id = self.client.dataset_id

    def melt_sales(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms wide sales dataframe (d_1 ... d_N) to long format.

        Args:
            sales_df (pd.DataFrame): Wide sales dataframe.

        Returns:
            pd.DataFrame: Long sales dataframe with columns ['id', 'item_id', 'dept_id', 'cat_id', 'store_id', 'state_id', 'd', 'sales'].
        """
        id_vars = [c for c in ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"] if c in sales_df.columns]
        d_cols = [c for c in sales_df.columns if c.startswith("d_")]

        logger.info("Unpivoting %d day columns across %d item-store records...", len(d_cols), len(sales_df))
        long_df = pd.melt(
            sales_df,
            id_vars=id_vars,
            value_vars=d_cols,
            var_name="d",
            value_name="sales"
        )

        # Standardize sales column to non-negative integer
        long_df["sales"] = pd.to_numeric(long_df["sales"], errors="coerce").fillna(0)
        long_df["sales"] = np.clip(long_df["sales"], a_min=0, a_max=None).astype(int)

        return long_df

    def map_dates(self, long_df: pd.DataFrame, calendar_df: pd.DataFrame) -> pd.DataFrame:
        """
        Maps day IDs (d_1, d_2, ...) to actual ISO calendar dates and weekly temporal keys.

        Args:
            long_df (pd.DataFrame): Long sales dataframe.
            calendar_df (pd.DataFrame): Cleaned calendar metadata dataframe.

        Returns:
            pd.DataFrame: DataFrame with added 'date' and 'wm_yr_wk' columns.
        """
        logger.info("Mapping day IDs to ISO calendar dates and weekly temporal IDs...")
        cal_cols = [c for c in ["d", "date", "wm_yr_wk"] if c in calendar_df.columns]
        
        merged_df = long_df.merge(
            calendar_df[cal_cols],
            on="d",
            how="left"
        )

        # Ensure date is string formatted as YYYY-MM-DD
        if "date" in merged_df.columns:
            merged_df["date"] = pd.to_datetime(merged_df["date"]).dt.strftime("%Y-%m-%d")

        # Ensure wm_yr_wk is integer
        if "wm_yr_wk" in merged_df.columns:
            merged_df["wm_yr_wk"] = pd.to_numeric(merged_df["wm_yr_wk"], errors="coerce").fillna(0).astype(int)

        return merged_df

    def join_sell_prices(self, sales_with_date_df: pd.DataFrame, prices_df: pd.DataFrame) -> pd.DataFrame:
        """
        Integrates weekly sell price data using store_id, item_id, and wm_yr_wk.

        Args:
            sales_with_date_df (pd.DataFrame): Long sales dataframe containing 'wm_yr_wk'.
            prices_df (pd.DataFrame): Unit sell price dataframe.

        Returns:
            pd.DataFrame: Merged dataframe with 'sell_price' column.
        """
        logger.info("Joining weekly sell prices on (store_id, item_id, wm_yr_wk)...")
        price_cols = [c for c in ["store_id", "item_id", "wm_yr_wk", "sell_price"] if c in prices_df.columns]

        merged_df = sales_with_date_df.merge(
            prices_df[price_cols],
            on=["store_id", "item_id", "wm_yr_wk"],
            how="left"
        )

        # Ensure sell_price numeric float
        if "sell_price" in merged_df.columns:
            merged_df["sell_price"] = pd.to_numeric(merged_df["sell_price"], errors="coerce")

        return merged_df

    def transform(self, sales_df: pd.DataFrame, calendar_df: pd.DataFrame, prices_df: pd.DataFrame) -> pd.DataFrame:
        """
        Executes full transformation flow on provided DataFrames.

        Returns:
            pd.DataFrame: Standardized long analytical sales DataFrame.
        """
        # 1. Wide to Long Unpivoting
        long_sales = self.melt_sales(sales_df)

        # 2. Date & Week Mapping
        sales_with_dates = self.map_dates(long_sales, calendar_df)

        # 3. Sell Price Integration
        final_df = self.join_sell_prices(sales_with_dates, prices_df)

        # Select & Order analytical columns
        target_cols = ["date", "item_id", "dept_id", "cat_id", "store_id", "state_id", "sales", "sell_price"]
        available_cols = [c for c in target_cols if c in final_df.columns]
        
        # Keep any extra hierarchy columns if present
        extra_cols = [c for c in final_df.columns if c not in available_cols and c not in ["id", "d", "wm_yr_wk"]]
        final_cols = available_cols + extra_cols

        final_df = final_df[final_cols].sort_values(by=["date", "store_id", "item_id"]).reset_index(drop=True)
        return final_df

    def transform_and_load(self, table_name: str = "fact_daily_sales") -> Tuple[pd.DataFrame, bool]:
        """
        Fetches clean/raw tables from warehouse, transforms sales data into analytical format,
        and saves into BigQuery / Warehouse target table.

        Args:
            table_name (str): Target warehouse table name (default 'fact_daily_sales').

        Returns:
            Tuple[pd.DataFrame, bool]: Transformed DataFrame and ingestion success status.
        """
        dataset = self.dataset_id
        logger.info("Reading input tables from warehouse dataset '%s'...", dataset)

        # Priority order: Clean table from Day 4, then raw tables
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
        if sales_df is None:
            raise ValueError(f"No sales table found in warehouse dataset '{dataset}'.")

        cal_tbls = ["clean_calendar", "raw_calendar"]
        calendar_df = None
        for tbl in cal_tbls:
            try:
                res = self.client.query(f"SELECT * FROM {dataset}.{tbl}")
                if not res.empty:
                    calendar_df = res
                    break
            except Exception:
                continue
        if calendar_df is None:
            raise ValueError(f"No calendar table found in warehouse dataset '{dataset}'.")

        price_tbls = ["clean_sell_prices", "raw_sell_prices"]
        prices_df = None
        for tbl in price_tbls:
            try:
                res = self.client.query(f"SELECT * FROM {dataset}.{tbl}")
                if not res.empty:
                    prices_df = res
                    break
            except Exception:
                continue
        if prices_df is None:
            raise ValueError(f"No prices table found in warehouse dataset '{dataset}'.")

        transformed_df = self.transform(sales_df, calendar_df, prices_df)

        # Save snapshot locally for fast access
        parquet_path = config.PROCESSED_DATA_DIR / "fact_daily_sales.parquet"
        csv_path = config.PROCESSED_DATA_DIR / "fact_daily_sales.csv"
        try:
            transformed_df.to_parquet(parquet_path, index=False)
            logger.info("Saved local parquet snapshot to '%s'", parquet_path)
        except Exception:
            transformed_df.to_csv(csv_path, index=False)
            logger.info("Saved local CSV snapshot to '%s'", csv_path)

        # Ingest into Data Warehouse
        logger.info("Ingesting %d analytical sales records into table '%s'...", len(transformed_df), table_name)
        success = self.client.load_dataframe(transformed_df, table_name, if_exists="replace")

        # Also populate stg_sales_long alias for backward compatibility
        self.client.load_dataframe(transformed_df, "stg_sales_long", if_exists="replace")

        return transformed_df, success


def transform_sales_data(client: Optional[WarehouseClient] = None, table_name: str = "fact_daily_sales") -> Tuple[pd.DataFrame, bool]:
    """Convenience function for Day 5 transformation execution."""
    transformer = SalesTransformer(client=client)
    return transformer.transform_and_load(table_name=table_name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    df, success = transform_sales_data()
    print(f"Transform Sales execution status: {success}, Rows: {len(df):,}")
