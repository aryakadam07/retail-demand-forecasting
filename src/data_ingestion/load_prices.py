"""
Retail Demand Forecasting — Sell Prices Dataset Ingestion Module
Loads raw sell_prices.csv into Google BigQuery table `raw_sell_prices`.
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


def load_prices_data(
    client: Optional[WarehouseClient] = None,
    if_exists: str = "replace"
) -> Tuple[bool, int, float]:
    """
    Loads raw sell_prices.csv into BigQuery table `raw_sell_prices`.

    Args:
        client: Optional pre-configured WarehouseClient instance.
        if_exists: 'replace' or 'append'. Defaults to 'replace' to prevent duplicates.

    Returns:
        Tuple of (success: bool, num_rows: int, elapsed_seconds: float)
    """
    start_time = time.time()
    table_name = ingestion_config.RAW_PRICES_TABLE

    if client is None:
        client = WarehouseClient()

    logger.info("Starting ingestion for 'sell_prices.csv' into '%s'...", table_name)

    # 1. Read sell prices dataset safely
    prices_path = ingestion_config.SELL_PRICES_FILE
    if prices_path.exists():
        logger.info("Reading sell prices file from '%s'...", prices_path)
        try:
            df = pd.read_csv(prices_path, dtype=ingestion_config.PRICES_DTYPES)
        except Exception as err:
            logger.warning("Typed read failed (%s), reading with default pandas inference...", err)
            df = pd.read_csv(prices_path)
    else:
        logger.info("Local 'sell_prices.csv' not found. Using M5 sample generator...")
        loader = M5DataLoader()
        datasets = loader.load_raw_files()
        df = datasets["sell_prices"]

    logger.info("Successfully read %d rows x %d columns for sell prices data.", len(df), len(df.columns))

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
        logger.error("ERROR loading sell prices dataset: %s", exc, exc_info=True)
        return False, 0, round(time.time() - start_time, 2)


if __name__ == "__main__":
    success, rows, elapsed = load_prices_data()
    if success:
        print(f"\n[load_prices] Completed successfully: {rows:,} rows loaded in {elapsed}s.")
    else:
        print("\n[load_prices] Ingestion failed.")
        sys.exit(1)
