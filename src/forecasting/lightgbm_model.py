"""
Retail Demand Forecasting — LightGBM Demand Forecasting Engine
Implements LightGBM gradient boosting model for retail time-series forecasting.
"""

import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import lightgbm as lgb

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("LightGBMForecaster")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DEFAULT_FEATURES = [
    "lag_1", "lag_7", "lag_14", "lag_28",
    "rolling_mean_7", "rolling_std_7", "rolling_mean_28", "rolling_std_28",
    "year", "month", "day", "day_of_week", "week_of_year", "is_weekend",
    "sell_price"
]


class LightGBMForecaster:
    """Trains LightGBM Regressor on time-series features and predicts validation & future demand."""

    def __init__(self, feature_cols: Optional[List[str]] = None, n_estimators: int = 150, learning_rate: float = 0.05):
        self.feature_cols = feature_cols or DEFAULT_FEATURES
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.model: Optional[lgb.LGBMRegressor] = None

    def train_and_predict(self, train_df: pd.DataFrame, val_df: pd.DataFrame) -> pd.DataFrame:
        """
        Trains LightGBM model on train_df and generates validation predictions for val_df.
        """
        # Ensure all feature columns exist in dataset
        avail_features = [f for f in self.feature_cols if f in train_df.columns]
        logger.info("Training LightGBM model with %d features: %s", len(avail_features), avail_features)

        X_train = train_df[avail_features]
        y_train = train_df["sales"]

        X_val = val_df[avail_features]
        y_val = val_df["sales"]

        self.model = lgb.LGBMRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            random_state=42,
            verbose=-1
        )
        self.model.fit(X_train, y_train)

        val_preds = self.model.predict(X_val)
        val_res = val_df[["date", "store_id", "item_id", "sales"]].copy()
        val_res = val_res.rename(columns={"sales": "actual"})
        val_res["predicted_demand"] = np.maximum(0, val_preds)
        val_res["model_name"] = "LightGBM"

        logger.info("LightGBM validation prediction completed for %d records.", len(val_res))
        return val_res[["date", "store_id", "item_id", "actual", "predicted_demand", "model_name"]]

    def predict_future(
        self,
        full_df: pd.DataFrame,
        horizon_days: int = 30
    ) -> pd.DataFrame:
        """
        Generates multi-step recursive future demand predictions for `horizon_days` beyond max date.
        """
        logger.info("Generating %d-day future demand forecast using LightGBM...", horizon_days)
        avail_features = [f for f in self.feature_cols if f in full_df.columns]

        if self.model is None:
            # Fit model on full dataset
            X_full = full_df[avail_features]
            y_full = full_df["sales"]
            self.model = lgb.LGBMRegressor(
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate,
                random_state=42,
                verbose=-1
            )
            self.model.fit(X_full, y_full)

        future_records = []

        for (store_id, item_id), group in full_df.groupby(["store_id", "item_id"]):
            history_series = group.sort_values("date").copy()
            max_date = history_series["date"].max()

            for step in range(1, horizon_days + 1):
                next_date = max_date + pd.Timedelta(days=step)
                
                # Compute features for next_date using past actual/predicted sales history
                past_sales = history_series["sales"].values

                lag_1 = past_sales[-1] if len(past_sales) >= 1 else 0
                lag_7 = past_sales[-7] if len(past_sales) >= 7 else lag_1
                lag_14 = past_sales[-14] if len(past_sales) >= 14 else lag_7
                lag_28 = past_sales[-28] if len(past_sales) >= 28 else lag_14

                rolling_7 = np.mean(past_sales[-7:]) if len(past_sales) >= 7 else np.mean(past_sales)
                rolling_std_7 = np.std(past_sales[-7:]) if len(past_sales) >= 7 else 0
                rolling_28 = np.mean(past_sales[-28:]) if len(past_sales) >= 28 else np.mean(past_sales)
                rolling_std_28 = np.std(past_sales[-28:]) if len(past_sales) >= 28 else 0

                sell_price = history_series["sell_price"].iloc[-1] if "sell_price" in history_series.columns else 0

                feat_dict = {
                    "lag_1": lag_1,
                    "lag_7": lag_7,
                    "lag_14": lag_14,
                    "lag_28": lag_28,
                    "rolling_mean_7": rolling_7,
                    "rolling_std_7": rolling_std_7,
                    "rolling_mean_28": rolling_28,
                    "rolling_std_28": rolling_std_28,
                    "year": next_date.year,
                    "month": next_date.month,
                    "day": next_date.day,
                    "day_of_week": next_date.dayofweek,
                    "week_of_year": next_date.isocalendar().week,
                    "is_weekend": 1 if next_date.dayofweek in [5, 6] else 0,
                    "sell_price": sell_price
                }

                feat_row = pd.DataFrame([feat_dict])[avail_features]
                pred_sales = float(np.maximum(0, self.model.predict(feat_row)[0]))

                future_records.append({
                    "forecast_date": next_date,
                    "store_id": store_id,
                    "item_id": item_id,
                    "predicted_demand": pred_sales,
                    "model_used": "LightGBM"
                })

                # Append prediction to history so subsequent lag steps use it recursively
                new_row = history_series.iloc[-1:].copy()
                new_row["date"] = next_date
                new_row["sales"] = pred_sales
                history_series = pd.concat([history_series, new_row], ignore_index=True)

        res_df = pd.DataFrame(future_records)
        return res_df


if __name__ == "__main__":
    from src.forecasting.data_preparation import ForecastingDataPreparer
    prep = ForecastingDataPreparer()
    raw = prep.load_analytical_data(series_limit=2)
    clean = prep.fill_missing_dates(raw)
    feat = prep.engineer_lightgbm_features(clean)
    train, val = prep.split_train_test(feat)

    lgb_model = LightGBMForecaster()
    val_preds = lgb_model.train_and_predict(train, val)
    print("LightGBM Validation Predictions Sample:\n", val_preds.head())
