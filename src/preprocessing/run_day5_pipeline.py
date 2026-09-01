"""
Retail Demand Forecasting — Week 1 Day 5 Data Transformation Pipeline
Orchestrates wide-to-long sales dataset transformation, date mapping, sell price joining,
target warehouse table ingestion (`fact_daily_sales`), and post-transformation data validation.
"""

import sys
import time
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import config
from src.data_ingestion.bq_client import WarehouseClient
from src.preprocessing.transform_sales import SalesTransformer, transform_sales_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Day5Pipeline")


class Day5TransformationPipeline:
    """Master pipeline for Week 1 Day 5 Data Transformation and Validation."""

    def __init__(self, use_local_duckdb: Optional[bool] = None):
        self.client = WarehouseClient(use_local_duckdb=use_local_duckdb)
        self.dataset_id = self.client.dataset_id
        self.transformer = SalesTransformer(client=self.client)

    def audit_raw_sales_total(self) -> int:
        """Calculates total sales volume across all daily columns in raw/clean wide sales table."""
        dataset = self.dataset_id
        try:
            wide_sales = self.client.query(f"SELECT * FROM {dataset}.clean_sales_train_validation")
        except Exception:
            wide_sales = self.client.query(f"SELECT * FROM {dataset}.raw_sales_train_validation")

        d_cols = [c for c in wide_sales.columns if c.startswith("d_")]
        if not d_cols:
            return 0

        # Non-negative sum
        sales_matrix = wide_sales[d_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        sales_matrix = np.clip(sales_matrix, a_min=0, a_max=None)
        return int(sales_matrix.values.sum())

    def validate_transformed_data(self, df: pd.DataFrame, raw_sales_total: int) -> Dict[str, Any]:
        """
        Executes granular validation metrics on the transformed analytical sales dataframe.
        """
        logger.info("Executing post-transformation validation checks...")

        # 1. Total records
        total_records = len(df)

        # 2. Date range
        min_date = df["date"].min() if "date" in df.columns and not df.empty else "N/A"
        max_date = df["date"].max() if "date" in df.columns and not df.empty else "N/A"

        # 3. Unique entities
        unique_items = df["item_id"].nunique() if "item_id" in df.columns else 0
        unique_stores = df["store_id"].nunique() if "store_id" in df.columns else 0
        unique_depts = df["dept_id"].nunique() if "dept_id" in df.columns else 0
        unique_cats = df["cat_id"].nunique() if "cat_id" in df.columns else 0

        # 4. Sales metrics
        total_sales = int(df["sales"].sum()) if "sales" in df.columns else 0
        neg_sales = int((df["sales"] < 0).sum()) if "sales" in df.columns else 0

        # 5. Missing values
        missing_dates = int(df["date"].isnull().sum()) if "date" in df.columns else total_records
        missing_prices = int(df["sell_price"].isnull().sum()) if "sell_price" in df.columns else total_records

        # 6. Duplicate key checks (date + item_id + store_id)
        dup_keys = 0
        if all(c in df.columns for c in ["date", "item_id", "store_id"]):
            dup_keys = int(df.duplicated(subset=["date", "item_id", "store_id"]).sum())

        # 7. Total sales conservation
        sales_match = (total_sales == raw_sales_total)

        metrics = {
            "total_records": total_records,
            "min_date": min_date,
            "max_date": max_date,
            "unique_items": unique_items,
            "unique_stores": unique_stores,
            "unique_depts": unique_depts,
            "unique_cats": unique_cats,
            "total_sales": total_sales,
            "raw_total_sales": raw_sales_total,
            "sales_match": sales_match,
            "neg_sales": neg_sales,
            "missing_dates": missing_dates,
            "missing_prices": missing_prices,
            "duplicate_keys": dup_keys
        }
        return metrics

    def generate_report_text(self, metrics: Dict[str, Any]) -> str:
        """Renders formatted text report summarizing Day 5 transformation and validation."""
        sales_match_str = "[PASS] MATCHED" if metrics["sales_match"] else f"[WARN] MISMATCH (Raw: {metrics['raw_total_sales']:,} vs Transformed: {metrics['total_sales']:,})"
        dup_str = "[PASS] 0 duplicates" if metrics["duplicate_keys"] == 0 else f"[FAIL] {metrics['duplicate_keys']:,} duplicate keys"
        neg_str = "[PASS] 0 negative sales" if metrics["neg_sales"] == 0 else f"[WARN] {metrics['neg_sales']:,} negative sales"
        dates_str = "[PASS] 0 missing dates" if metrics["missing_dates"] == 0 else f"[FAIL] {metrics['missing_dates']:,} missing dates"

        report_lines = [
            "==================================================",
            "  WEEK 1 DAY 5: SALES DATA TRANSFORMATION REPORT  ",
            "==================================================",
            f"  Target Table Name       : fact_daily_sales (alias: stg_sales_long)",
            f"  Warehouse Dataset       : {self.dataset_id}",
            f"  Warehouse Backend Engine: {self.client.engine_mode.upper()}",
            "--------------------------------------------------",
            "  TRANSFORMATION METRICS & SUMMARY:",
            f"    - Total Records Created: {metrics['total_records']:,}",
            f"    - Minimum Date         : {metrics['min_date']}",
            f"    - Maximum Date         : {metrics['max_date']}",
            f"    - Unique Products      : {metrics['unique_items']:,}",
            f"    - Unique Stores        : {metrics['unique_stores']:,}",
            f"    - Unique Departments   : {metrics['unique_depts']:,}",
            f"    - Unique Categories    : {metrics['unique_cats']:,}",
            "--------------------------------------------------",
            "  DATA INTEGRITY & VALIDATION CHECKS:",
            f"    1. Raw vs Transformed Sales Sum : {sales_match_str}",
            f"       - Raw Sales Total            : {metrics['raw_total_sales']:,}",
            f"       - Transformed Sales Total    : {metrics['total_sales']:,}",
            f"    2. Negative Sales Volumes       : {neg_str}",
            f"    3. Missing Calendar Dates       : {dates_str}",
            f"    4. Missing Sell Prices          : {metrics['missing_prices']:,} records without price",
            f"       * Note: Missing prices occur for weeks prior to product release in store.",
            f"    5. Key Uniqueness (date+item+store): {dup_str}",
            "==================================================\n"
        ]
        return "\n".join(report_lines)

    def run_pipeline(self, target_table: str = "fact_daily_sales") -> Dict[str, Any]:
        """Executes full transformation, ingestion, validation, and reporting pipeline."""
        start_time = time.time()
        logger.info("==================================================")
        logger.info("  WEEK 1 DAY 5: SALES DATA TRANSFORMATION         ")
        logger.info("==================================================")
        logger.info("Target Warehouse Table : %s", target_table)
        logger.info("Engine Backend         : %s", self.client.engine_mode.upper())
        logger.info("--------------------------------------------------")

        # Step 1: Calculate Raw Sales Volume Sum
        logger.info("[Step 1/4] Calculating raw sales volume benchmark...")
        raw_total_sales = self.audit_raw_sales_total()

        # Step 2: Transform & Load Table
        logger.info("[Step 2/4] Executing Wide-to-Long transformation & loading '%s'...", target_table)
        transformed_df, success = self.transformer.transform_and_load(table_name=target_table)

        # Step 3: Post-Transformation Validation
        logger.info("[Step 3/4] Running post-transformation validation suite...")
        metrics = self.validate_transformed_data(transformed_df, raw_total_sales)

        # Step 4: Verification & Reporting
        logger.info("[Step 4/4] Verifying table status in Data Warehouse...")
        verification = self.client.verify_table(target_table)

        report_text = self.generate_report_text(metrics)
        report_file = config.PROCESSED_DATA_DIR / "day5_transformation_report.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_text)
        logger.info("Saved Transformation Report to '%s'.", report_file)

        # Print report
        print("\n" + report_text)

        elapsed = round(time.time() - start_time, 2)
        logger.info("==================================================")
        logger.info("  DAY 5 PIPELINE EXECUTION COMPLETED (in %.2fs)   ", elapsed)
        logger.info("  Table '%s' status: %s | Rows: %d", target_table, "VERIFIED" if verification.get("exists") else "FAILED", verification.get("row_count", 0))
        logger.info("==================================================\n")

        return {
            "transformed_df": transformed_df,
            "success": success,
            "metrics": metrics,
            "verification": verification,
            "elapsed_seconds": elapsed
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Week 1 Day 5 Transformation Pipeline")
    parser.add_argument("--local", action="store_true", help="Force local warehouse fallback")
    args = parser.parse_args()

    pipeline = Day5TransformationPipeline(use_local_duckdb=args.local if args.local else None)
    pipeline.run_pipeline()


if __name__ == "__main__":
    main()
