"""
Retail Demand Forecasting — Time Series Data Preparation Engine
Prepares analytical sales data from warehouse (BigQuery / DuckDB) for Prophet and LightGBM models.
"""

import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_ingestion.bq_client import WarehouseClient

logger = logging.getLogger("DataPreparation")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class ForecastingDataPreparer:
    """Handles data extraction, reindexing, feature engineering, and temporal validation splits."""

    def __init__(self, client: Optional[WarehouseClient] = None, validation_days: int = 28):
        self.client = client or WarehouseClient()
        self.validation_days = validation_days

    def load_analytical_data(self, series_limit: Optional[int] = None) -> pd.DataFrame:
        """
        Extracts `mart_sales_forecasting` dataset from data warehouse.
        """
        dataset = self.client.dataset_id
        table_name = f"{dataset}.mart_sales_forecasting"
        
        logger.info("Extracting analytical sales data from '%s'...", table_name)
        sql = f"SELECT * FROM {table_name} ORDER BY item_id, store_id, date"
        
        df = self.client.query(sql)
        if df.empty:
            raise ValueError(f"Analytical table '{table_name}' returned zero records.")

        # Ensure date parsing
        df["date"] = pd.to_datetime(df["date"])
        df["sales"] = pd.to_numeric(df["sales"], errors="coerce").fillna(0)
        if "sell_price" in df.columns:
            df["sell_price"] = pd.to_numeric(df["sell_price"], errors="coerce").fillna(0)

        # Standardize hierarchy columns
        if "category" not in df.columns and "cat_id" in df.columns:
            df["category"] = df["cat_id"]
        if "department" not in df.columns and "dept_id" in df.columns:
            df["department"] = df["dept_id"]

        if series_limit:
            # Filter to top series by volume for scalable performance
            series_totals = df.groupby(["store_id", "item_id"])["sales"].sum().reset_index()
            top_series = series_totals.sort_values(by="sales", ascending=False).head(series_limit)
            df = df.merge(top_series[["store_id", "item_id"]], on=["store_id", "item_id"], how="inner")
            logger.info("Filtered dataset to top %d item-store series (%d total rows)", series_limit, len(df))

        return df

    def fill_missing_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensures strict date continuity for each (store_id, item_id) series.
        Missing dates are filled with zero sales.
        """
        logger.info("Verifying date continuity across time-series...")
        groups = []
        
        for (store_id, item_id), group in df.groupby(["store_id", "item_id"]):
            group = group.sort_values("date").drop_duplicates(subset=["date"])
            min_date = group["date"].min()
            max_date = group["date"].max()
            full_date_range = pd.date_range(start=min_date, end=max_date, freq="D")

            if len(full_date_range) > len(group):
                # Reindex to full date range
                group = group.set_index("date").reindex(full_date_range)
                group.index.name = "date"
                group = group.reset_index()
                group["store_id"] = store_id
                group["item_id"] = item_id
                group["sales"] = group["sales"].fillna(0)
                # Forward fill metadata attributes
                for col in ["state_id", "category", "department", "cat_id", "dept_id", "sell_price"]:
                    if col in group.columns:
                        group[col] = group[col].ffill().bfill()
            groups.append(group)

        full_df = pd.concat(groups, ignore_index=True)
        full_df = full_df.sort_values(by=["store_id", "item_id", "date"]).reset_index(drop=True)
        return full_df

    def engineer_lightgbm_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generates lag, rolling window, calendar, and price features for LightGBM.
        Calculated per (store_id, item_id) series to prevent cross-series contamination.
        """
        logger.info("Engineering time-series lag and rolling statistics for LightGBM...")
        df = df.sort_values(by=["store_id", "item_id", "date"]).copy()

        # Date features
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["day"] = df["date"].dt.day
        df["day_of_week"] = df["date"].dt.dayofweek
        df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

        # Categorical event encoding
        for col in ["event_name_1", "event_type_1"]:
            if col in df.columns:
                df[col] = df[col].fillna("None").astype("category")

        # Lag & Rolling Features computed per series
        feature_dfs = []
        for _, group in df.groupby(["store_id", "item_id"]):
            group = group.copy()
            sales = group["sales"]

            # Lags
            group["lag_1"] = sales.shift(1)
            group["lag_7"] = sales.shift(7)
            group["lag_14"] = sales.shift(14)
            group["lag_28"] = sales.shift(28)

            # Rolling Means & Standard Deviations (shifted by 1 day to prevent data leakage!)
            shifted = sales.shift(1)
            group["rolling_mean_7"] = shifted.rolling(window=7, min_periods=1).mean()
            group["rolling_std_7"] = shifted.rolling(window=7, min_periods=1).std().fillna(0)
            group["rolling_mean_28"] = shifted.rolling(window=28, min_periods=1).mean()
            group["rolling_std_28"] = shifted.rolling(window=28, min_periods=1).std().fillna(0)

            # Price features
            if "sell_price" in group.columns:
                group["price_lag_1"] = group["sell_price"].shift(1)
                group["price_diff_1"] = group["sell_price"] - group["price_lag_1"]

            feature_dfs.append(group)

        featured_df = pd.concat(feature_dfs, ignore_index=True)
        featured_df = featured_df.sort_values(by=["store_id", "item_id", "date"]).reset_index(drop=True)
        
        # Drop initial rows with unfillable NaN lags (e.g. max lag 28)
        featured_df = featured_df.dropna(subset=["lag_28"]).reset_index(drop=True)
        return featured_df

    def split_train_test(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Performs a temporal train/validation split (no random split!).
        Validation set consists of the last `validation_days` days per series.
        """
        max_date = df["date"].max()
        cutoff_date = max_date - pd.Timedelta(days=self.validation_days)

        train_df = df[df["date"] <= cutoff_date].copy()
        val_df = df[df["date"] > cutoff_date].copy()

        logger.info("Train/Val Temporal Split Cutoff Date: %s", cutoff_date.strftime("%Y-%m-%d"))
        logger.info("Train Period: %s to %s (%d records)", 
                    train_df["date"].min().strftime("%Y-%m-%d"), 
                    train_df["date"].max().strftime("%Y-%m-%d"), len(train_df))
        logger.info("Val Period:   %s to %s (%d records)", 
                    val_df["date"].min().strftime("%Y-%m-%d"), 
                    val_df["date"].max().strftime("%Y-%m-%d"), len(val_df))

        return train_df, val_df


if __name__ == "__main__":
    preparer = ForecastingDataPreparer()
    raw_df = preparer.load_analytical_data()
    clean_df = preparer.fill_missing_dates(raw_df)
    feat_df = preparer.engineer_lightgbm_features(clean_df)
    train, val = preparer.split_train_test(feat_df)
    print("Sample Engineered Features:\n", feat_df[["date", "item_id", "store_id", "sales", "lag_1", "lag_7", "rolling_mean_7"]].head())
