"""
Retail Demand Forecasting — Week 1 Day 4 Data Quality & Standardization Pipeline
Orchestrates raw dataset quality auditing, report generation, and clean BigQuery table creation.
"""

import sys
import time
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import config
from src.data_ingestion.bq_client import WarehouseClient
from src.preprocessing.data_quality import DataQualityChecker, DataQualityReport
from src.preprocessing.clean_calendar import clean_calendar_data
from src.preprocessing.clean_sales import clean_sales_data
from src.preprocessing.clean_prices import clean_prices_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Day4Pipeline")


class Day4DataQualityPipeline:
    """Master pipeline for Week 1 Day 4 Data Quality and Standardization."""

    def __init__(self, use_local_duckdb: Optional[bool] = None):
        self.client = WarehouseClient(use_local_duckdb=use_local_duckdb)
        self.dataset_id = self.client.dataset_id

    def run_pipeline(self) -> Dict[str, Any]:
        """Executes full data quality audit, report generation, and clean table creation."""
        start_time = time.time()
        logger.info("==================================================")
        logger.info("  WEEK 1 DAY 4: DATA QUALITY & STANDARDIZATION    ")
        logger.info("==================================================")
        logger.info("Target Warehouse Dataset : %s", self.dataset_id)
        logger.info("Engine Backend           : %s", self.client.engine_mode.upper())
        logger.info("--------------------------------------------------")

        # Step 1: Fetch raw tables from warehouse
        logger.info("[Step 1/4] Querying raw tables from Data Warehouse...")
        raw_calendar = self.client.query(f"SELECT * FROM {self.dataset_id}.raw_calendar")
        raw_sales = self.client.query(f"SELECT * FROM {self.dataset_id}.raw_sales_train_validation")
        raw_prices = self.client.query(f"SELECT * FROM {self.dataset_id}.raw_sell_prices")

        # Step 2: Perform Data Quality Audits
        logger.info("[Step 2/4] Executing Data Quality Audits...")
        cal_report = DataQualityChecker.audit_calendar_data(raw_calendar)
        sales_report = DataQualityChecker.audit_sales_data(raw_sales)
        prices_report = DataQualityChecker.audit_prices_data(raw_prices)

        # Render combined report string
        combined_report = "\n".join([
            cal_report.generate_text_report(),
            sales_report.generate_text_report(),
            prices_report.generate_text_report()
        ])

        # Save Data Quality Report to text file
        report_file = config.PROCESSED_DATA_DIR / "data_quality_report.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(combined_report)
        logger.info("Saved Data Quality Report to '%s'.", report_file)

        # Print report to stdout
        print("\n" + combined_report)

        # Step 3: Run Data Standardization & Ingest Clean Tables
        logger.info("[Step 3/4] Standardizing datasets & populating clean BigQuery tables...")
        clean_cal_df, cal_success = clean_calendar_data(client=self.client)
        clean_sales_df, sales_success = clean_sales_data(client=self.client)
        clean_prices_df, prices_success = clean_prices_data(client=self.client)

        # Step 4: Verify Clean Tables
        logger.info("[Step 4/4] Verifying clean BigQuery tables...")
        verification = {
            "clean_calendar": self.client.verify_table("clean_calendar"),
            "clean_sales_train_validation": self.client.verify_table("clean_sales_train_validation"),
            "clean_sell_prices": self.client.verify_table("clean_sell_prices")
        }

        elapsed = round(time.time() - start_time, 2)
        logger.info("==================================================")
        logger.info("  DAY 4 PIPELINE EXECUTION COMPLETED (in %.2fs)   ", elapsed)
        logger.info("==================================================")
        for tbl_name, v_info in verification.items():
            status = "VERIFIED" if v_info.get("exists") else "FAILED"
            r_cnt = v_info.get("row_count", 0)
            logger.info(" Table: %-30s | Status: %-8s | Rows: %10d", tbl_name, status, r_cnt)
        logger.info("==================================================\n")

        return {
            "calendar_report": cal_report,
            "sales_report": sales_report,
            "prices_report": prices_report,
            "verification": verification,
            "elapsed_seconds": elapsed
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Day 4 Data Quality & Standardization Pipeline")
    parser.add_argument("--local", action="store_true", help="Force local warehouse fallback")
    args = parser.parse_args()

    pipeline = Day4DataQualityPipeline(use_local_duckdb=args.local if args.local else None)
    pipeline.run_pipeline()


if __name__ == "__main__":
    main()
