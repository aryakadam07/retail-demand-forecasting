"""
Retail Demand Forecasting — Master Inventory Optimization Engine
Computes Safety Stock, Reorder Point, Recommended Order Quantity, and Stockout Risk.
Uploads final inventory optimization recommendations to BigQuery / DuckDB.
"""

import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_ingestion.bq_client import WarehouseClient
from src.inventory.safety_stock import SafetyStockCalculator
from src.inventory.reorder_point import ReorderPointCalculator

logger = logging.getLogger("InventoryOptimizer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class InventoryOptimizer:
    """Orchestrates safety stock, reorder points, order quantities, and stockout risk classification."""

    def __init__(
        self,
        client: Optional[WarehouseClient] = None,
        service_level: float = 0.95,
        lead_time_days: int = 7,
        initial_inventory_ratio: float = 0.5
    ):
        self.client = client or WarehouseClient()
        self.ss_calc = SafetyStockCalculator(service_level=service_level, lead_time_days=lead_time_days)
        self.rop_calc = ReorderPointCalculator(lead_time_days=lead_time_days)
        self.initial_inventory_ratio = initial_inventory_ratio

    def classify_stockout_risk(self, available_inventory: float, safety_stock: float, reorder_point: float) -> str:
        """Classifies stockout risk into HIGH, MEDIUM, or LOW."""
        if available_inventory < safety_stock:
            return "HIGH"
        elif available_inventory < reorder_point:
            return "MEDIUM"
        else:
            return "LOW"

    def run_inventory_optimization(
        self,
        forecast_df: Optional[pd.DataFrame] = None,
        historical_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Executes end-to-end inventory optimization flow and uploads results to database.
        """
        dataset = self.client.dataset_id

        # Fetch 30-day forecast if not supplied
        if forecast_df is None or forecast_df.empty:
            logger.info("Fetching 'forecast_results' table from warehouse dataset '%s'...", dataset)
            forecast_df = self.client.query(f"SELECT * FROM {dataset}.forecast_results")

        # Fetch historical sales if not supplied
        if historical_df is None or historical_df.empty:
            logger.info("Fetching 'mart_sales_forecasting' table from warehouse dataset '%s'...", dataset)
            historical_df = self.client.query(f"SELECT * FROM {dataset}.mart_sales_forecasting")

        if forecast_df.empty or historical_df.empty:
            raise ValueError("Forecast results or historical sales tables are empty.")

        # Step 1: Calculate Safety Stock per series
        logger.info("[1/4] Calculating Safety Stock (SL: %.2f, Lead Time: %dd)...",
                    self.ss_calc.service_level, self.ss_calc.lead_time_days)
        ss_df = self.ss_calc.compute_dataframe_safety_stock(historical_df)

        # Step 2: Calculate Reorder Point per series
        logger.info("[2/4] Calculating Reorder Point (ROP)...")
        inv_summary = self.rop_calc.compute_dataframe_rop(forecast_df, ss_df)

        # Step 3: Available Inventory Scenario & Recommended Order Quantity
        logger.info("[3/4] Estimating Available Inventory & Recommended Order Quantity (ROQ)...")
        
        # Note: M5 does not track live inventory; available_inventory is calculated based on configurable initial_inventory_ratio of ROP
        inv_summary["available_inventory"] = np.ceil(inv_summary["reorder_point"] * self.initial_inventory_ratio)

        # ROQ = max(0, total_30d_forecast + safety_stock - available_inventory)
        inv_summary["recommended_order_quantity"] = np.maximum(
            0,
            np.ceil(inv_summary["total_30d_forecast"] + inv_summary["safety_stock"] - inv_summary["available_inventory"])
        )

        # Step 4: Classify Stockout Risk
        logger.info("[4/4] Classifying Stockout Risk (HIGH / MEDIUM / LOW)...")
        risk_labels = []
        for _, row in inv_summary.iterrows():
            risk = self.classify_stockout_risk(row["available_inventory"], row["safety_stock"], row["reorder_point"])
            risk_labels.append(risk)
        inv_summary["stockout_risk"] = risk_labels

        # Format final output schema
        model_used = forecast_df["model_used"].iloc[0] if "model_used" in forecast_df.columns else "Best Model"
        max_forecast_date = pd.to_datetime(forecast_df["forecast_date"]).max()

        inv_summary["forecast_date"] = max_forecast_date
        inv_summary["predicted_demand"] = inv_summary["total_30d_forecast"].round(2)
        inv_summary["model_used"] = model_used

        final_cols = [
            "item_id", "store_id", "forecast_date", "predicted_demand",
            "safety_stock", "reorder_point", "available_inventory",
            "recommended_order_quantity", "stockout_risk", "model_used"
        ]
        out_df = inv_summary[final_cols].copy()

        # Step 5: Save to Warehouse
        table_name = "inventory_recommendations"
        logger.info("Persisting final recommendations into '%s.%s'...", dataset, table_name)
        self.client.load_dataframe(out_df, table_name, if_exists="replace")

        logger.info("Inventory optimization complete for %d item-store series.", len(out_df))
        return out_df


if __name__ == "__main__":
    optimizer = InventoryOptimizer()
    rec_df = optimizer.run_inventory_optimization()
    print("Inventory Recommendations Sample:\n", rec_df.head())
