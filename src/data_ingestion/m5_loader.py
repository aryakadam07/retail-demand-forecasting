"""
Retail Demand Forecasting — M5 Data Loader & Synthetic Generator
Loads raw M5 CSV dataset files into the Data Warehouse.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Optional
from src import config
from src.data_ingestion.bq_client import WarehouseClient


class M5DataLoader:
    """Manages loading and validation of M5 Forecasting Dataset."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or config.DATA_DIR
        self.client = WarehouseClient()

    def generate_synthetic_m5_data(self, num_items: int = 20, num_days: int = 100) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Generates realistic synthetic M5 data for automated testing and fast pipeline iteration."""
        print(f"[Generator] Generating synthetic M5 dataset ({num_items} items, {num_days} days)...")
        
        stores = ["CA_1", "CA_2", "TX_1", "WI_1"]
        categories = ["HOBBIES", "HOUSEHOLD", "FOODS"]
        
        # 1. Calendar Data
        date_range = pd.date_range(start="2011-01-29", periods=num_days, freq="D")
        calendar_rows = []
        events = [None, "SuperBowl", "PresidentsDay", "ValentinesDay", "Easter"]
        
        for idx, dt in enumerate(date_range, start=1):
            day_str = f"d_{idx}"
            wday = dt.dayofweek + 1  # 1-7
            month = dt.month
            year = dt.year
            event_name = events[idx % len(events)]
            event_type = "Sporting" if event_name in ["SuperBowl"] else ("Cultural" if event_name else None)
            
            calendar_rows.append({
                "date": dt.strftime("%Y-%m-%d"),
                "wm_yr_wk": 11101 + (idx // 7),
                "weekday": dt.strftime("%A"),
                "wday": wday,
                "month": month,
                "year": year,
                "d": day_str,
                "event_name_1": event_name,
                "event_type_1": event_type,
                "event_name_2": None,
                "event_type_2": None,
                "snap_CA": 1 if idx % 3 == 0 else 0,
                "snap_TX": 1 if idx % 4 == 0 else 0,
                "snap_WI": 1 if idx % 5 == 0 else 0,
            })
        calendar_df = pd.DataFrame(calendar_rows)

        # 2. Sales Train Data
        items_rows = []
        for item_idx in range(1, num_items + 1):
            cat = categories[item_idx % len(categories)]
            dept = f"{cat}_{1 + (item_idx % 2)}"
            item_id = f"{dept}_{item_idx:03d}"
            store_id = stores[item_idx % len(stores)]
            state_id = store_id.split("_")[0]
            id_str = f"{item_id}_{store_id}_validation"
            
            row = {
                "id": id_str,
                "item_id": item_id,
                "dept_id": dept,
                "cat_id": cat,
                "store_id": store_id,
                "state_id": state_id,
            }
            # Generate synthetic daily sales counts
            base_sales = np.random.poisson(lam=3 + (item_idx % 5), size=num_days)
            for d_idx in range(1, num_days + 1):
                row[f"d_{d_idx}"] = int(base_sales[d_idx - 1])
                
            items_rows.append(row)
        sales_df = pd.DataFrame(items_rows)

        # 3. Sell Prices Data
        price_rows = []
        unique_wm_weeks = calendar_df["wm_yr_wk"].unique()
        for item in sales_df["item_id"].unique():
            for store in stores:
                base_price = round(float(np.random.uniform(1.99, 14.99)), 2)
                for wk in unique_wm_weeks:
                    price_rows.append({
                        "store_id": store,
                        "item_id": item,
                        "wm_yr_wk": wk,
                        "sell_price": base_price
                    })
        prices_df = pd.DataFrame(price_rows)

        return calendar_df, sales_df, prices_df

    def load_raw_files(self) -> Dict[str, pd.DataFrame]:
        """Loads raw CSV files from data_dir. Uses synthetic generator if missing."""
        calendar_path = self.data_dir / "calendar.csv"
        sales_path = self.data_dir / "sales_train_validation.csv"
        prices_path = self.data_dir / "sell_prices.csv"

        if calendar_path.exists() and sales_path.exists() and prices_path.exists():
            print(f"[Loader] Loading official CSVs from {self.data_dir}...")
            calendar_df = pd.read_csv(calendar_path)
            sales_df = pd.read_csv(sales_path)
            prices_df = pd.read_csv(prices_path)
        else:
            print(f"[Loader] Official M5 CSVs not found in '{self.data_dir}'. Generating synthetic dataset for ingestion...")
            calendar_df, sales_df, prices_df = self.generate_synthetic_m5_data()
            
            # Save synthetic files for local persistence
            calendar_df.to_csv(calendar_path, index=False)
            sales_df.to_csv(sales_path, index=False)
            prices_df.to_csv(prices_path, index=False)
            print(f"[Loader] Saved synthetic CSV files to '{self.data_dir}'.")

        return {
            "calendar": calendar_df,
            "sales_train": sales_df,
            "sell_prices": prices_df
        }

    def ingest_to_warehouse(self) -> None:
        """Ingests raw M5 dataframes into raw warehouse tables."""
        datasets = self.load_raw_files()
        self.client.create_dataset()

        print("[Ingestion] Loading 'raw_calendar' table...")
        self.client.load_dataframe(datasets["calendar"], "raw_calendar", if_exists="replace")

        print("[Ingestion] Loading 'raw_sales_train' table...")
        self.client.load_dataframe(datasets["sales_train"], "raw_sales_train", if_exists="replace")

        print("[Ingestion] Loading 'raw_sell_prices' table...")
        self.client.load_dataframe(datasets["sell_prices"], "raw_sell_prices", if_exists="replace")

        print("[Ingestion] Complete! Raw tables stored in Data Warehouse.")


if __name__ == "__main__":
    loader = M5DataLoader()
    loader.ingest_to_warehouse()
