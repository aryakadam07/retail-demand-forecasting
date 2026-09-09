"""
Retail Demand Forecasting — Master Forecasting Pipeline Runner
Orchestrates data preparation, model training (Prophet & LightGBM), metric evaluation, best model selection, and future 30-day demand forecast generation.
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
from src.forecasting.data_preparation import ForecastingDataPreparer
from src.forecasting.prophet_model import ProphetForecaster
from src.forecasting.lightgbm_model import LightGBMForecaster
from src.forecasting.evaluation import ModelEvaluator

logger = logging.getLogger("ForecastingPipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class ForecastingPipeline:
    """Master Orchestrator for the Demand Forecasting Stage."""

    def __init__(self, client: Optional[WarehouseClient] = None, series_limit: Optional[int] = None):
        self.client = client or WarehouseClient()
        self.series_limit = series_limit
        self.preparer = ForecastingDataPreparer(client=self.client)
        self.evaluator = ModelEvaluator(client=self.client)

    def run_forecasting_pipeline(self, horizon_days: int = 30) -> Dict[str, Any]:
        """
        Executes end-to-end forecasting workflow and uploads 30-day forecast to warehouse.
        """
        logger.info("==================================================")
        logger.info("       DEMAND FORECASTING & MODEL SELECTION       ")
        logger.info("==================================================")

        # Step 1: Load and Prepare Data
        raw_df = self.preparer.load_analytical_data(series_limit=self.series_limit)
        clean_df = self.preparer.fill_missing_dates(raw_df)
        feat_df = self.preparer.engineer_lightgbm_features(clean_df)
        train_df, val_df = self.preparer.split_train_test(feat_df)

        # Step 2: Prophet Forecasting
        logger.info("[1/4] Running Prophet forecasting stage...")
        prophet_forecaster = ProphetForecaster()
        prophet_val_preds = prophet_forecaster.predict_all(train_df, val_df)

        # Step 3: LightGBM Forecasting
        logger.info("[2/4] Running LightGBM forecasting stage...")
        lgb_forecaster = LightGBMForecaster()
        lgb_val_preds = lgb_forecaster.train_and_predict(train_df, val_df)

        # Step 4: Model Evaluation & Selection
        logger.info("[3/4] Evaluating validation performance & selecting best model...")
        eval_df, best_model_name = self.evaluator.evaluate_models(prophet_val_preds, lgb_val_preds)

        # Step 5: Generate 30-Day Future Forecast using Winner
        logger.info("[4/4] Generating future %d-day forecast using winning model (%s)...", horizon_days, best_model_name)
        if best_model_name == "LightGBM":
            forecast_df = lgb_forecaster.predict_future(clean_df, horizon_days=horizon_days)
        else:
            forecast_df = prophet_forecaster.predict_future(clean_df, horizon_days=horizon_days)

        # Validate Forecast Output
        assert not forecast_df.empty, "Generated future forecast dataframe is empty!"
        assert (forecast_df["predicted_demand"] >= 0).all(), "Negative demand predictions detected!"
        assert forecast_df["predicted_demand"].isna().sum() == 0, "NaN values detected in forecast!"

        forecast_df["forecast_date"] = pd.to_datetime(forecast_df["forecast_date"])
        logger.info("Generated %d total 30-day forecast records across %d unique store-item series.",
                    len(forecast_df), forecast_df[["store_id", "item_id"]].drop_duplicates().shape[0])

        # Step 6: Store Forecast Results in BigQuery / DuckDB
        table_name = "forecast_results"
        logger.info("Persisting forecast results to warehouse table '%s.%s'...", self.client.dataset_id, table_name)
        self.client.load_dataframe(forecast_df, table_name, if_exists="replace")

        logger.info("==================================================")
        logger.info("   FORECASTING STAGE COMPLETED SUCCESSFULLY!      ")
        logger.info("==================================================\n")

        return {
            "evaluation_metrics": eval_df,
            "winning_model": best_model_name,
            "forecast_df": forecast_df,
            "prophet_val_preds": prophet_val_preds,
            "lgb_val_preds": lgb_val_preds
        }


if __name__ == "__main__":
    pipeline = ForecastingPipeline(series_limit=5)
    results = pipeline.run_forecasting_pipeline(horizon_days=30)
    print("Forecast Results Sample:\n", results["forecast_df"].head())
