"""
Retail Demand Forecasting — Pricing Information Standardization Module
Validates unit prices and creates `clean_sell_prices` in BigQuery.
"""

import sys
import logging
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_ingestion.bq_client import WarehouseClient

logger = logging.getLogger(__name__)


def clean_prices_data(client: Optional[WarehouseClient] = None) -> Tuple[pd.DataFrame, bool]:
    """
    Standardizes unit pricing data:
    1. Cleans string identifiers (store_id, item_id).
    2. Ensures wm_yr_wk is an integer.
    3. Validates sell_price numeric type (float) and checks for negative/zero values.
    4. Reports missing prices (does NOT invent or fake missing prices).
    5. Deduplicates exact duplicate key combinations if any exist.
    6. Uploads cleaned data into BigQuery table `clean_sell_prices`.

    Returns:
        Tuple[pd.DataFrame, bool]: Cleaned DataFrame and ingestion success status.
    """
    if client is None:
        client = WarehouseClient()

    dataset_id = client.dataset_id
    table_name = "clean_sell_prices"
    raw_table = f"{dataset_id}.raw_sell_prices"

    logger.info("Reading raw pricing data from '%s'...", raw_table)
    raw_df = client.query(f"SELECT * FROM {raw_table}")
    clean_df = raw_df.copy()

    # 1. Clean string identifiers
    for col in ["store_id", "item_id"]:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].astype(str).str.strip()

    # 2. Ensure wm_yr_wk is integer
    if "wm_yr_wk" in clean_df.columns:
        clean_df["wm_yr_wk"] = pd.to_numeric(clean_df["wm_yr_wk"], errors="coerce").fillna(0).astype(int)

    # 3. Standardize sell_price column
    if "sell_price" in clean_df.columns:
        clean_df["sell_price"] = pd.to_numeric(clean_df["sell_price"], errors="coerce")
        missing_count = int(clean_df["sell_price"].isnull().sum())
        if missing_count > 0:
            logger.warning("Found %d records with missing sell_price — leaving uninvented for downstream handling.", missing_count)

        neg_mask = clean_df["sell_price"] < 0
        if neg_mask.any():
            logger.warning("Found %d negative price records in raw data.", neg_mask.sum())

    # 4. Deduplicate keys if any exact duplicates exist
    key_cols = ["store_id", "item_id", "wm_yr_wk"]
    if all(c in clean_df.columns for c in key_cols):
        dup_cnt = int(clean_df.duplicated(subset=key_cols).sum())
        if dup_cnt > 0:
            logger.info("Removing %d duplicate store-item-week records...", dup_cnt)
            clean_df = clean_df.drop_duplicates(subset=key_cols, keep="first").reset_index(drop=True)

    # 5. Sort by store_id, item_id, wm_yr_wk
    clean_df = clean_df.sort_values(by=["store_id", "item_id", "wm_yr_wk"]).reset_index(drop=True)

    # 6. Ingest into Data Warehouse
    logger.info("Ingesting %d cleaned pricing records into '%s'...", len(clean_df), table_name)
    success = client.load_dataframe(clean_df, table_name, if_exists="replace")

    return clean_df, success


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    df, success = clean_prices_data()
    print(f"Clean Prices execution status: {success}, Rows: {len(df):,}")
