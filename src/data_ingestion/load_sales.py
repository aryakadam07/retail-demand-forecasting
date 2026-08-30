"""
Retail Demand Forecasting — Sales Dataset Ingestion Module
Loads raw sales_train_validation.csv into Google BigQuery table `raw_sales_train_validation`.
"""

import sys
import time
import logging
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_ingestion import config as ingestion_config
from src.data_ingestion.bq_client import WarehouseClient
from src.data_ingestion.m5_loader import M5DataLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_sales_data(
    client: Optional[WarehouseClient] = None,
    if_exists: str = "replace"
) -> Tuple[bool, int, float]:
    """
    Loads raw sales_train_validation.csv into BigQuery table `raw_sales_train_validation`.

    Args:
        client: Optional pre-configured WarehouseClient instance.
        if_exists: 'replace' or 'append'. Defaults to 'replace' to prevent duplicates.

    Returns:
        Tuple of (success: bool, num_rows: int, elapsed_seconds: float)
    """
    start_time = time.time()
    table_name = ingestion_config.RAW_SALES_TABLE

    if client is None:
        client = WarehouseClient()

    logger.info("Starting ingestion for 'sales_train_validation.csv' into '%s'...", table_name)

    # 1. Read sales dataset safely
    sales_path = ingestion_config.SALES_TRAIN_FILE
    if sales_path.exists():
        logger.info("Reading sales train validation file from '%s'...", sales_path)
        try:
            df = pd.read_csv(sales_path, dtype=ingestion_config.SALES_BASE_DTYPES)
        except Exception as err:
            logger.warning("Typed read failed (%s), reading with default pandas inference...", err)
            df = pd.read_csv(sales_path)
    else:
        logger.info("Local 'sales_train_validation.csv' not found. Using M5 sample generator...")
        loader = M5DataLoader()
        datasets = loader.load_raw_files()
        df = datasets["sales_train"]

    logger.info("Successfully read %d rows x %d columns for sales train validation data.", len(df), len(df.columns))

    # 2. Ensure dataset exists in warehouse
    client.create_dataset()

    # 3. Load DataFrame into BigQuery / Warehouse
    try:
        success = client.load_dataframe(df, table_name, if_exists=if_exists)
        elapsed = round(time.time() - start_time, 2)
        if success:
            logger.info("SUCCESS: Loaded %d rows into '%s' in %.2fs.", len(df), table_name, elapsed)
        else:
            logger.error("FAILED: Could not load '%s'.", table_name)
        return success, len(df), elapsed
    except Exception as exc:
        logger.error("ERROR loading sales dataset: %s", exc, exc_info=True)
        return False, 0, round(time.time() - start_time, 2)


if __name__ == "__main__":
    success, rows, elapsed = load_sales_data()
    if success:
        print(f"\n[load_sales] Completed successfully: {rows:,} rows loaded in {elapsed}s.")
    else:
        print("\n[load_sales] Ingestion failed.")
        sys.exit(1)
