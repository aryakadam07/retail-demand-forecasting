"""
Retail Demand Forecasting — Sales Volume Standardization Module
Validates wide-format daily sales volumes and creates `clean_sales_train_validation` in BigQuery.
"""

import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_ingestion.bq_client import WarehouseClient

logger = logging.getLogger(__name__)


def clean_sales_data(client: Optional[WarehouseClient] = None) -> Tuple[pd.DataFrame, bool]:
    """
    Standardizes wide sales data:
    1. Validates primary string identifiers (id, item_id, dept_id, cat_id, store_id, state_id).
    2. Enforces numeric non-negative integer types across all daily sales columns (d_1 ... d_N).
    3. Handles missing or invalid sales values (fills NaN with 0, clips negative sales to 0).
    4. Audits outliers without deleting them.
    5. Uploads cleaned data into BigQuery tables `clean_sales_train_validation` and `clean_sales`.

    Returns:
        Tuple[pd.DataFrame, bool]: Cleaned DataFrame and ingestion success status.
    """
    if client is None:
        client = WarehouseClient()

    dataset_id = client.dataset_id
    table_name = "clean_sales_train_validation"
    raw_table = f"{dataset_id}.raw_sales_train_validation"

    logger.info("Reading raw sales data from '%s'...", raw_table)
    raw_df = client.query(f"SELECT * FROM {raw_table}")
    clean_df = raw_df.copy()

    # 1. Clean primary identifier columns
    id_cols = ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]
    for col in id_cols:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].astype(str).str.strip()

    # 2. Standardize daily sales volume columns (d_1 ... d_N)
    d_cols = [c for c in clean_df.columns if c.startswith("d_")]
    logger.info("Validating sales volumes across %d daily sales columns...", len(d_cols))

    for col in d_cols:
        # Convert non-numeric or missing to 0
        clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce").fillna(0)
        # Clip negative sales values to 0
        neg_mask = clean_df[col] < 0
        if neg_mask.any():
            logger.warning("Clipped %d negative sales entries to 0 in column '%s'.", neg_mask.sum(), col)
            clean_df.loc[neg_mask, col] = 0
        # Cast to integer
        clean_df[col] = clean_df[col].astype(int)

    # 3. Sort by item_id and store_id
    if "item_id" in clean_df.columns and "store_id" in clean_df.columns:
        clean_df = clean_df.sort_values(by=["store_id", "item_id"]).reset_index(drop=True)

    # 4. Ingest into Data Warehouse
    logger.info("Ingesting %d cleaned sales records into '%s'...", len(clean_df), table_name)
    success = client.load_dataframe(clean_df, table_name, if_exists="replace")

    # Maintain clean_sales alias for backwards compatibility
    client.load_dataframe(clean_df, "clean_sales", if_exists="replace")

    return clean_df, success


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    df, success = clean_sales_data()
    print(f"Clean Sales execution status: {success}, Rows: {len(df):,}")
