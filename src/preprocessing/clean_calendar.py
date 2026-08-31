"""
Retail Demand Forecasting — Calendar Data Standardization Module
Standardizes date fields and creates `clean_calendar` in BigQuery / Warehouse.
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


def clean_calendar_data(client: Optional[WarehouseClient] = None) -> Tuple[pd.DataFrame, bool]:
    """
    Standardizes calendar data:
    1. Formats date column to ISO standard YYYY-MM-DD.
    2. Casts numeric columns (wm_yr_wk, wday, month, year) to integer types.
    3. Cleans string fields (weekday, d, event names/types).
    4. Uploads cleaned data into BigQuery table `clean_calendar`.

    Returns:
        Tuple[pd.DataFrame, bool]: Cleaned DataFrame and ingestion success status.
    """
    if client is None:
        client = WarehouseClient()

    dataset_id = client.dataset_id
    table_name = "clean_calendar"
    raw_table = f"{dataset_id}.raw_calendar"

    logger.info("Reading raw calendar data from '%s'...", raw_table)
    raw_df = client.query(f"SELECT * FROM {raw_table}")
    clean_df = raw_df.copy()

    # 1. Standardize date column
    logger.info("Standardizing date column to ISO YYYY-MM-DD format...")
    clean_df["date"] = pd.to_datetime(clean_df["date"]).dt.strftime("%Y-%m-%d")

    # 2. Integer casting for temporal identifiers
    int_cols = ["wm_yr_wk", "wday", "month", "year", "snap_CA", "snap_TX", "snap_WI"]
    for col in int_cols:
        if col in clean_df.columns:
            clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce").fillna(0).astype(int)

    # 3. Clean string columns
    str_cols = ["weekday", "d", "event_name_1", "event_type_1", "event_name_2", "event_type_2"]
    for col in str_cols:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].astype(str).str.strip()
            null_mask = clean_df[col].isin(["nan", "None", "<NA>", ""]) | clean_df[col].isna()
            clean_df.loc[null_mask, col] = None

    # 4. Sort chronologically
    clean_df = clean_df.sort_values(by="date").reset_index(drop=True)

    # 5. Ingest into Data Warehouse
    logger.info("Ingesting %d cleaned calendar records into '%s'...", len(clean_df), table_name)
    success = client.load_dataframe(clean_df, table_name, if_exists="replace")

    return clean_df, success


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    df, success = clean_calendar_data()
    print(f"Clean Calendar execution status: {success}, Rows: {len(df):,}")
