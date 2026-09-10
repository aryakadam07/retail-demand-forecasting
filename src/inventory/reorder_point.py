"""
Retail Demand Forecasting — Reorder Point (ROP) Calculation Engine
Computes Reorder Point = Expected Lead-Time Demand + Safety Stock.
"""

import math
import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional

logger = logging.getLogger("ReorderPoint")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class ReorderPointCalculator:
    """
    Calculates Reorder Point using formula:
    Reorder Point (ROP) = Expected Lead-Time Demand + Safety Stock
    where Expected Lead-Time Demand = Avg Daily Forecasted Demand * Lead Time (days).
    """

    def __init__(self, lead_time_days: int = 7):
        self.lead_time_days = lead_time_days

    def compute_reorder_point(
        self,
        avg_daily_forecast: float,
        safety_stock: float
    ) -> float:
        """Computes ROP for a single item-store series."""
        lead_time_demand = avg_daily_forecast * self.lead_time_days
        rop = lead_time_demand + safety_stock
        return float(np.ceil(rop))

    def compute_dataframe_rop(
        self,
        forecast_df: pd.DataFrame,
        safety_stock_df: pd.DataFrame,
        store_col: str = "store_id",
        item_col: str = "item_id",
        demand_col: str = "predicted_demand"
    ) -> pd.DataFrame:
        """
        Combines 30-day forecast demand with safety stock to compute ROP per item-store series.
        """
        # Group forecast demand per series
        summary_df = forecast_df.groupby([store_col, item_col]).agg(
            total_30d_forecast=(demand_col, "sum"),
            avg_daily_forecast=(demand_col, "mean")
        ).reset_index()

        merged = summary_df.merge(safety_stock_df, on=[store_col, item_col], how="left")
        merged["safety_stock"] = merged["safety_stock"].fillna(0)

        merged["lead_time_demand"] = (merged["avg_daily_forecast"] * self.lead_time_days).round(2)
        merged["reorder_point"] = np.ceil(merged["lead_time_demand"] + merged["safety_stock"])

        return merged


if __name__ == "__main__":
    rop_calc = ReorderPointCalculator(lead_time_days=7)
    sample_rop = rop_calc.compute_reorder_point(avg_daily_forecast=6.5, safety_stock=12.0)
    print(f"Sample Reorder Point: {sample_rop} units")
