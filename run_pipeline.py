"""
Retail Demand Forecasting & Inventory Optimization — Master End-to-End Execution Pipeline
Orchestrates raw data ingestion, data quality audits, dbt transformations, Prophet & LightGBM demand forecasting,
validation metric evaluation, 30-day forecast generation, and inventory replenishment optimization.
"""

import sys
import os
import time
import argparse
import subprocess
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import config
from src.data_ingestion.bq_client import WarehouseClient
from src.preprocessing.run_day6_pipeline import Day6ValidationPipeline
from src.forecasting.forecasting_pipeline import ForecastingPipeline
from src.inventory.inventory_optimizer import InventoryOptimizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MasterPipeline")


def run_dbt_build(use_local: bool) -> bool:
    """Executes dbt build to compile models and execute database tests."""
    target = "local" if use_local else "dev"
    logger.info("==================================================")
    logger.info("       RUNNING DBT TRANSFORMATION & TESTS          ")
    logger.info("==================================================")
    logger.info("dbt Target Profile: %s", target)
    
    cmd = [
        "dbt", "build",
        "--project-dir", "dbt",
        "--profiles-dir", "dbt",
        "--target", target
    ]
    
    try:
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True, capture_output=True, text=True)
        logger.info("dbt build completed successfully.")
        return True
    except subprocess.CalledProcessError as exc:
        logger.error("dbt build failed: %s", exc.stderr)
        return False


def run_master_pipeline(series_limit: int = 10, use_local: bool = True):
    """Executes complete end-to-end architecture pipeline."""
    start_time = time.time()
    logger.info("==================================================")
    logger.info("  RETAIL DEMAND FORECASTING & INVENTORY PIPELINE  ")
    logger.info("==================================================")
    
    client = WarehouseClient(use_local_duckdb=use_local)
    logger.info("Warehouse Mode : %s", client.engine_mode.upper())
    logger.info("Dataset Name   : %s", client.dataset_id)
    logger.info("--------------------------------------------------")

    # STAGE 1: Data Quality & Preprocessing Verification
    logger.info("\n[STAGE 1/4] Data Quality Verification...")
    day6_pipe = Day6ValidationPipeline(use_local_duckdb=use_local)
    day6_res = day6_pipe.run_pipeline()

    # STAGE 2: dbt Modeling & Materialization
    logger.info("\n[STAGE 2/4] Executing dbt models & tests...")
    dbt_success = run_dbt_build(use_local=use_local)
    if not dbt_success:
        logger.warning("dbt step reported errors. Continuing with warehouse fallback tables...")

    # STAGE 3: Prophet + LightGBM Forecasting & Model Selection
    logger.info("\n[STAGE 3/4] Demand Forecasting Engine...")
    forecast_pipe = ForecastingPipeline(client=client, series_limit=series_limit)
    forecast_res = forecast_pipe.run_forecasting_pipeline(horizon_days=30)

    # STAGE 4: Inventory Replenishment Optimization
    logger.info("\n[STAGE 4/4] Inventory Replenishment Optimization...")
    inventory_opt = InventoryOptimizer(client=client, service_level=0.95, lead_time_days=7)
    inventory_res = inventory_opt.run_inventory_optimization()

    elapsed = round(time.time() - start_time, 2)
    logger.info("==================================================")
    logger.info("  PIPELINE EXECUTION COMPLETED IN %.2f SECONDS     ", elapsed)
    logger.info("==================================================")
    logger.info("Winning Forecast Model   : %s", forecast_res["winning_model"])
    logger.info("30-Day Forecast Records  : %d", len(forecast_res["forecast_df"]))
    logger.info("Inventory Series Audited : %d", len(inventory_res))
    logger.info("--------------------------------------------------")
    logger.info("To launch the Streamlit Executive Dashboard, run:")
    logger.info("  streamlit run dashboard/app.py\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Master Retail Demand Forecasting Pipeline")
    parser.add_argument("--series-limit", type=int, default=10, help="Number of item-store series to forecast (default: 10)")
    parser.add_argument("--local", action="store_true", default=True, help="Use local DuckDB database")
    args = parser.parse_args()

    run_master_pipeline(series_limit=args.series_limit, use_local=args.local)
