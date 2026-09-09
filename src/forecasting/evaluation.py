"""
Retail Demand Forecasting — Model Evaluation & Best Model Selection Engine
Calculates MAE, RMSE, sMAPE metrics to compare Prophet vs LightGBM predictions.
"""

import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from src.data_ingestion.bq_client import WarehouseClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("ModelEvaluation")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class ModelEvaluator:
    """Evaluates validation performance of demand forecasting models and selects the optimal architecture."""

    def __init__(self, client: Optional[WarehouseClient] = None):
        self.client = client or WarehouseClient()

    @staticmethod
    def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculates MAE, RMSE, and sMAPE handling zero-demand safety."""
        y_true = np.array(y_true, dtype=float)
        y_pred = np.array(y_pred, dtype=float)

        mae = float(np.mean(np.abs(y_true - y_pred)))
        rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
        
        # Symmetric Mean Absolute Percentage Error (sMAPE)
        denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
        # Prevent division by zero when both y_true and y_pred are 0
        smape_mask = denominator > 1e-5
        if np.sum(smape_mask) > 0:
            smape = float(np.mean(np.abs(y_true[smape_mask] - y_pred[smape_mask]) / denominator[smape_mask]) * 100.0)
        else:
            smape = 0.0

        return {
            "MAE": round(mae, 4),
            "RMSE": round(rmse, 4),
            "sMAPE": round(smape, 2)
        }

    def evaluate_models(
        self,
        prophet_preds: pd.DataFrame,
        lgb_preds: pd.DataFrame
    ) -> Tuple[pd.DataFrame, str]:
        """
        Calculates metrics for Prophet and LightGBM predictions and returns evaluation summary and winning model.
        """
        logger.info("Evaluating forecasting models against validation actuals...")
        eval_records = []

        # Evaluate Prophet
        if not prophet_preds.empty:
            p_metrics = self.calculate_metrics(prophet_preds["actual"].values, prophet_preds["predicted_demand"].values)
            p_metrics["Model"] = "Prophet"
            eval_records.append(p_metrics)

        # Evaluate LightGBM
        if not lgb_preds.empty:
            lgb_metrics = self.calculate_metrics(lgb_preds["actual"].values, lgb_preds["predicted_demand"].values)
            lgb_metrics["Model"] = "LightGBM"
            eval_records.append(lgb_metrics)

        if not eval_records:
            raise ValueError("No prediction datasets provided for evaluation.")

        eval_df = pd.DataFrame(eval_records)[["Model", "MAE", "RMSE", "sMAPE"]]

        # Select best model based on lowest RMSE
        winning_row = eval_df.sort_values(by="RMSE", ascending=True).iloc[0]
        best_model_name = winning_row["Model"]

        logger.info("Model Comparison Matrix:\n\n%s\n", eval_df.to_string(index=False))
        logger.info("--> SELECTED BEST MODEL: %s (RMSE: %.4f, sMAPE: %.2f%%)",
                    best_model_name, winning_row["RMSE"], winning_row["sMAPE"])

        # Persist metrics to warehouse
        try:
            self.client.load_dataframe(eval_df, "model_evaluation_metrics", if_exists="replace")
        except Exception as exc:
            logger.warning("Could not persist evaluation metrics to warehouse: %s", exc)

        return eval_df, best_model_name


if __name__ == "__main__":
    from src.forecasting.data_preparation import ForecastingDataPreparer
    from src.forecasting.prophet_model import ProphetForecaster
    from src.forecasting.lightgbm_model import LightGBMForecaster

    prep = ForecastingDataPreparer()
    raw = prep.load_analytical_data(series_limit=2)
    clean = prep.fill_missing_dates(raw)
    feat = prep.engineer_lightgbm_features(clean)
    train, val = prep.split_train_test(feat)

    p = ProphetForecaster()
    p_preds = p.predict_all(train, val)

    lgb = LightGBMForecaster()
    lgb_preds = lgb.train_and_predict(train, val)

    evaluator = ModelEvaluator()
    summary, winner = evaluator.evaluate_models(p_preds, lgb_preds)
    print("Winner Model:", winner)
