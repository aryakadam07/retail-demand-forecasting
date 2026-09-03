"""
Retail Demand Forecasting — Week 1 Day 6 Validation Pipeline Runner
Orchestrates validation checks, hierarchy verification, sales analysis, temporal coverage analysis,
price statistics verification, and generates the final Week 1 Data Quality & Validation Report.
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
from src.preprocessing.validate_transformed import SalesDataValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Day6Pipeline")


class Day6ValidationPipeline:
    """Master Pipeline for Week 1 Day 6 Data Validation & Reporting."""

    def __init__(self, use_local_duckdb: Optional[bool] = None):
        self.client = WarehouseClient(use_local_duckdb=use_local_duckdb)
        self.dataset_id = self.client.dataset_id
        self.validator = SalesDataValidator(client=self.client)

    def fetch_fact_daily_sales(self) -> pd.DataFrame:
        """Fetches fact_daily_sales from warehouse, with local processed file fallback."""
        dataset = self.dataset_id
        try:
            logger.info("Querying 'fact_daily_sales' table from dataset '%s'...", dataset)
            df = self.client.query(f"SELECT * FROM {dataset}.fact_daily_sales")
            if not df.empty:
                return df
        except Exception as exc:
            logger.warning("Could not fetch table from warehouse (%s). Trying local file fallback...", exc)

        parquet_path = config.PROCESSED_DATA_DIR / "fact_daily_sales.parquet"
        csv_path = config.PROCESSED_DATA_DIR / "fact_daily_sales.csv"

        if parquet_path.exists():
            logger.info("Loading local parquet snapshot from '%s'...", parquet_path)
            return pd.read_parquet(parquet_path)
        elif csv_path.exists():
            logger.info("Loading local CSV snapshot from '%s'...", csv_path)
            return pd.read_csv(csv_path)
        else:
            raise FileNotFoundError("No fact_daily_sales dataset found in warehouse or local storage.")

    def audit_raw_sales_benchmark(self) -> Optional[int]:
        """Queries total sum of sales from raw/clean wide table for comparison."""
        dataset = self.dataset_id
        try:
            wide_sales = self.client.query(f"SELECT * FROM {dataset}.clean_sales_train_validation")
        except Exception:
            try:
                wide_sales = self.client.query(f"SELECT * FROM {dataset}.raw_sales_train_validation")
            except Exception:
                return None

        d_cols = [c for c in wide_sales.columns if c.startswith("d_")]
        if not d_cols:
            return None
        sales_matrix = wide_sales[d_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        sales_matrix = sales_matrix.clip(lower=0)
        return int(sales_matrix.values.sum())

    def run_pipeline(self) -> Dict[str, Any]:
        """Executes complete Day 6 validation pipeline and generates reports."""
        start_time = time.time()
        logger.info("==================================================")
        logger.info("  WEEK 1 DAY 6: TRANSFORMED SALES DATA VALIDATION ")
        logger.info("==================================================")
        logger.info("Warehouse Dataset : %s", self.dataset_id)
        logger.info("Engine Backend    : %s", self.client.engine_mode.upper())
        logger.info("--------------------------------------------------")

        # Step 1: Fetch Transformed Sales Data
        logger.info("[Step 1/5] Fetching transformed sales data ('fact_daily_sales')...")
        df = self.fetch_fact_daily_sales()

        # Step 2: Fetch Benchmark Raw Sales Total
        logger.info("[Step 2/5] Fetching raw sales benchmark total...")
        raw_total_sales = self.audit_raw_sales_benchmark()

        # Step 3: Execute Data Quality & Integrity Validation
        logger.info("[Step 3/5] Executing fact_daily_sales integrity & hierarchy checks...")
        val_metrics = self.validator.validate_fact_daily_sales(df)
        hierarchy_metrics = self.validator.verify_m5_hierarchy(df)
        sales_metrics = self.validator.perform_sales_analysis(df)
        temporal_metrics = self.validator.check_temporal_coverage(df)
        price_metrics = self.validator.validate_price_information(df)

        # Step 4: Render & Save Final Validation Report
        logger.info("[Step 4/5] Generating Week 1 Final Validation Report...")
        report_text = self.validator.generate_validation_report(df, raw_sales_total=raw_total_sales)

        report_file_txt = config.PROCESSED_DATA_DIR / "week1_validation_report.txt"
        with open(report_file_txt, "w", encoding="utf-8") as f:
            f.write(report_text)
        logger.info("Saved validation report to '%s'.", report_file_txt)

        # Step 5: Output Report Summary to Console
        logger.info("[Step 5/5] Console Output of Week 1 Report:")
        print("\n" + report_text)

        elapsed = round(time.time() - start_time, 2)
        logger.info("==================================================")
        logger.info("  DAY 6 PIPELINE EXECUTION COMPLETED (in %.2fs)   ", elapsed)
        logger.info("  Validation Status: %s | Rows Validated: %d", val_metrics.get("row_count_status"), len(df))
        logger.info("==================================================\n")

        return {
            "df": df,
            "validation_metrics": val_metrics,
            "hierarchy_metrics": hierarchy_metrics,
            "sales_metrics": sales_metrics,
            "temporal_metrics": temporal_metrics,
            "price_metrics": price_metrics,
            "report_text": report_text,
            "elapsed_seconds": elapsed
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Week 1 Day 6 Validation Pipeline")
    parser.add_argument("--local", action="store_true", help="Force local warehouse fallback")
    args = parser.parse_args()

    pipeline = Day6ValidationPipeline(use_local_duckdb=args.local if args.local else None)
    pipeline.run_pipeline()


if __name__ == "__main__":
    main()
