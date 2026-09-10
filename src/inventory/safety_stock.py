"""
Retail Demand Forecasting — Safety Stock Calculation Engine
Computes safety stock based on demand variability, lead time, and service level targets.
"""

import math
import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional

logger = logging.getLogger("SafetyStock")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Z-score mapping for standard service levels
SERVICE_LEVEL_Z_SCORES = {
    0.80: 0.84,
    0.85: 1.04,
    0.90: 1.28,
    0.95: 1.65,
    0.98: 2.05,
    0.99: 2.33,
}


class SafetyStockCalculator:
    """
    Calculates safety stock using formula:
    Safety Stock = Z * sigma_d * sqrt(L)

    Assumptions:
    - Service Level (Z): Target probability of not stocking out during lead time (default: 95%, Z = 1.65).
    - Demand Variability (sigma_d): Standard deviation of daily sales for each item-store combination.
    - Lead Time (L): Order fulfillment lead time in days (default: 7 days).
    """

    def __init__(self, service_level: float = 0.95, lead_time_days: int = 7):
        self.service_level = service_level
        self.lead_time_days = lead_time_days
        self.z_score = SERVICE_LEVEL_Z_SCORES.get(service_level, 1.65)

    def compute_series_safety_stock(self, historical_sales: pd.Series) -> float:
        """Computes safety stock for a single series given historical daily demand."""
        std_d = float(historical_sales.std()) if len(historical_sales) > 1 else 0.0
        if math.isnan(std_d):
            std_d = 0.0
        safety_stock = self.z_score * std_d * math.sqrt(self.lead_time_days)
        return float(np.ceil(safety_stock))

    def compute_dataframe_safety_stock(
        self,
        historical_df: pd.DataFrame,
        store_col: str = "store_id",
        item_col: str = "item_id",
        sales_col: str = "sales"
    ) -> pd.DataFrame:
        """
        Computes safety stock per (store_id, item_id) series across a dataframe.
        """
        records = []
        for (store_id, item_id), group in historical_df.groupby([store_col, item_col]):
            ss = self.compute_series_safety_stock(group[sales_col])
            mean_demand = float(group[sales_col].mean())
            std_demand = float(group[sales_col].std())
            
            records.append({
                store_col: store_id,
                item_col: item_id,
                "historical_mean_daily_sales": round(mean_demand, 2),
                "historical_std_daily_sales": round(std_demand, 2),
                "service_level_target": self.service_level,
                "lead_time_days": self.lead_time_days,
                "z_score": self.z_score,
                "safety_stock": ss
            })

        return pd.DataFrame(records)


if __name__ == "__main__":
    calc = SafetyStockCalculator(service_level=0.95, lead_time_days=7)
    sample_sales = pd.Series([5, 8, 4, 10, 6, 7, 9, 3, 5, 8])
    ss = calc.compute_series_safety_stock(sample_sales)
    print(f"Sample Safety Stock (95% SL, 7-day lead time): {ss} units")
