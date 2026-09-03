"""
Retail Demand Forecasting — Week 1 Master ETL & Data Quality Pipeline
Orchestrates end-to-end execution of the entire Week 1 data pipeline:
1. Raw Data Ingestion (BigQuery / Local Warehouse)
2. Data Quality & Standardization (Calendar, Sales, Prices)
3. Wide-to-Long Sales Transformation (fact_daily_sales)
4. Analytical Data Quality & Hierarchy Validation
"""

import sys
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import config
from src.data_ingestion.bigquery_ingestion import BigQueryIngestionEngine
from src.preprocessing.run_day4_pipeline import Day4DataQualityPipeline
from src.preprocessing.run_day5_pipeline import Day5TransformationPipeline
from src.preprocessing.run_day6_pipeline import Day6ValidationPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Week1MasterPipeline")


class Week1MasterETLPipeline:
    """Master orchestrator for Week 1 Data Architecture & ETL Pipeline."""

    def __init__(self, use_local_duckdb: Optional[bool] = None):
        if use_local_duckdb is None:
            self.use_local = config.USE_LOCAL_DUCKDB
        else:
            self.use_local = use_local_duckdb

    def run_pipeline(self) -> Dict[str, Any]:
        """Runs Stage 1 through Stage 4 of Week 1 ETL consecutively."""
        start_time = time.time()
        logger.info("================================================================================")
        logger.info("          STARTING WEEK 1 MASTER ETL & DATA QUALITY PIPELINE                     ")
        logger.info("================================================================================")
        logger.info("Local Fallback Mode : %s", self.use_local)
        logger.info("Warehouse Target    : %s", config.BIGQUERY_DATASET)
        logger.info("--------------------------------------------------------------------------------")

        # Stage 1: Raw Data Ingestion
        logger.info("\n[STAGE 1/4] Executing Raw Data Ingestion Pipeline...")
        ingestion_engine = BigQueryIngestionEngine(use_local_duckdb=self.use_local)
        ingestion_results = ingestion_engine.run_full_ingestion()

        # Stage 2: Data Quality & Standardization
        logger.info("\n[STAGE 2/4] Executing Data Quality & Standardization Pipeline...")
        day4_pipeline = Day4DataQualityPipeline(use_local_duckdb=self.use_local)
        day4_results = day4_pipeline.run_pipeline()

        # Stage 3: Wide-to-Long Sales Transformation
        logger.info("\n[STAGE 3/4] Executing Wide-to-Long Sales Data Transformation Pipeline...")
        day5_pipeline = Day5TransformationPipeline(use_local_duckdb=self.use_local)
        day5_results = day5_pipeline.run_pipeline()

        # Stage 4: Analytical Data Quality & Hierarchy Validation
        logger.info("\n[STAGE 4/4] Executing Transformed Data Quality & Validation Pipeline...")
        day6_pipeline = Day6ValidationPipeline(use_local_duckdb=self.use_local)
        day6_results = day6_pipeline.run_pipeline()

        elapsed = round(time.time() - start_time, 2)
        logger.info("================================================================================")
        logger.info("          WEEK 1 MASTER ETL PIPELINE COMPLETED SUCCESSFULLY (in %.2fs)          ", elapsed)
        logger.info("          Overall Validation Status: %s | Final Fact Rows: %d",
                    day6_results["validation_metrics"].get("row_count_status"),
                    day6_results["validation_metrics"].get("row_count", 0))
        logger.info("================================================================================\n")

        return {
            "stage1_ingestion": ingestion_results,
            "stage2_quality": day4_results,
            "stage3_transform": day5_results,
            "stage4_validation": day6_results,
            "total_elapsed_seconds": elapsed,
            "status": "PASS" if day6_results["validation_metrics"].get("row_count_status") == "PASS" else "FAIL"
        }


def main():
    parser = argparse.ArgumentParser(description="Week 1 Master ETL Pipeline")
    parser.add_argument("--local", action="store_true", help="Force local warehouse execution")
    args = parser.parse_args()

    master = Week1MasterETLPipeline(use_local_duckdb=args.local if args.local else None)
    master.run_pipeline()


if __name__ == "__main__":
    main()
