"""
Retail Demand Forecasting — Google BigQuery Raw Data Ingestion Engine
Orchestrates loading of raw M5 datasets into Google BigQuery warehouse tables.
"""

import sys
import time
import argparse
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import config
from src.data_ingestion import config as ingestion_config
from src.data_ingestion.bq_client import WarehouseClient
from src.data_ingestion.load_calendar import load_calendar_data
from src.data_ingestion.load_sales import load_sales_data
from src.data_ingestion.load_prices import load_prices_data


class BigQueryIngestionEngine:
    """Manages secure and robust ingestion of raw M5 datasets into Google BigQuery."""

    def __init__(self, use_local_duckdb: Optional[bool] = None):
        self.client = WarehouseClient(use_local_duckdb=use_local_duckdb)
        self.project_id = self.client.project_id
        self.dataset_id = self.client.dataset_id

    def check_prerequisites(self) -> bool:
        """Verifies dataset files and configuration before starting ingestion."""
        print("==================================================")
        print("    BIGQUERY M5 RAW DATA INGESTION ENGINE        ")
        print("==================================================")
        print(f"Target Project ID : {self.project_id}")
        print(f"Target Dataset ID : {self.dataset_id}")
        print(f"Engine Mode       : {self.client.engine_mode.upper()}")
        print("--------------------------------------------------")

        files_found = {
            "calendar.csv": config.CALENDAR_FILE.exists(),
            "sales_train_validation.csv": config.SALES_TRAIN_FILE.exists(),
            "sell_prices.csv": config.SELL_PRICES_FILE.exists()
        }

        for file_name, exists in files_found.items():
            status = "FOUND" if exists else "NOT FOUND (Will use synthetic sample generator)"
            print(f"  [{file_name}] : {status}")

        print("--------------------------------------------------")
        return True

    def ingest_table(self, df: pd.DataFrame, table_name: str) -> Tuple[bool, int, float]:
        """Loads a single DataFrame into BigQuery/Warehouse and measures latency."""
        start_time = time.time()
        print(f"\n[Ingestion] Ingesting '{table_name}' ({len(df):,} rows x {len(df.columns)} cols)...")
        success = self.client.load_dataframe(df, table_name, if_exists="replace")
        elapsed = round(time.time() - start_time, 2)
        return success, len(df), elapsed

    def run_full_ingestion(self) -> Dict[str, dict]:
        """Runs end-to-end ingestion for calendar, sales_train_validation, and sell_prices."""
        self.check_prerequisites()

        print(f"[Dataset Setup] Initializing BigQuery dataset '{self.dataset_id}'...")
        self.client.create_dataset()

        summary = {}

        # 1. Ingest Calendar
        cal_success, cal_rows, cal_time = load_calendar_data(client=self.client)
        summary["raw_calendar"] = {"success": cal_success, "rows": cal_rows, "elapsed_sec": cal_time}

        # 2. Ingest Sales Train Validation
        sales_success, sales_rows, sales_time = load_sales_data(client=self.client)
        summary["raw_sales_train_validation"] = {"success": sales_success, "rows": sales_rows, "elapsed_sec": sales_time}
        # Keep alias for raw_sales_train backwards compatibility
        self.client.load_dataframe(
            pd.read_csv(config.SALES_TRAIN_FILE) if config.SALES_TRAIN_FILE.exists() else pd.DataFrame(),
            "raw_sales_train",
            if_exists="replace"
        )
        summary["raw_sales_train"] = {"success": sales_success, "rows": sales_rows, "elapsed_sec": sales_time}

        # 3. Ingest Sell Prices
        price_success, price_rows, price_time = load_prices_data(client=self.client)
        summary["raw_sell_prices"] = {"success": price_success, "rows": price_rows, "elapsed_sec": price_time}

        self.verify_ingestion_summary(summary)
        return summary

    def verify_ingestion_summary(self, summary: Dict[str, dict]) -> None:
        """Verifies row counts and prints execution summary."""
        print("\n==================================================")
        print("          INGESTION VERIFICATION REPORT           ")
        print("==================================================")

        all_passed = True
        total_rows = 0
        total_time = 0.0

        for table, stats in summary.items():
            if table == "raw_sales_train":  # skip alias in summary metrics
                continue
            status = "PASSED" if stats["success"] else "FAILED"
            if not stats["success"]:
                all_passed = False
            total_rows += stats["rows"]
            total_time += stats["elapsed_sec"]
            print(f" Table: {table:<27} | Status: {status:<6} | Rows: {stats['rows']:>10,} | Time: {stats['elapsed_sec']}s")

        print("--------------------------------------------------")
        print(f" Total Rows Ingested : {total_rows:,}")
        print(f" Total Ingestion Time: {round(total_time, 2)}s")
        print(f" Overall Status      : {'SUCCESS' if all_passed else 'FAILURE'}")
        print("==================================================\n")

    def print_verification_queries(self) -> None:
        """Prints SQL verification queries for BigQuery Console."""
        print("--- Verification SQL Queries for BigQuery ---")
        print(f"SELECT 'raw_calendar' AS tbl, COUNT(*) AS cnt FROM `{self.dataset_id}.raw_calendar` UNION ALL")
        print(f"SELECT 'raw_sales_train_validation' AS tbl, COUNT(*) AS cnt FROM `{self.dataset_id}.raw_sales_train_validation` UNION ALL")
        print(f"SELECT 'raw_sell_prices' AS tbl, COUNT(*) AS cnt FROM `{self.dataset_id}.raw_sell_prices`;")


def main():
    parser = argparse.ArgumentParser(description="M5 BigQuery Raw Data Ingestion Engine")
    parser.add_argument("--local", action="store_true", help="Force local warehouse fallback execution")
    args = parser.parse_args()

    engine = BigQueryIngestionEngine(use_local_duckdb=args.local if args.local else None)
    summary = engine.run_full_ingestion()
    engine.print_verification_queries()


if __name__ == "__main__":
    main()
