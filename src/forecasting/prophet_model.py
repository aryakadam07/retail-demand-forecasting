"""
Retail Demand Forecasting — Prophet Demand Forecasting Engine
Implements Prophet model per time-series for retail demand prediction.
"""

import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from prophet import Prophet

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("ProphetForecaster")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class ProphetForecaster:
    """Trains Prophet models across item-store time series and outputs validation predictions."""

    def __init__(self, weekly_seasonality: bool = True, yearly_seasonality: bool = False):
        self.weekly_seasonality = weekly_seasonality
        self.yearly_seasonality = yearly_seasonality
        self.models: Dict[Tuple[str, str], Prophet] = {}

    def fit_predict_series(
        self,
        train_series: pd.DataFrame,
        val_series: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Fits a Prophet model on a single (store_id, item_id) series training data
        and generates predictions for the validation period.
        """
        store_id = train_series["store_id"].iloc[0]
        item_id = train_series["item_id"].iloc[0]

        # Prepare Prophet format
        df_prophet = train_series[["date", "sales"]].rename(columns={"date": "ds", "sales": "y"})

        # Initialize Prophet with suppressed logs
        model = Prophet(
            weekly_seasonality=self.weekly_seasonality,
            yearly_seasonality=self.yearly_seasonality,
            daily_seasonality=False,
            interval_width=0.95
        )
        
        # Suppress cmdstanpy / prophet logs
        logging.getLogger("prophet").setLevel(logging.ERROR)
        logging.getLogger("cmdstanpy").setLevel(logging.ERROR)

        model.fit(df_prophet)
        self.models[(store_id, item_id)] = model

        # Predict for validation dates
        future = val_series[["date"]].rename(columns={"date": "ds"})
        forecast = model.predict(future)

        # Merge validation actuals with predictions
        val_res = val_series[["date", "store_id", "item_id", "sales"]].copy()
        val_res["date"] = pd.to_datetime(val_res["date"])
        forecast["ds"] = pd.to_datetime(forecast["ds"])

        merged = val_res.merge(forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]], left_on="date", right_on="ds", how="left")
        merged = merged.rename(columns={"sales": "actual", "yhat": "predicted_demand"})
        
        # Ensure non-negative predictions
        merged["predicted_demand"] = np.maximum(0, merged["predicted_demand"])
        merged["model_name"] = "Prophet"

        return merged[["date", "store_id", "item_id", "actual", "predicted_demand", "model_name"]]

    def predict_all(self, train_df: pd.DataFrame, val_df: pd.DataFrame) -> pd.DataFrame:
        """
        Executes Prophet training and validation across all (store_id, item_id) series.
        """
        logger.info("Training Prophet models across all series...")
        results = []

        for (store_id, item_id), train_group in train_df.groupby(["store_id", "item_id"]):
            val_group = val_df[(val_df["store_id"] == store_id) & (val_df["item_id"] == item_id)]
            if val_group.empty:
                continue

            try:
                res = self.fit_predict_series(train_group, val_group)
                results.append(res)
            except Exception as exc:
                logger.warning("Prophet failed for (%s, %s): %s", store_id, item_id, exc)

        if not results:
            return pd.DataFrame()

        all_res = pd.concat(results, ignore_index=True)
        logger.info("Generated Prophet validation predictions for %d total records across %d series.",
                    len(all_res), len(results))
        return all_res

    def predict_future(
        self,
        full_df: pd.DataFrame,
        horizon_days: int = 30
    ) -> pd.DataFrame:
        """
        Fits Prophet on full historical data and generates a future `horizon_days` forecast.
        """
        logger.info("Generating %d-day future demand forecast using Prophet...", horizon_days)
        future_forecasts = []

        for (store_id, item_id), group in full_df.groupby(["store_id", "item_id"]):
            df_prophet = group[["date", "sales"]].rename(columns={"date": "ds", "sales": "y"})
            
            model = Prophet(
                weekly_seasonality=self.weekly_seasonality,
                yearly_seasonality=self.yearly_seasonality,
                daily_seasonality=False
            )
            logging.getLogger("prophet").setLevel(logging.ERROR)
            model.fit(df_prophet)

            max_date = group["date"].max()
            future_dates = pd.date_range(start=max_date + pd.Timedelta(days=1), periods=horizon_days, freq="D")
            future_df = pd.DataFrame({"ds": future_dates})

            fcst = model.predict(future_df)
            fcst["store_id"] = store_id
            fcst["item_id"] = item_id
            fcst["forecast_date"] = fcst["ds"].dt.date
            fcst["predicted_demand"] = np.maximum(0, fcst["yhat"])
            fcst["model_used"] = "Prophet"

            future_forecasts.append(fcst[["forecast_date", "item_id", "store_id", "predicted_demand", "model_used"]])

        if not future_forecasts:
            return pd.DataFrame()

        res_df = pd.concat(future_forecasts, ignore_index=True)
        res_df["forecast_date"] = pd.to_datetime(res_df["forecast_date"])
        return res_df


if __name__ == "__main__":
    from src.forecasting.data_preparation import ForecastingDataPreparer
    prep = ForecastingDataPreparer()
    raw = prep.load_analytical_data(series_limit=2)
    clean = prep.fill_missing_dates(raw)
    feat = prep.engineer_lightgbm_features(clean)
    train, val = prep.split_train_test(feat)

    p = ProphetForecaster()
    val_preds = p.predict_all(train, val)
    print("Prophet Validation Predictions Sample:\n", val_preds.head())
